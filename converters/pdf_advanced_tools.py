import os
import io
import math
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
import pymupdf as fitz
from PIL import Image

def merge_pdfs(pdf_paths: List[Union[str, Path]], output_path: Union[str, Path]) -> str:
    """
    Une múltiples archivos PDF en un único documento respetando el orden de la lista.
    Equivalente a 'Unir PDF' de iLovePDF.
    """
    if not pdf_paths:
        raise ValueError("Debes proporcionar al menos un archivo PDF para unir.")

    merged_doc = fitz.open()
    for p in pdf_paths:
        with fitz.open(str(p)) as src:
            merged_doc.insert_pdf(src)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged_doc.save(str(output_path), deflate=True, garbage=3)
    merged_doc.close()
    return str(output_path)

def split_pdf(
    pdf_path: Union[str, Path], 
    output_dir: Union[str, Path], 
    ranges: Optional[str] = None
) -> List[str]:
    """
    Divide un PDF por rangos de páginas (ej: '1-3, 5, 8-10') o en páginas individuales si ranges es None.
    Equivalente a 'Dividir PDF' de iLovePDF.
    """
    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(pdf_path).stem
    created_files = []

    if not ranges or ranges.strip() == "":
        # Extraer cada página individualmente
        for i in range(total_pages):
            out_file = out_dir / f"{stem}_pag_{i + 1:03d}.pdf"
            sub_doc = fitz.open()
            sub_doc.insert_pdf(doc, from_page=i, to_page=i)
            sub_doc.save(str(out_file), deflate=True)
            sub_doc.close()
            created_files.append(str(out_file))
    else:
        # Procesar rangos especificados por el usuario
        range_parts = [r.strip() for r in ranges.split(",") if r.strip()]
        for idx, part in enumerate(range_parts):
            if "-" in part:
                tokens = part.split("-")
                start = max(1, int(tokens[0])) - 1
                end = min(total_pages, int(tokens[1])) - 1
            else:
                p_num = int(part)
                start = max(1, p_num) - 1
                end = min(total_pages, p_num) - 1

            if start <= end and start < total_pages:
                out_file = out_dir / f"{stem}_rango_{idx + 1}_{start + 1}-{end + 1}.pdf"
                sub_doc = fitz.open()
                sub_doc.insert_pdf(doc, from_page=start, to_page=end)
                sub_doc.save(str(out_file), deflate=True)
                sub_doc.close()
                created_files.append(str(out_file))

    doc.close()
    return created_files

def remove_pages(
    pdf_path: Union[str, Path], 
    pages_to_remove: List[int], 
    output_path: Union[str, Path]
) -> str:
    """
    Elimina las páginas indicadas (1-based index) de un PDF.
    Equivalente a 'Eliminar páginas' de iLovePDF.
    """
    doc = fitz.open(str(pdf_path))
    total = len(doc)
    # Convertir a 0-based index y ordenar en orden descendente para borrar sin alterar índices
    zero_based = sorted([p - 1 for p in pages_to_remove if 1 <= p <= total], reverse=True)
    for p in zero_based:
        doc.delete_page(p)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path), deflate=True, garbage=3)
    doc.close()
    return str(output_path)

def extract_pages(
    pdf_path: Union[str, Path], 
    pages_to_keep: List[int], 
    output_path: Union[str, Path]
) -> str:
    """
    Conserva únicamente las páginas especificadas (1-based index) en un nuevo PDF.
    Equivalente a 'Extraer páginas' de iLovePDF.
    """
    doc = fitz.open(str(pdf_path))
    total = len(doc)
    zero_based = [p - 1 for p in pages_to_keep if 1 <= p <= total]
    doc.select(zero_based)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path), deflate=True, garbage=3)
    doc.close()
    return str(output_path)

def rotate_pages(
    pdf_path: Union[str, Path], 
    rotation: int, 
    pages: Union[str, List[int]] = "all", 
    output_path: Optional[Union[str, Path]] = None
) -> str:
    """
    Rota páginas 90, 180 o 270 grados.
    Equivalente a 'Rotar PDF' de iLovePDF.
    """
    doc = fitz.open(str(pdf_path))
    total = len(doc)
    if pages == "all":
        target_indices = list(range(total))
    else:
        target_indices = [p - 1 for p in pages if 1 <= p <= total]

    for idx in target_indices:
        page = doc[idx]
        page.set_rotation((page.rotation + rotation) % 360)

    if not output_path:
        output_path = Path(pdf_path).with_name(f"{Path(pdf_path).stem}_rotado.pdf")
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path), deflate=True)
    doc.close()
    return str(output_path)

def compress_pdf(
    pdf_path: Union[str, Path], 
    output_path: Union[str, Path], 
    level: str = "recommended"
) -> Tuple[str, int, int]:
    """
    Optimiza y comprime drásticamente el peso de un PDF (baja, recomendada o extrema).
    En iLovePDF la compresión extrema es una función de pago/premium. Aquí es 100% libre.
    Retorna (output_path, original_size, compressed_size).
    """
    pdf_path = Path(pdf_path)
    output_path = Path(output_path)
    orig_size = pdf_path.stat().st_size

    doc = fitz.open(str(pdf_path))

    # Parámetros según el nivel de compresión
    if level == "extreme":
        # Compresión Extrema: remuestreo de imágenes a menor resolución y calidad JPEG + garbage collecion total
        for page in doc:
            for img in page.get_images():
                xref = img[0]
                base_img = doc.extract_image(xref)
                if base_img and "image" in base_img:
                    try:
                        pil_img = Image.open(io.BytesIO(base_img["image"]))
                        if pil_img.mode not in ["RGB", "L"]:
                            pil_img = pil_img.convert("RGB")
                        # Reducir resolución a máximo 1200px de lado mayor
                        max_side = max(pil_img.size)
                        if max_side > 1200:
                            ratio = 1200.0 / max_side
                            new_size = (int(pil_img.size[0] * ratio), int(pil_img.size[1] * ratio))
                            pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
                        
                        out_io = io.BytesIO()
                        pil_img.save(out_io, format="JPEG", quality=60, optimize=True)
                        # Reemplazar flujo de imagen en el PDF
                        doc.update_stream(xref, out_io.getvalue())
                    except Exception:
                        pass
        doc.save(
            str(output_path),
            garbage=4,
            deflate=True,
            deflate_images=True,
            clean=True
        )
    elif level == "low":
        # Compresión baja: lossless, máxima fidelidad visual
        doc.save(str(output_path), garbage=3, deflate=True)
    else:
        # Recomendada: compresión óptima sin pérdida visible
        doc.save(str(output_path), garbage=4, deflate=True, clean=True)

    doc.close()
    comp_size = output_path.stat().st_size
    return (str(output_path), orig_size, comp_size)

def protect_pdf(
    pdf_path: Union[str, Path], 
    output_path: Union[str, Path], 
    user_password: str, 
    owner_password: Optional[str] = None
) -> str:
    """
    Protege un PDF con encriptación militar AES-256 bits y contraseña.
    Función de seguridad destacada de iLovePDF.
    """
    doc = fitz.open(str(pdf_path))
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    owner_pw = owner_password if owner_password else user_password
    doc.save(
        str(output_path),
        encryption=fitz.PDF_ENCRYPT_AES_256,
        user_pw=user_password,
        owner_pw=owner_pw,
        permissions=fitz.PDF_PERM_PRINT | fitz.PDF_PERM_COPY
    )
    doc.close()
    return str(output_path)

def unlock_pdf(
    pdf_path: Union[str, Path], 
    output_path: Union[str, Path], 
    password: str
) -> str:
    """
    Desbloquea un PDF protegido eliminando contraseñas y cualquier restricción de copiado/impresión.
    """
    doc = fitz.open(str(pdf_path))
    if doc.is_encrypted:
        auth_success = doc.authenticate(password)
        if not auth_success:
            raise ValueError("Contraseña incorrecta. No se pudo desbloquear el PDF.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Guardar sin encriptación
    doc.save(str(output_path), encryption=fitz.PDF_ENCRYPT_KEEP, deflate=True)
    doc.close()
    return str(output_path)

def watermark_pdf(
    pdf_path: Union[str, Path], 
    output_path: Union[str, Path], 
    text: Optional[str] = "CONFIDENCIAL", 
    image_path: Optional[Union[str, Path]] = None, 
    opacity: float = 0.35, 
    angle: float = 45.0, 
    font_size: float = 48.0, 
    color: Any = "#757575"
) -> str:
    """
    Aplica una marca de agua (texto o imagen) profesional en todas las páginas del PDF.
    Equivalente a 'Marca de agua' de iLovePDF.
    """
    from converters.pdf_editor import parse_color
    doc = fitz.open(str(pdf_path))
    norm_color = parse_color(color)

    for page in doc:
        rect = page.rect
        cx = rect.width / 2.0
        cy = rect.height / 2.0

        if image_path and Path(image_path).exists():
            # Marca de agua con imagen centrada
            with Image.open(image_path) as im:
                im_w, im_h = im.size
                scale = min(rect.width * 0.5 / im_w, rect.height * 0.5 / im_h)
                w = im_w * scale
                h = im_h * scale
                img_rect = fitz.Rect(cx - w/2, cy - h/2, cx + w/2, cy + h/2)
                page.insert_image(img_rect, filename=str(image_path), overlay=True)
        elif text:
            # Marca de agua con texto rotado
            # Usar shape o insert_text con matriz de rotación
            rad = math.radians(angle)
            # Calcular posición estimada para centrar texto
            approx_w = len(text) * font_size * 0.5
            start_x = cx - (approx_w / 2.0) * math.cos(rad)
            start_y = cy - (approx_w / 2.0) * math.sin(rad)
            
            # En PyMuPDF podemos insertar el texto con morph=(point, matrix) para rotación exacta
            morph = (fitz.Point(cx, cy), fitz.Matrix(angle))
            page.insert_text(
                fitz.Point(cx - approx_w / 2.0, cy),
                text,
                fontsize=font_size,
                fontname="helv",
                color=norm_color,
                morph=morph,
                stroke_opacity=opacity,
                fill_opacity=opacity
            )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path), deflate=True)
    doc.close()
    return str(output_path)

def rotate_page_bytes(pdf_bytes: bytes, page_number: int, angle: int = 90) -> bytes:
    """Rota la página indicada (0-indexed) de un flujo de bytes PDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if 0 <= page_number < len(doc):
        p = doc[page_number]
        p.set_rotation((p.rotation + angle) % 360)
    out = doc.tobytes(deflate=True, garbage=3)
    doc.close()
    return out

def insert_blank_page_bytes(pdf_bytes: bytes, after_page: int, width: float = 595.0, height: float = 842.0) -> bytes:
    """Inserta una página en blanco después de after_page (0-indexed)."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    idx = max(0, min(len(doc), after_page + 1))
    doc.new_page(idx, width=width, height=height)
    out = doc.tobytes(deflate=True, garbage=3)
    doc.close()
    return out

def duplicate_page_bytes(pdf_bytes: bytes, page_number: int) -> bytes:
    """Duplica la página indicada (0-indexed) justo a continuación."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    src = fitz.open(stream=pdf_bytes, filetype="pdf")
    if 0 <= page_number < len(doc):
        doc.insert_pdf(src, from_page=page_number, to_page=page_number, start_at=page_number + 1)
    out = doc.tobytes(deflate=True, garbage=3)
    src.close()
    doc.close()
    return out

def delete_page_bytes(pdf_bytes: bytes, page_number: int) -> bytes:
    """Elimina la página indicada (0-indexed) si el documento tiene más de 1 página."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if len(doc) > 1 and 0 <= page_number < len(doc):
        doc.delete_page(page_number)
    out = doc.tobytes(deflate=True, garbage=3)
    doc.close()
    return out

def extract_single_page_bytes(pdf_bytes: bytes, page_number: int) -> bytes:
    """Extrae únicamente la página indicada (0-indexed) como un nuevo PDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if 0 <= page_number < len(doc):
        sub = fitz.open()
        sub.insert_pdf(doc, from_page=page_number, to_page=page_number)
        out = sub.tobytes(deflate=True)
        sub.close()
    else:
        out = pdf_bytes
    doc.close()
    return out

def add_page_numbers(
    pdf_path: Union[str, Path], 
    output_path: Union[str, Path], 
    format_template: str = "Página {page} de {total}", 
    position: str = "bottom_center", 
    margin: float = 30.0, 
    font_size: float = 10.0, 
    color: Any = "#333333"
) -> str:
    """
    Inserta numeración de páginas en el pie de página o encabezado de cada hoja.
    Equivalente a 'Número de página' de iLovePDF.
    """
    from converters.pdf_editor import parse_color
    norm_c = parse_color(color)
    doc = fitz.open(str(pdf_path))
    total = len(doc)

    for i, page in enumerate(doc):
        label = format_template.format(page=i + 1, total=total)
        text_w = len(label) * font_size * 0.55
        p_rect = page.rect

        if position == "bottom_center":
            pos = fitz.Point((p_rect.width - text_w) / 2.0, p_rect.height - margin)
        elif position == "bottom_right":
            pos = fitz.Point(p_rect.width - text_w - margin, p_rect.height - margin)
        elif position == "bottom_left":
            pos = fitz.Point(margin, p_rect.height - margin)
        elif position == "top_center":
            pos = fitz.Point((p_rect.width - text_w) / 2.0, margin + font_size)
        elif position == "top_right":
            pos = fitz.Point(p_rect.width - text_w - margin, margin + font_size)
        else:
            pos = fitz.Point(margin, margin + font_size)

        page.insert_text(pos, label, fontsize=font_size, fontname="helv", color=norm_c)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path), deflate=True)
    doc.close()
    return str(output_path)

def rotate_page_bytes(pdf_bytes: bytes, page_number: int, angle: int = 90) -> bytes:
    """Rota la página indicada (0-indexed) de un flujo de bytes PDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if 0 <= page_number < len(doc):
        p = doc[page_number]
        p.set_rotation((p.rotation + angle) % 360)
    out = doc.tobytes(deflate=True, garbage=3)
    doc.close()
    return out

def insert_blank_page_bytes(pdf_bytes: bytes, after_page: int, width: float = 595.0, height: float = 842.0) -> bytes:
    """Inserta una página en blanco después de after_page (0-indexed)."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    idx = max(0, min(len(doc), after_page + 1))
    doc.new_page(idx, width=width, height=height)
    out = doc.tobytes(deflate=True, garbage=3)
    doc.close()
    return out

def duplicate_page_bytes(pdf_bytes: bytes, page_number: int) -> bytes:
    """Duplica la página indicada (0-indexed) justo a continuación."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    src = fitz.open(stream=pdf_bytes, filetype="pdf")
    if 0 <= page_number < len(doc):
        doc.insert_pdf(src, from_page=page_number, to_page=page_number, start_at=page_number + 1)
    out = doc.tobytes(deflate=True, garbage=3)
    src.close()
    doc.close()
    return out

def delete_page_bytes(pdf_bytes: bytes, page_number: int) -> bytes:
    """Elimina la página indicada (0-indexed) si el documento tiene más de 1 página."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if len(doc) > 1 and 0 <= page_number < len(doc):
        doc.delete_page(page_number)
    out = doc.tobytes(deflate=True, garbage=3)
    doc.close()
    return out

def extract_single_page_bytes(pdf_bytes: bytes, page_number: int) -> bytes:
    """Extrae únicamente la página indicada (0-indexed) como un nuevo PDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if 0 <= page_number < len(doc):
        sub = fitz.open()
        sub.insert_pdf(doc, from_page=page_number, to_page=page_number)
        out = sub.tobytes(deflate=True)
        sub.close()
    else:
        out = pdf_bytes
    doc.close()
    return out

def pdf_to_pptx(pdf_path: Union[str, Path], output_path: Union[str, Path]) -> str:
    """
    Convierte cada página del PDF en una diapositiva de presentación PowerPoint (.pptx).
    Equivalente a 'PDF a PowerPoint' de iLovePDF.
    """
    from pptx import Presentation
    from pptx.util import Inches, Pt

    doc = fitz.open(str(pdf_path))
    prs = Presentation()
    # Ajustar a pantalla ancha 16:9
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    for i, page in enumerate(doc):
        slide = prs.slides.add_slide(blank_layout)
        # Renderizar página como imagen de alta resolución para garantizar fidelidad 100% de tablas y diagramas
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        
        # Calcular proporciones para ajustar en la diapositiva
        page_ratio = page.rect.width / page.rect.height
        target_h = 6.8
        target_w = target_h * page_ratio
        if target_w > 12.0:
            target_w = 12.0
            target_h = target_w / page_ratio

        left = Inches((13.333 - target_w) / 2.0)
        top = Inches((7.5 - target_h) / 2.0)

        img_stream = io.BytesIO(img_bytes)
        slide.shapes.add_picture(img_stream, left, top, width=Inches(target_w), height=Inches(target_h))

    doc.close()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))
    return str(output_path)

def pdf_to_excel(pdf_path: Union[str, Path], output_path: Union[str, Path]) -> str:
    """
    Detecta automáticamente tablas en el PDF y las exporta a un libro Excel (.xlsx).
    Equivalente a 'PDF a Excel' de iLovePDF.
    """
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = openpyxl.Workbook()
    # Eliminar hoja por defecto
    wb.remove(wb.active)

    doc = fitz.open(str(pdf_path))
    found_any_table = False

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    thin_border = Border(
        left=Side(style="thin", color="CCCCCC"),
        right=Side(style="thin", color="CCCCCC"),
        top=Side(style="thin", color="CCCCCC"),
        bottom=Side(style="thin", color="CCCCCC")
    )

    for i, page in enumerate(doc):
        tabs = page.find_tables()
        if tabs.tables:
            found_any_table = True
            ws = wb.create_sheet(title=f"Página_{i + 1}")
            row_idx = 1
            for t_idx, tab in enumerate(tabs):
                df_data = tab.extract()
                if not df_data:
                    continue
                # Escribir título de tabla
                title_cell = ws.cell(row=row_idx, column=1, value=f"Tabla {t_idx + 1} (Página {i + 1})")
                title_cell.font = Font(bold=True, size=12, color="1F497D")
                row_idx += 1

                for r_i, row in enumerate(df_data):
                    for c_i, val in enumerate(row):
                        cell = ws.cell(row=row_idx, column=c_i + 1, value=str(val or "").strip())
                        cell.border = thin_border
                        if r_i == 0:
                            cell.font = header_font
                            cell.fill = header_fill
                            cell.alignment = Alignment(horizontal="center", vertical="center")
                    row_idx += 1
                row_idx += 2  # Separación entre tablas
        else:
            # Si no hay tablas formales, volcar el texto por bloques ordenados
            text_blocks = page.get_text("blocks")
            if text_blocks:
                ws = wb.create_sheet(title=f"Texto_Pág_{i + 1}")
                ws.cell(row=1, column=1, value=f"Contenido Extraído - Página {i + 1}").font = Font(bold=True)
                for r_i, blk in enumerate(text_blocks):
                    ws.cell(row=r_i + 2, column=1, value=blk[4].strip())

    doc.close()

    if not wb.sheetnames:
        ws = wb.create_sheet(title="Documento")
        ws.cell(row=1, column=1, value="No se detectaron datos estructurados en el documento.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(output_path))
    return str(output_path)

def crop_pdf(
    pdf_path: Union[str, Path], 
    output_path: Union[str, Path], 
    margins: Tuple[float, float, float, float] = (10, 10, 10, 10)
) -> str:
    """
    Recorta los bordes de cada página del PDF según los márgenes especificados (izq, sup, der, inf).
    Equivalente a 'Recortar PDF' de iLovePDF.
    """
    left_m, top_m, right_m, bottom_m = margins
    doc = fitz.open(str(pdf_path))

    for page in doc:
        rect = page.rect
        new_rect = fitz.Rect(
            rect.x0 + left_m,
            rect.y0 + top_m,
            rect.x1 - right_m,
            rect.y1 - bottom_m
        )
        if new_rect.width > 20 and new_rect.height > 20:
            page.set_cropbox(new_rect)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path), deflate=True)
    doc.close()
    return str(output_path)

def rotate_page_bytes(pdf_bytes: bytes, page_number: int, angle: int = 90) -> bytes:
    """Rota la página indicada (0-indexed) de un flujo de bytes PDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if 0 <= page_number < len(doc):
        p = doc[page_number]
        p.set_rotation((p.rotation + angle) % 360)
    out = doc.tobytes(deflate=True, garbage=3)
    doc.close()
    return out

def insert_blank_page_bytes(pdf_bytes: bytes, after_page: int, width: float = 595.0, height: float = 842.0) -> bytes:
    """Inserta una página en blanco después de after_page (0-indexed)."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    idx = max(0, min(len(doc), after_page + 1))
    doc.new_page(idx, width=width, height=height)
    out = doc.tobytes(deflate=True, garbage=3)
    doc.close()
    return out

def duplicate_page_bytes(pdf_bytes: bytes, page_number: int) -> bytes:
    """Duplica la página indicada (0-indexed) justo a continuación."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    src = fitz.open(stream=pdf_bytes, filetype="pdf")
    if 0 <= page_number < len(doc):
        doc.insert_pdf(src, from_page=page_number, to_page=page_number, start_at=page_number + 1)
    out = doc.tobytes(deflate=True, garbage=3)
    src.close()
    doc.close()
    return out

def delete_page_bytes(pdf_bytes: bytes, page_number: int) -> bytes:
    """Elimina la página indicada (0-indexed) si el documento tiene más de 1 página."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if len(doc) > 1 and 0 <= page_number < len(doc):
        doc.delete_page(page_number)
    out = doc.tobytes(deflate=True, garbage=3)
    doc.close()
    return out

def extract_single_page_bytes(pdf_bytes: bytes, page_number: int) -> bytes:
    """Extrae únicamente la página indicada (0-indexed) como un nuevo PDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if 0 <= page_number < len(doc):
        sub = fitz.open()
        sub.insert_pdf(doc, from_page=page_number, to_page=page_number)
        out = sub.tobytes(deflate=True)
        sub.close()
    else:
        out = pdf_bytes
    doc.close()
    return out
