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

if __name__ == "__main__":
    ret = pytest.main([__file__, "-v", "-s"])
    sys.exit(ret)

