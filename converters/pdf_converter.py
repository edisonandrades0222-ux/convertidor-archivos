import os
from pathlib import Path
from PIL import Image

def pdf_to_docx(pdf_path, output_path=None, progress_callback=None):
    """
    Convierte un documento PDF a Word (.docx) manteniendo formato, tablas e imagenes.
    """
    from pdf2docx import Converter
    
    pdf_path = Path(pdf_path)
    if not output_path:
        output_path = pdf_path.with_suffix(".docx")
    else:
        output_path = Path(output_path)
        
    if progress_callback:
        progress_callback("Iniciando conversión de PDF a Word...")
        
    try:
        cv = Converter(str(pdf_path))
        cv.convert(str(output_path), start=0, end=None)
        cv.close()
        if progress_callback:
            progress_callback(f"Completado con éxito: {output_path.name}")
        return str(output_path)
    except Exception as e:
        if progress_callback:
            progress_callback(f"Aplicando extractor de alta compatibilidad...")
        try:
            import pymupdf
            import docx
            doc_pdf = pymupdf.open(str(pdf_path))
            doc_word = docx.Document()
            for idx, page in enumerate(doc_pdf):
                text = page.get_text()
                if text.strip():
                    for line in text.splitlines():
                        if line.strip():
                            doc_word.add_paragraph(line)
                if idx < len(doc_pdf) - 1:
                    doc_word.add_page_break()
            doc_pdf.close()
            doc_word.save(str(output_path))
            if progress_callback:
                progress_callback(f"Completado con éxito: {output_path.name}")
            return str(output_path)
        except Exception:
            raise e

def pdf_to_images(pdf_path, output_folder=None, img_format="png", dpi=200, progress_callback=None):
    """
    Convierte cada página del PDF en una imagen (PNG o JPG).
    """
    import fitz  # PyMuPDF
    
    pdf_path = Path(pdf_path)
    if not output_folder:
        output_folder = pdf_path.parent / f"{pdf_path.stem}_imagenes"
    else:
        output_folder = Path(output_folder)
        
    output_folder.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)
    generated_files = []
    
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    
    for i, page in enumerate(doc):
        if progress_callback:
            progress_callback(f"Procesando página {i + 1} de {total_pages}...")
            
        pix = page.get_pixmap(matrix=mat, alpha=False if img_format.lower() in ["jpg", "jpeg"] else True)
        out_file = output_folder / f"pagina_{i + 1:03d}.{img_format.lower()}"
        pix.save(str(out_file))
        generated_files.append(str(out_file))
        
    doc.close()
    if progress_callback:
        progress_callback(f"Se generaron {len(generated_files)} imágenes en {output_folder.name}")
    return generated_files

def images_to_pdf(image_paths, output_pdf_path, progress_callback=None):
    """
    Combina una lista de imágenes en un único archivo PDF.
    """
    if not image_paths:
        raise ValueError("No se proporcionaron imágenes para convertir a PDF.")
        
    output_pdf_path = Path(output_pdf_path)
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    
    if progress_callback:
        progress_callback(f"Preparando {len(image_paths)} imagen(es) para el PDF...")
        
    pil_images = []
    for idx, img_p in enumerate(image_paths):
        img = Image.open(img_p)
        if img.mode != "RGB":
            img = img.convert("RGB")
        pil_images.append(img)
        
    first_img = pil_images[0]
    rest_imgs = pil_images[1:] if len(pil_images) > 1 else []
    
    first_img.save(
        str(output_pdf_path),
        "PDF",
        resolution=100.0,
        save_all=True,
        append_images=rest_imgs
    )
    
    if progress_callback:
        progress_callback(f"PDF generado exitosamente: {output_pdf_path.name}")
    return str(output_pdf_path)

def pdf_to_text(pdf_path, output_txt_path=None, progress_callback=None):
    """
    Extrae todo el texto de un PDF a un archivo .txt.
    """
    import fitz
    
    pdf_path = Path(pdf_path)
    if not output_txt_path:
        output_txt_path = pdf_path.with_suffix(".txt")
    else:
        output_txt_path = Path(output_txt_path)
        
    doc = fitz.open(str(pdf_path))
    full_text = []
    
    for i, page in enumerate(doc):
        full_text.append(f"--- PÁGINA {i+1} ---\n")
        full_text.append(page.get_text())
        full_text.append("\n\n")
        
    doc.close()
    
    with open(output_txt_path, "w", encoding="utf-8") as f:
        f.writelines(full_text)
        
    if progress_callback:
        progress_callback(f"Texto guardado en: {output_txt_path.name}")
    return str(output_txt_path)
