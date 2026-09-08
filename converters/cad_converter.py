import os
import shutil
import subprocess
from pathlib import Path
import pymupdf
from converters.dwg_setup import (
    get_dwg2dxf_path,
    ensure_libredwg,
    get_linux_env,
    BIN_DIR
)

PAPER_SIZES = {
    "A0": (1189, 841),
    "A1": (841, 594),
    "A2": (594, 420),
    "A3": (420, 297),
    "A4": (297, 210),
    "Carta": (279, 216),
    "Oficio": (356, 216),
    "Auto": (420, 297)
}

def get_dxf2dwg_path():
    if os.name != 'nt':
        return shutil.which("dxf2dwg")
    p = BIN_DIR / "dxf2dwg.exe"
    if p.is_file():
        return str(p)
    return shutil.which("dxf2dwg.exe") or shutil.which("dxf2dwg")

_FONTS_SCANNED = False

def ensure_ezdxf_fonts():
    """
    Garantiza que ezdxf tenga fuentes TrueType disponibles en cualquier entorno
    (especialmente en Linux / Streamlit Community Cloud donde no hay fuentes del sistema instaladas).
    """
    global _FONTS_SCANNED
    if _FONTS_SCANNED:
        return

    try:
        from ezdxf.fonts import fonts
        fm = fonts.font_manager
        # 1. Carpeta local fonts/ en el proyecto
        proj_fonts = Path(__file__).resolve().parent.parent / "fonts"
        if proj_fonts.is_dir():
            try:
                fm.scan_folder(proj_fonts)
            except Exception:
                pass
        
        # 2. Fuentes empaquetadas en matplotlib
        try:
            import matplotlib
            mpl_ttf = Path(matplotlib.__file__).parent / "mpl-data" / "fonts" / "ttf"
            if mpl_ttf.is_dir():
                fm.scan_folder(mpl_ttf)
        except Exception:
            pass
        _FONTS_SCANNED = True
    except Exception:
        pass

# Inicializar fuentes al cargar el modulo
ensure_ezdxf_fonts()

def load_dxf_document(dxf_path):
    ensure_ezdxf_fonts()
    import ezdxf
    from ezdxf import entitydb, recover
    
    # Parche de compatibilidad con LibreDWG para handles "0"
    orig_add = entitydb.EntityDB.add
    def patched_add(self, entity):
        if hasattr(entity, 'dxf') and getattr(entity.dxf, 'handle', None) == '0':
            entity.dxf.handle = self.next_handle()
        return orig_add(self, entity)
    entitydb.EntityDB.add = patched_add

    try:
        doc, auditor = recover.readfile(str(dxf_path))
    except Exception:
        doc = ezdxf.readfile(str(dxf_path))

    # Visibilidad total: activar, descongelar y desbloquear todas las capas del plano
    try:
        for lay in doc.layers:
            lay.on()
            lay.thaw()
            lay.unlock()
    except Exception:
        pass

    return doc

def _get_page(paper_size="A3", orientation="landscape"):
    from ezdxf.addons.drawing import layout
    dims = PAPER_SIZES.get(paper_size, PAPER_SIZES["A3"])
    w, h = dims
    if orientation == "portrait":
        return layout.Page(min(w, h), max(w, h))
    else:
        return layout.Page(max(w, h), min(w, h))

def _is_doc_blank(pdf_bytes):
    """Verifica si el documento PDF renderizado quedo completamente en blanco."""
    try:
        temp = pymupdf.open("pdf", pdf_bytes)
        for page in temp:
            pix = page.get_pixmap(dpi=72)
            # Si hay algun pixel que no sea blanco (255), tiene contenido
            for s in pix.samples:
                if s != 255:
                    temp.close()
                    return False
        temp.close()
        return True
    except Exception:
        return False

def _get_target_layouts(doc, space_mode="layout", progress_callback=None):
    if space_mode == "model":
        return [doc.modelspace()]

    paper_layouts = [lay for lay in doc.layouts if getattr(lay, 'is_any_paperspace', False)]

    # Filtrar solo layouts que contengan entidades
    non_empty_papers = []
    for lay in paper_layouts:
        try:
            if len(list(lay)) > 0:
                non_empty_papers.append(lay)
        except Exception:
            pass

    if space_mode == "all_layouts":
        if len(non_empty_papers) > 0:
            return non_empty_papers
        if len(paper_layouts) > 0:
            return paper_layouts
        return [doc.modelspace()]

    if len(non_empty_papers) > 0:
        if progress_callback:
            progress_callback(f"Seleccionado Layout: '{non_empty_papers[0].name}'")
        return [non_empty_papers[0]]

    # Si los layouts no tienen entidades, usar espacio modelo
    try:
        msp = doc.modelspace()
        if len(list(msp)) > 0:
            if progress_callback:
                progress_callback("Layout vacio; exportando contenido de Espacio Modelo...")
            return [msp]
    except Exception:
        pass

    if len(paper_layouts) > 0:
        return [paper_layouts[0]]
    return [doc.modelspace()]

def dxf_to_pdf(
    dxf_path,
    output_pdf_path=None,
    space_mode="layout",
    color_mode="monochrome",
    lineweight_scale=0.5,
    paper_size="A3",
    orientation="landscape",
    progress_callback=None
):
    from ezdxf.addons.drawing import Frontend, RenderContext
    from ezdxf.addons.drawing.config import Configuration, ColorPolicy
    from ezdxf.addons.drawing.pymupdf import PyMuPdfBackend

    dxf_path = Path(dxf_path)
    if not output_pdf_path:
        output_pdf_path = dxf_path.with_suffix(".pdf")
    else:
        output_pdf_path = Path(output_pdf_path)
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    if progress_callback:
        progress_callback(f"Cargando plano CAD: {dxf_path.name}...")

    doc = load_dxf_document(dxf_path)
    ctx = RenderContext(doc)

    c_policy = ColorPolicy.BLACK if color_mode == "monochrome" else ColorPolicy.COLOR
    cfg = Configuration(
        color_policy=c_policy,
        lineweight_scaling=float(lineweight_scale),
        min_lineweight=0.01 if float(lineweight_scale) <= 0.5 else 0.05
    )

    page = _get_page(paper_size, orientation)
    target_layouts = _get_target_layouts(doc, space_mode, progress_callback)

    if progress_callback:
        mode_txt = "Monocromatico" if color_mode == "monochrome" else "Color"
        progress_callback(f"Renderizando vectorialmente [{mode_txt} | Grosor {lineweight_scale}x | {paper_size}]...")

    def _render_layout(lay_to_draw):
        # 1. Intentar con PyMuPdfBackend (motor vectorial de alta velocidad)
        try:
            backend = PyMuPdfBackend()
            frontend = Frontend(ctx, backend, config=cfg)
            frontend.draw_layout(lay_to_draw, finalize=True)
            if len(backend.records) > 0:
                pdf_b = backend.get_pdf_bytes(page)
                if pdf_b and len(pdf_b) > 200:
                    return pdf_b
        except Exception:
            pass

        # 2. Fallback con MatplotlibBackend (modo headless Agg para Linux sin display)
        try:
            import matplotlib
            matplotlib.use('Agg')
            from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
            import matplotlib.pyplot as plt
            from io import BytesIO

            w_mm = getattr(page, 'width_in_mm', 420)
            h_mm = getattr(page, 'height_in_mm', 297)
            fig = plt.figure(figsize=(w_mm / 25.4, h_mm / 25.4))
            ax = fig.add_axes([0.02, 0.02, 0.96, 0.96])
            ax.axis('off')
            out = MatplotlibBackend(ax)
            frontend = Frontend(ctx, out, config=cfg)
            frontend.draw_layout(lay_to_draw, finalize=True)

            buf = BytesIO()
            fig.savefig(buf, format='pdf', dpi=150)
            plt.close(fig)
            pdf_b = buf.getvalue()
            if pdf_b and len(pdf_b) > 500:
                return pdf_b
        except Exception:
            pass

        return None

    pdf_doc = pymupdf.open()
    for lay in target_layouts:
        b = _render_layout(lay)
        if b:
            try:
                temp_doc = pymupdf.open("pdf", b)
                if len(temp_doc) > 0:
                    pdf_doc.insert_pdf(temp_doc)
                temp_doc.close()
            except Exception:
                pass

    # Si los layouts quedaron en blanco o vacios, exportar obligatoriamente el Modelo
    if len(pdf_doc) == 0:
        if progress_callback:
            progress_callback("Extrayendo geometria de Espacio Modelo...")
        b_model = _render_layout(doc.modelspace())
        if b_model:
            try:
                temp_doc = pymupdf.open("pdf", b_model)
                if len(temp_doc) > 0:
                    pdf_doc.insert_pdf(temp_doc)
                temp_doc.close()
            except Exception:
                pass

    # Respaldo final: iterar cualquier layout del archivo si todavia no hay paginas
    if len(pdf_doc) == 0:
        for lay in doc.layouts:
            b_alt = _render_layout(lay)
            if b_alt:
                try:
                    temp_doc = pymupdf.open("pdf", b_alt)
                    if len(temp_doc) > 0:
                        pdf_doc.insert_pdf(temp_doc)
                        temp_doc.close()
                        break
                except Exception:
                    pass

    if len(pdf_doc) == 0:
        pdf_doc.close()
        raise RuntimeError("El archivo CAD no contiene geometria vectorial visible para exportar.")

    pdf_doc.save(str(output_pdf_path))
    pdf_doc.close()

    if progress_callback:
        progress_callback(f"PDF generado exitosamente: {output_pdf_path.name}")
    return str(output_pdf_path)

def dwg_to_dxf(dwg_path, output_dxf_path=None, progress_callback=None):
    dwg_path = Path(dwg_path)
    if not output_dxf_path:
        output_dxf_path = dwg_path.with_suffix(".dxf")
    else:
        output_dxf_path = Path(output_dxf_path)
    output_dxf_path.parent.mkdir(parents=True, exist_ok=True)
    ensure_libredwg(progress_callback)
    exe = get_dwg2dxf_path()
    if not exe:
        raise RuntimeError("No se encontro el conversor dwg2dxf para procesar el archivo DWG.")
    if progress_callback:
        progress_callback(f"Extrayendo entidades DWG -> DXF ({dwg_path.name})...")
    
    # Intentar conversion estandar primero
    cmd = [exe, "-y", "-o", str(output_dxf_path), str(dwg_path)]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                   env=get_linux_env(),
                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                   
    # Fallback a versiones compatibles si falla
    if not output_dxf_path.exists() or output_dxf_path.stat().st_size == 0:
        cmd_fb = [exe, "-y", "--as", "r2010", "-o", str(output_dxf_path), str(dwg_path)]
        subprocess.run(cmd_fb, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                       env=get_linux_env(),
                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                       
    if not output_dxf_path.exists() or output_dxf_path.stat().st_size == 0:
        cmd_r2 = [exe, "-y", "--as", "r2000", "-o", str(output_dxf_path), str(dwg_path)]
        subprocess.run(cmd_r2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                       env=get_linux_env(),
                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

    if not output_dxf_path.exists() or output_dxf_path.stat().st_size == 0:
        raise RuntimeError("No se pudo extraer geometria del archivo DWG.")
    if progress_callback:
        progress_callback(f"DXF generado: {output_dxf_path.name}")
    return str(output_dxf_path)

def dwg_to_pdf(
    dwg_path, output_pdf_path=None,
    space_mode="layout", color_mode="monochrome",
    lineweight_scale=0.5, paper_size="A3", orientation="landscape",
    progress_callback=None
):
    """
    Convierte un archivo DWG a PDF vectorial con garantias de no dejar paginas en blanco:
    1. Extrae todas las capas y geometrias DWG -> DXF con LibreDWG.
    2. Renderiza el Layout seleccionado o el Espacio Modelo con el motor vectorial de PyMuPDF.
    3. Si un Layout esta vacio o blanco, conmuta automaticamente al Espacio Modelo para no entregar un PDF en blanco.
    """
    dwg_path = Path(dwg_path)
    if not output_pdf_path:
        output_pdf_path = dwg_path.with_suffix(".pdf")
    else:
        output_pdf_path = Path(output_pdf_path)

    temp_dxf = dwg_path.parent / f"__temp_{dwg_path.stem}.dxf"
    try:
        dwg_to_dxf(dwg_path, temp_dxf, progress_callback)
        result_pdf = dxf_to_pdf(
            temp_dxf, output_pdf_path,
            space_mode=space_mode, color_mode=color_mode,
            lineweight_scale=lineweight_scale, paper_size=paper_size,
            orientation=orientation, progress_callback=progress_callback
        )
        return result_pdf
    finally:
        if temp_dxf.exists():
            try: temp_dxf.unlink()
            except: pass

def dxf_to_dwg(dxf_path, output_dwg_path=None, progress_callback=None):
    dxf_path = Path(dxf_path)
    if not output_dwg_path:
        output_dwg_path = dxf_path.with_suffix(".dwg")
    else:
        output_dwg_path = Path(output_dwg_path)
    output_dwg_path.parent.mkdir(parents=True, exist_ok=True)
    ensure_libredwg(progress_callback)
    exe = get_dxf2dwg_path()
    if not exe:
        raise RuntimeError("No se encontro dxf2dwg en bin/.")
    if progress_callback:
        progress_callback(f"Convirtiendo DXF -> DWG ({dxf_path.name})...")
    cmd = [exe, "-y", "-o", str(output_dwg_path), str(dxf_path)]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                   env=get_linux_env(),
                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    if not output_dwg_path.exists():
        raise RuntimeError("Error al generar DWG.")
    if progress_callback:
        progress_callback(f"DWG creado: {output_dwg_path.name}")
    return str(output_dwg_path)

def dxf_to_image(dxf_path, output_img_path=None, img_format="png", dpi=300, progress_callback=None):
    from ezdxf.addons.drawing import Frontend, RenderContext
    from ezdxf.addons.drawing.config import Configuration, ColorPolicy
    from ezdxf.addons.drawing.pymupdf import PyMuPdfBackend

    dxf_path = Path(dxf_path)
    if not output_img_path:
        output_img_path = dxf_path.with_suffix(f".{img_format.lower()}")
    else:
        output_img_path = Path(output_img_path)

    doc = load_dxf_document(dxf_path)
    page = _get_page("A3", "landscape")
    ctx = RenderContext(doc)
    cfg = Configuration(color_policy=ColorPolicy.BLACK, lineweight_scaling=0.5)
    backend = PyMuPdfBackend()
    frontend = Frontend(ctx, backend, config=cfg)
    frontend.draw_layout(doc.modelspace(), finalize=True)
    img_bytes = backend.get_pixmap_bytes(page, fmt=img_format, dpi=dpi)
    with open(str(output_img_path), "wb") as f:
        f.write(img_bytes)
    if progress_callback:
        progress_callback(f"Imagen CAD exportada: {output_img_path.name}")
    return str(output_img_path)
