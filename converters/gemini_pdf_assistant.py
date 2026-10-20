import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
import pymupdf as fitz
from google import genai
from google.genai import types

def get_gemini_client() -> Optional[genai.Client]:
    """
    Inicializa y retorna el cliente oficial de Gemini API si existe GEMINI_API_KEY.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        return genai.Client()
    except Exception:
        return None

def gemini_ocr_pdf(
    pdf_path_or_bytes: Union[str, Path, bytes],
    prompt: Optional[str] = None
) -> str:
    """
    Realiza OCR de ultra-alta precisión multimodal utilizando Gemini 3.8 Flash.
    Extrae texto, tablas formateadas, encabezados y notas de páginas escaneadas o fotos.
    """
    client = get_gemini_client()
    if not client:
        raise RuntimeError("No se detectó la variable de entorno GEMINI_API_KEY.")

    if isinstance(pdf_path_or_bytes, (str, Path)):
        with open(pdf_path_or_bytes, "rb") as f:
            pdf_bytes = f.read()
    else:
        pdf_bytes = pdf_path_or_bytes

    doc_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
    instruction = prompt or (
        "Eres un transcriptor y digitalizador experto de documentos. "
        "Realiza un OCR exhaustivo y preciso de este documento PDF. "
        "Transcribe fielmente todo el texto, títulos, subtítulos, listas y tablas (en formato Markdown). "
        "Conserva la jerarquía y estructura del documento original sin omitir ningún párrafo ni dato numérico."
    )

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=[doc_part, instruction]
    )
    return response.text or ""

def gemini_summarize_pdf(
    pdf_path_or_bytes: Union[str, Path, bytes],
    summary_type: str = "executive"
) -> str:
    """
    Genera un análisis y resumen profesional del PDF con Gemini 3.8 Flash.
    """
    client = get_gemini_client()
    if not client:
        raise RuntimeError("No se detectó la variable de entorno GEMINI_API_KEY.")

    if isinstance(pdf_path_or_bytes, (str, Path)):
        with open(pdf_path_or_bytes, "rb") as f:
            pdf_bytes = f.read()
    else:
        pdf_bytes = pdf_path_or_bytes

    doc_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")

    if summary_type == "bullets":
        prompt = (
            "Analiza detalladamente este documento PDF y elabora una síntesis en viñetas ordenadas (Bullet Points) "
            "con las conclusiones clave, datos relevantes, acuerdos o especificaciones técnicas."
        )
    elif summary_type == "deep":
        prompt = (
            "Realiza un análisis exhaustivo de este documento. Incluye:\n"
            "1. Objetivo y propósito principal del documento.\n"
            "2. Resumen sección por sección.\n"
            "3. Puntos críticos, fechas, plazos y números clave.\n"
            "4. Conclusiones y recomendaciones estratégicas."
        )
    else:
        prompt = (
            "Elabora un Resumen Ejecutivo de alto impacto para este documento PDF. "
            "Estructura la respuesta con: Contexto General, Hallazgos Principales y Conclusiones Clave. "
            "Usa un tono profesional, claro y directo en español."
        )

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=[doc_part, prompt]
    )
    return response.text or ""

def gemini_chat_with_pdf(
    pdf_path_or_bytes: Union[str, Path, bytes],
    user_question: str,
    chat_history: Optional[List[Dict[str, str]]] = None
) -> str:
    """
    Responde consultas interactivas del usuario sobre el contenido del documento PDF usando Gemini 3.8 Flash.
    """
    client = get_gemini_client()
    if not client:
        raise RuntimeError("No se detectó la variable de entorno GEMINI_API_KEY.")

    if isinstance(pdf_path_or_bytes, (str, Path)):
        with open(pdf_path_or_bytes, "rb") as f:
            pdf_bytes = f.read()
    else:
        pdf_bytes = pdf_path_or_bytes

    doc_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")

    conversation_context = ""
    if chat_history:
        for msg in chat_history[-6:]:
            role = "Usuario" if msg.get("role") == "user" else "Asistente"
            conversation_context += f"{role}: {msg.get('content', '')}\n"

    prompt = (
        "Eres un analista de documentos inteligente. Lee con total atención el documento PDF adjunto "
        "y responde la siguiente pregunta del usuario basándote con máxima fidelidad en el contenido del documento.\n\n"
        f"Historial reciente:\n{conversation_context}\n"
        f"Pregunta del usuario: {user_question}\n\n"
        "Si la respuesta se encuentra explícita en el documento, cítala textualmente o indica la sección de referencia. "
        "Si la información no aparece en el archivo, dilo con honestidad."
    )

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=[doc_part, prompt]
    )
    return response.text or ""

def gemini_translate_pdf_text(
    pdf_path_or_bytes: Union[str, Path, bytes],
    target_language: str = "Español"
) -> str:
    """
    Traduce el contenido del PDF al idioma de destino utilizando Gemini 3.8 Flash,
    manteniendo la terminología técnica y formato de párrafos.
    """
    client = get_gemini_client()
    if not client:
        raise RuntimeError("No se detectó la variable de entorno GEMINI_API_KEY.")

    if isinstance(pdf_path_or_bytes, (str, Path)):
        with open(pdf_path_or_bytes, "rb") as f:
            pdf_bytes = f.read()
    else:
        pdf_bytes = pdf_path_or_bytes

    doc_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
    prompt = (
        f"Traduce todo el contenido de este documento PDF al idioma: {target_language}. "
        "Mantén la estructura en Markdown con títulos, listas, tablas y numeración original. "
        "Asegura una traducción técnica y natural de altísima calidad."
    )

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=[doc_part, prompt]
    )
    return response.text or ""
