import os
import io
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import pymupdf as fitz
import docx
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from google import genai
from converters.gemini_pdf_assistant import get_gemini_client

def extract_pdf_to_document_data(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Extrae el contenido de un PDF con estructura semántica (títulos, párrafos, páginas)
    para alimentar el procesador de texto en línea estilo Microsoft Word.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages_data = []
    full_paragraphs = []
    html_parts = []

    for i, page in enumerate(doc):
        page_num = i + 1
        blocks = page.get_text("blocks")
        page_text_blocks = []

        for b in blocks:
            # b = (x0, y0, x1, y1, "text", block_no, block_type)
            # block_type == 0 es texto
            if b[6] == 0:
                raw_text = b[4].strip()
                if not raw_text:
                    continue
                
                # Heurística para detectar encabezados según longitud y mayúsculas
                lines = raw_text.split("\n")
                first_line = lines[0].strip()
                is_heading = len(raw_text) < 70 and (first_line.isupper() or len(lines) == 1)
                
                clean_text = " ".join(lines)
                page_text_blocks.append(clean_text)
                full_paragraphs.append(clean_text)

                if is_heading and len(clean_text) < 50:
                    html_parts.append(f"<h3>{clean_text}</h3>")
                else:
                    html_parts.append(f"<p>{clean_text}</p>")

        pages_data.append({
            "page_num": page_num,
            "text": "\n\n".join(page_text_blocks),
            "paragraphs": page_text_blocks
        })

    doc.close()

    full_plain_text = "\n\n".join(full_paragraphs)
    full_html = "".join(html_parts) if html_parts else f"<p>{full_plain_text}</p>"

    return {
        "total_pages": len(pages_data),
        "pages": pages_data,
        "full_text": full_plain_text,
        "html_content": full_html
    }

def compile_html_to_pdf(html_text: str, doc_title: str = "Documento") -> bytes:
    """
    Compila el texto enriquecido editado en el procesador Word a un PDF editorial
    en memoria (A4, márgenes 2cm, tipografía limpia Helvetica y paginación) con PyMuPDF.
    """
    # Envolver con estilos CSS limpios tipo Word
    styled_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
      body {{
        font-family: Helvetica, Arial, sans-serif;
        font-size: 11pt;
        line-height: 1.6;
        color: #222222;
      }}
      h1 {{
        font-size: 20pt;
        color: #1a237e;
        border-bottom: 2px solid #1a237e;
        padding-bottom: 4px;
        margin-top: 18px;
        margin-bottom: 12px;
      }}
      h2 {{
        font-size: 15pt;
        color: #0d47a1;
        margin-top: 14px;
        margin-bottom: 8px;
      }}
      h3 {{
        font-size: 12pt;
        color: #1565c0;
        margin-top: 12px;
        margin-bottom: 6px;
      }}
      p {{
        margin-top: 0;
        margin-bottom: 10px;
        text-align: justify;
      }}
      ul, ol {{
        margin-top: 4px;
        margin-bottom: 10px;
        padding-left: 24px;
      }}
      li {{
        margin-bottom: 4px;
      }}
      blockquote {{
        border-left: 4px solid #3b8ed0;
        padding-left: 12px;
        color: #555555;
        margin-left: 0;
      }}
    </style>
    </head>
    <body>
    {html_text}
    </body>
    </html>
    """

    buf = io.BytesIO()
    writer = fitz.DocumentWriter(buf)
    story = fitz.Story(html=styled_html)

    # Dimensiones estándar A4 (595 x 842 pt) con márgenes de 54 pt (0.75 pulgadas)
    mediabox = fitz.Rect(0, 0, 595, 842)
    printable_area = fitz.Rect(54, 54, 595 - 54, 842 - 54)

    more = 1
    while more:
        dev = writer.begin_page(mediabox)
        more, _ = story.place(printable_area)
        story.draw(dev)
        writer.end_page()

    writer.close()
    return buf.getvalue()

def compile_html_to_docx(html_text: str, doc_title: str = "Documento") -> bytes:
    """
    Convierte el texto editado en el procesador Word a un archivo nativo Microsoft Word (.docx).
    """
    doc = docx.Document()

    # Configurar márgenes estándar de 1 pulgada (2.54 cm)
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # Si es texto plano o HTML básico, dividir por líneas o etiquetas
    # Reemplazar saltos y normalizar
    clean_html = re.sub(r'</?(div|span)[^>]*>', '', html_text)

    # Dividir por etiquetas de bloque: h1, h2, h3, p, li
    tokens = re.split(r'(<h[1-3][^>]*>.*?</h[1-3]>|<p[^>]*>.*?</p>|<li[^>]*>.*?</li>)', clean_html, flags=re.DOTALL | re.IGNORECASE)

    has_content = False
    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue

        # Encabezado 1
        m_h1 = re.match(r'<h1[^>]*>(.*?)</h1>', tok, re.DOTALL | re.IGNORECASE)
        if m_h1:
            clean_t = re.sub(r'<[^>]+>', '', m_h1.group(1)).strip()
            if clean_t:
                doc.add_heading(clean_t, level=1)
                has_content = True
            continue

        # Encabezado 2
        m_h2 = re.match(r'<h2[^>]*>(.*?)</h2>', tok, re.DOTALL | re.IGNORECASE)
        if m_h2:
            clean_t = re.sub(r'<[^>]+>', '', m_h2.group(1)).strip()
            if clean_t:
                doc.add_heading(clean_t, level=2)
                has_content = True
            continue

        # Encabezado 3
        m_h3 = re.match(r'<h3[^>]*>(.*?)</h3>', tok, re.DOTALL | re.IGNORECASE)
        if m_h3:
            clean_t = re.sub(r'<[^>]+>', '', m_h3.group(1)).strip()
            if clean_t:
                doc.add_heading(clean_t, level=3)
                has_content = True
            continue

        # Lista
        m_li = re.match(r'<li[^>]*>(.*?)</li>', tok, re.DOTALL | re.IGNORECASE)
        if m_li:
            clean_t = re.sub(r'<[^>]+>', '', m_li.group(1)).strip()
            if clean_t:
                doc.add_paragraph(clean_t, style='List Bullet')
                has_content = True
            continue

        # Párrafo normal
        m_p = re.match(r'<p[^>]*>(.*?)</p>', tok, re.DOTALL | re.IGNORECASE)
        p_content = m_p.group(1) if m_p else tok
        clean_p = re.sub(r'<[^>]+>', '', p_content).strip()
        if clean_p:
            p = doc.add_paragraph()
            p.paragraph_format.line_spacing = 1.15
            p.paragraph_format.space_after = Pt(6)
            p.add_run(clean_p)
            has_content = True

    if not has_content:
        # Fallback si no había tags formales
        plain_t = re.sub(r'<[^>]+>', '', html_text).strip()
        for par in plain_t.split("\n\n"):
            if par.strip():
                doc.add_paragraph(par.strip())

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

def gemini_ai_word_assistant(
    text: str, 
    action: str = "grammar", 
    custom_instruction: Optional[str] = None
) -> str:
    """
    Asistente inteligente con Gemini 3.8 Flash para redacción, corrección de estilo
    y traducción en el modo procesador de texto (Microsoft Word).
    """
    client = get_gemini_client()
    if not client:
        raise RuntimeError("No se detectó la clave de API GEMINI_API_KEY.")

    if action == "grammar":
        prompt = (
            "Eres un corrector de estilo y editor editorial experto. Revisa y corrige minuciosamente "
            "la ortografía, acentuación, concordancia, puntuación y gramática del siguiente texto. "
            "Conserva intacta la intención y formato del documento. Devuelve únicamente el texto corregido:\n\n"
            f"{text}"
        )
    elif action == "formal":
        prompt = (
            "Reescribe el siguiente texto con un tono ejecutivo, formal y corporativo de alto nivel, "
            "garantizando precisión técnica y elegancia en la redacción. Devuelve únicamente el texto reescrito:\n\n"
            f"{text}"
        )
    elif action == "summarize":
        prompt = (
            "Elabora un resumen ejecutivo profesional y estructurado con viñetas del siguiente documento:\n\n"
            f"{text}"
        )
    elif action == "translate_en":
        prompt = (
            "Translate the following text into professional, fluent English. "
            "Preserve formatting, technical terms, and paragraph structure. Return only the translated text:\n\n"
            f"{text}"
        )
    elif action == "translate_es":
        prompt = (
            "Traduce el siguiente texto a un español profesional y fluido. "
            "Conserva la terminología técnica y estructura de párrafos. Devuelve únicamente el texto traducido:\n\n"
            f"{text}"
        )
    else:
        prompt = (
            f"Instrucción especial del usuario: {custom_instruction or 'Mejora este texto'}\n\n"
            f"Texto a procesar:\n{text}\n\n"
            "Devuelve el resultado listo para insertar en el documento."
        )

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt
    )
    return response.text or ""
