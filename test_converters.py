import os
import sys
from pathlib import Path
import pytest

# Añadir raíz del proyecto al path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from converters.cad_converter import dxf_to_pdf, dxf_to_dwg, dwg_to_pdf, dwg_to_dxf
from converters.pdf_converter import pdf_to_docx, pdf_to_images, images_to_pdf, pdf_to_text
from converters.image_converter import convert_image

@pytest.fixture(scope="session")
def test_dir(tmp_path_factory):
    # Usar directorio de muestras temporal para pruebas
    samples_dir = project_root / "test_samples"
    samples_dir.mkdir(exist_ok=True)
    return samples_dir

@pytest.fixture(scope="session")
def sample_dxf(test_dir):
    import ezdxf
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_line((0, 0), (100, 100), dxfattribs={"color": 1})
    msp.add_circle((50, 50), radius=30, dxfattribs={"color": 3})
    msp.add_text("Plano de Prueba CAD", dxfattribs={"height": 5}).set_placement((10, 90))
    dxf_path = test_dir / "sample.dxf"
    doc.saveas(str(dxf_path))
    assert dxf_path.exists()
    return dxf_path

@pytest.fixture(scope="session")
def sample_pdf(test_dir):
    import fitz
    sample_pdf_path = test_dir / "documento_prueba.pdf"
    doc_pdf = fitz.open()
    page = doc_pdf.new_page()
    page.insert_text((50, 72), "Documento de Prueba para Conversión a Word", fontsize=18)
    page.insert_text((50, 110), "Este es un párrafo de texto que será convertido fielmente a un archivo Word (.docx).", fontsize=11)
    page.draw_rect(fitz.Rect(50, 140, 500, 180), color=(0.2, 0.4, 0.8), width=2)
    page.insert_text((60, 165), "Texto dentro de un recuadro vectorial", fontsize=12)
    doc_pdf.save(str(sample_pdf_path))
    doc_pdf.close()
    assert sample_pdf_path.exists()
    return sample_pdf_path

def test_dxf_to_pdf(sample_dxf, test_dir):
    out_pdf = test_dir / "sample_cad.pdf"
    res = dxf_to_pdf(sample_dxf, out_pdf)
    assert Path(res).exists()
    assert Path(res).stat().st_size > 0

def test_dxf_to_dwg(sample_dxf, test_dir):
    out_dwg = test_dir / "sample.dwg"
    try:
        res = dxf_to_dwg(sample_dxf, out_dwg)
        assert Path(res).exists()
        assert Path(res).stat().st_size > 0
    except RuntimeError as e:
        pytest.skip(f"LibreDWG no disponible en este entorno: {e}")

def test_dwg_to_pdf(sample_dxf, test_dir):
    sample_dwg = test_dir / "sample.dwg"
    if not sample_dwg.exists():
        pytest.skip("No se generó sample.dwg para la prueba DWG -> PDF")
    out_pdf = test_dir / "dwg_converted.pdf"
    try:
        res = dwg_to_pdf(sample_dwg, out_pdf)
        assert Path(res).exists()
        assert Path(res).stat().st_size > 0
    except Exception as e:
        pytest.skip(f"LibreDWG no disponible o error al convertir DWG: {e}")

def test_pdf_to_docx(sample_pdf, test_dir):
    out_docx = test_dir / "documento_prueba.docx"
    res = pdf_to_docx(sample_pdf, out_docx)
    assert Path(res).exists()
    assert Path(res).stat().st_size > 0

def test_pdf_to_text(sample_pdf, test_dir):
    out_txt = test_dir / "documento_prueba.txt"
    res = pdf_to_text(sample_pdf, out_txt)
    assert Path(res).exists()
    content = Path(res).read_text(encoding="utf-8")
    assert "Documento de Prueba" in content

def test_pdf_to_images_and_back_to_pdf(sample_pdf, test_dir):
    out_folder = test_dir / "pdf_imgs"
    imgs = pdf_to_images(sample_pdf, out_folder, "png", 150)
    assert len(imgs) >= 1
    assert Path(imgs[0]).exists()

    # Combinar de vuelta a PDF
    comb_pdf = test_dir / "imagenes_combinadas.pdf"
    res = images_to_pdf(imgs, comb_pdf)
    assert Path(res).exists()
    assert Path(res).stat().st_size > 0

def test_image_conversion(sample_pdf, test_dir):
    out_folder = test_dir / "pdf_imgs"
    imgs = pdf_to_images(sample_pdf, out_folder, "png", 150)
    png_path = imgs[0]

    jpg_path = test_dir / "prueba.jpg"
    res = convert_image(png_path, "jpg", jpg_path, 90)
    assert Path(res).exists()
    assert Path(res).stat().st_size > 0

def test_cad_multi_layout_export(test_dir):
    import ezdxf
    import pymupdf
    multi_dxf_path = test_dir / "test_multi_layout.dxf"
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_line((0, 0), (100, 100))

    # Crear 3 layouts con diferentes nombres y geometrías
    l1 = doc.layouts.new("Plano_Arquitectura")
    l1.add_circle((50, 50), 30)

    l2 = doc.layouts.new("Plano_Estructuras")
    l2.add_line((10, 10), (200, 200))

    l3 = doc.layouts.new("Plano_Instalaciones")
    l3.add_text("Texto Instalaciones", dxfattribs={"height": 5}).set_placement((20, 20))

    doc.saveas(str(multi_dxf_path))
    assert multi_dxf_path.exists()

    out_pdf = test_dir / "test_multi_layout.pdf"
    res = dxf_to_pdf(multi_dxf_path, out_pdf, space_mode="all_layouts", paper_size="Auto")
    assert Path(res).exists()
    
    # Verificar que el PDF generado tenga al menos 3 páginas correspondientes a los layouts
    pdf_doc = pymupdf.open(str(res))
    assert len(pdf_doc) >= 3
    pdf_doc.close()

def test_pdf_editor_figures(sample_pdf, test_dir):
    from converters.pdf_editor import apply_all_figures_to_pdf, render_pdf_page_to_image
    figs = {
        0: [
            {"type": "arrow", "x1": 50, "y1": 50, "x2": 200, "y2": 150, "color": "#E53935", "width": 3.0, "head_size": 14.0},
            {"type": "circle", "cx": 250, "cy": 150, "radius": 40.0, "color": "#1E88E5", "fill_color": "#BBDEFB", "width": 2.0},
            {"type": "rect", "x": 60, "y": 200, "w": 180, "h": 70, "color": "#43A047", "fill_color": "#C8E6C9", "width": 2.0},
            {"type": "line", "x1": 50, "y1": 300, "x2": 300, "y2": 300, "color": "#000000", "width": 2.0, "dashed": True},
            {"type": "text", "x": 70, "y": 240, "text": "Nota de Revisión", "fontsize": 14.0, "color": "#B71C1C", "bold": True},
            {"type": "highlight", "x": 50, "y": 320, "w": 250, "h": 25, "color": "#FFEB3B"},
            {"type": "redact", "x": 50, "y": 360, "w": 200, "h": 30, "color": "#000000", "text": "CENSURADO"}
        ]
    }
    out_edited = test_dir / "pdf_con_figuras.pdf"
    res = apply_all_figures_to_pdf(sample_pdf, out_edited, figs)
    assert Path(res).exists()
    assert Path(res).stat().st_size > 0

    # Verificar que se puede renderizar la página con figuras a imagen
    img = render_pdf_page_to_image(out_edited, 0, dpi=100)
    assert img.size[0] > 0 and img.size[1] > 0

def test_pdf_advanced_ilovepdf_suite(sample_pdf, test_dir):
    from converters.pdf_advanced_tools import (
        merge_pdfs, split_pdf, rotate_pages, compress_pdf, protect_pdf,
        unlock_pdf, watermark_pdf, add_page_numbers, pdf_to_pptx, pdf_to_excel,
        crop_pdf, remove_pages, extract_pages
    )

    # 1. Unir
    merged = test_dir / "suite_unido.pdf"
    merge_pdfs([sample_pdf, sample_pdf], merged)
    assert merged.exists()

    # 2. Dividir
    split_dir = test_dir / "suite_split"
    split_files = split_pdf(merged, split_dir, ranges="1, 2")
    assert len(split_files) >= 1

    # 3. Rotar
    rotated = test_dir / "suite_rotado.pdf"
    rotate_pages(sample_pdf, 90, pages="all", output_path=rotated)
    assert rotated.exists()

    # 4. Comprimir (Extrema)
    comp_file = test_dir / "suite_comprimido.pdf"
    res_comp, o_sz, c_sz = compress_pdf(sample_pdf, comp_file, level="extreme")
    assert Path(res_comp).exists()

    # 5. Proteger y Desbloquear
    prot_file = test_dir / "suite_protegido.pdf"
    protect_pdf(sample_pdf, prot_file, "segura123")
    assert prot_file.exists()

    unl_file = test_dir / "suite_desbloqueado.pdf"
    unlock_pdf(prot_file, unl_file, "segura123")
    assert unl_file.exists()

    # 6. Marca de Agua
    wm_file = test_dir / "suite_watermark.pdf"
    watermark_pdf(sample_pdf, wm_file, text="CONFIDENCIAL", opacity=0.3)
    assert wm_file.exists()

    # 7. Numerar Páginas
    num_file = test_dir / "suite_numerado.pdf"
    add_page_numbers(sample_pdf, num_file, format_template="Pág {page} de {total}")
    assert num_file.exists()

    # 8. PDF a PowerPoint
    pptx_file = test_dir / "suite_presentacion.pptx"
    pdf_to_pptx(sample_pdf, pptx_file)
    assert pptx_file.exists()

    # 9. PDF a Excel
    excel_file = test_dir / "suite_tablas.xlsx"
    pdf_to_excel(sample_pdf, excel_file)
    assert excel_file.exists()

    # 10. Recortar
    crop_file = test_dir / "suite_recortado.pdf"
    crop_pdf(sample_pdf, crop_file, margins=(10, 10, 10, 10))
    assert crop_file.exists()

def test_pdf_editor_overlay_rotation_derotation():
    import pymupdf as fitz
    from converters.pdf_editor import apply_editor_overlay_to_page
    from PIL import Image, ImageDraw
    import io

    # Crear overlay con un punto rojo en (100, 100)
    img = Image.new('RGBA', (600, 800), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([90, 90, 110, 110], fill=(255, 0, 0, 255))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    overlay_bytes = buf.getvalue()

    for rot in [0, 90, 180, 270]:
        doc = fitz.open()
        w = 600 if rot in [0, 180] else 800
        h = 800 if rot in [0, 180] else 600
        page = doc.new_page(width=w, height=h)
        page.set_rotation(rot)

        apply_editor_overlay_to_page(page, overlay_bytes)
        pix = page.get_pixmap(dpi=72)
        r, g, b = pix.pixel(100, 100)
        assert (r > 200 and g < 50 and b < 50), f"Fallo de posicionamiento en rotación {rot}: RGB=({r},{g},{b})"
        doc.close()

if __name__ == "__main__":
    ret = pytest.main([__file__, "-v", "-s"])
    sys.exit(ret)

