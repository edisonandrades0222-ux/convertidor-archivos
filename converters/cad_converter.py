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

_ENTITYDB_PATCHED = False

def _patch_entitydb():
    global _ENTITYDB_PATCHED
    if _ENTITYDB_PATCHED:
        return
    try:
        from ezdxf import entitydb
        orig_add = entitydb.EntityDB.add
        def patched_add(self, entity):
            if hasattr(entity, 'dxf') and getattr(entity.dxf, 'handle', None) == '0':
                entity.dxf.handle = self.next_handle()
            return orig_add(self, entity)
        entitydb.EntityDB.add = patched_add
        _ENTITYDB_PATCHED = True
    except Exception:
        pass

def load_dxf_document(dxf_path):
    """
    Carga un archivo DXF de forma ultra tolerante a errores, caracteres especiales,
    codificaciones heredadas (ANSI, CP1252, ISO-8859-1) y entidades incompletas.
    """
    _patch_entitydb()
    ensure_ezdxf_fonts()
    import ezdxf
    from ezdxf import recover

    dxf_path = Path(dxf_path)
    doc = None

    # Intento 1: recover con surrogateescape (maxima reparacion automatica)
    try:
        doc, auditor = recover.readfile(str(dxf_path), errors="surrogateescape")
    except Exception:
        pass

    # Intento 2: recover con ignore
    if doc is None:
        try:
            doc, auditor = recover.readfile(str(dxf_path), errors="ignore")
        except Exception:
            pass

    # Intento 3: ezdxf.readfile directo
    if doc is None:
        try:
            doc = ezdxf.readfile(str(dxf_path), errors="ignore")
        except Exception:
            pass

    # Intento 4: forzar codificaciones comunes en planos en espanol
    if doc is None:
        for enc in ["cp1252", "latin1", "iso-8859-1", "utf-8"]:
            try:
                doc = ezdxf.readfile(str(dxf_path), encoding=enc, errors="ignore")
                break
            except Exception:
                pass

    if doc is None:
        raise RuntimeError(f"No se pudo decodificar el archivo CAD '{dxf_path.name}'. Formato no reconocido o dañado.")

    # Desbloquear capas para que sus geometrias se puedan leer sin restriccion
    try:
        for lay in doc.layers:
            try:
                lay.unlock()
            except Exception:
                pass
    except Exception:
        pass

    return doc

def get_cad_layout_names(dxf_or_dwg_path):
    """
    Retorna la lista de nombres de todos los layouts (láminas) disponibles
    en orden de visualización de AutoCAD (taborder).
    """
    p = Path(dxf_or_dwg_path)
    temp_dxf = None
    try:
        if p.suffix.lower() == ".dwg":
            temp_dxf = p.parent / f"__temp_inspect_{p.stem}.dxf"
            dwg_to_dxf(p, temp_dxf)
            doc = load_dxf_document(temp_dxf)
        else:
            doc = load_dxf_document(p)

        paper_layouts = [lay for lay in doc.layouts if getattr(lay, 'is_any_paperspace', False)]
        paper_layouts.sort(key=lambda l: getattr(getattr(l, 'dxf', None), 'taborder', 0))
        return [l.name for l in paper_layouts]
    except Exception:
        return []
    finally:
        if temp_dxf and temp_dxf.exists():
            try: temp_dxf.unlink()
            except Exception: pass

def _get_page_for_layout(lay, paper_size="Auto", orientation="landscape"):
    """
    Calcula el tamaño de página para un layout individual.
    Si paper_size == 'Auto', extrae las dimensiones exactas configuradas en AutoCAD (A0, A1, A2, etc.).
    """
    from ezdxf.addons.drawing import layout
    if paper_size == "Auto":
        try:
            p = layout.Page.from_dxf_layout(lay)
            if p and p.width_in_mm > 20 and p.height_in_mm > 20:
                return p
        except Exception:
            pass

    dims = PAPER_SIZES.get(paper_size, PAPER_SIZES["A3"])
    w, h = dims
    if orientation == "portrait":
        return layout.Page(min(w, h), max(w, h))
    else:
        return layout.Page(max(w, h), min(w, h))

def _get_target_layouts(doc, space_mode="all_layouts", specific_layout=None, progress_callback=None):
    """
    Determina la lista completa de layouts a procesar, respetando el orden de pestañas de AutoCAD.
    """
    if space_mode == "model":
        if progress_callback:
            progress_callback("Exportando contenido del Espacio Modelo...")
        return [doc.modelspace()]

    # Obtener todas las láminas paperspace
    paper_layouts = [lay for lay in doc.layouts if getattr(lay, 'is_any_paperspace', False)]
    # Ordenar por el orden de pestañas de AutoCAD
    paper_layouts.sort(key=lambda l: getattr(getattr(l, 'dxf', None), 'taborder', 0))

    if specific_layout:
        for lay in paper_layouts:
            if lay.name.lower() == str(specific_layout).strip().lower():
                if progress_callback:
                    progress_callback(f"Exportando lámina específica: '{lay.name}'")
                return [lay]

    if space_mode == "all_layouts":
        if len(paper_layouts) > 0:
            if progress_callback:
                progress_callback(f"Se exportarán {len(paper_layouts)} láminas: {', '.join([l.name for l in paper_layouts[:4]])}{'...' if len(paper_layouts) > 4 else ''}")
            return paper_layouts
        if progress_callback:
            progress_callback("No se detectaron láminas de presentación; exportando Espacio Modelo...")
        return [doc.modelspace()]

    # space_mode == "layout" (primera lámina)
    if len(paper_layouts) > 0:
        if progress_callback:
            progress_callback(f"Exportando lámina: '{paper_layouts[0].name}'")
        return [paper_layouts[0]]

    return [doc.modelspace()]

def dxf_to_pdf(
    dxf_path,
    output_pdf_path=None,
    space_mode="all_layouts",
    specific_layout=None,
    color_mode="monochrome",
    lineweight_scale=0.5,
    paper_size="Auto",
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

    target_layouts = _get_target_layouts(doc, space_mode, specific_layout, progress_callback)
    total_layouts = len(target_layouts)

    def _render_layout(lay_to_draw):
        page_to_use = _get_page_for_layout(lay_to_draw, paper_size, orientation)

        # 1. Intentar PyMuPdfBackend (motor vectorial ultra nítido y rápido)
        try:
            backend = PyMuPdfBackend()
            frontend = Frontend(ctx, backend, config=cfg)
            frontend.draw_layout(lay_to_draw, finalize=True)
            if len(backend.records) > 0:
                pdf_b = backend.get_pdf_bytes(page_to_use)
                if pdf_b and len(pdf_b) > 200:
                    return pdf_b
        except Exception:
            pass

        # 1b. Si falló, intentar PyMuPdfBackend con filtro seguro de entidades
        try:
            backend = PyMuPdfBackend()
            frontend = Frontend(ctx, backend, config=cfg)
            def safe_filter(e):
                try:
                    return getattr(e, 'is_alive', True)
                except Exception:
                    return False
            frontend.draw_layout(lay_to_draw, finalize=True, filter_func=safe_filter)
            if len(backend.records) > 0:
                pdf_b = backend.get_pdf_bytes(page_to_use)
                if pdf_b and len(pdf_b) > 200:
                    return pdf_b
        except Exception:
            pass

        # 2. Fallback con MatplotlibBackend (modo headless Agg)
        try:
            import matplotlib
            matplotlib.use('Agg')
            from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
            import matplotlib.pyplot as plt
            from io import BytesIO

            w_mm = getattr(page_to_use, 'width_in_mm', 420)
            h_mm = getattr(page_to_use, 'height_in_mm', 297)
            fig = plt.figure(figsize=(w_mm / 25.4, h_mm / 25.4))
            ax = fig.add_axes([0.01, 0.01, 0.98, 0.98])
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

        # 3. Si la lámina está vacía o no se pudo renderizar, crear página informativa
        try:
            doc_placeholder = pymupdf.open()
            w_pt = getattr(page_to_use, 'width_in_mm', 420) * 72.0 / 25.4
            h_pt = getattr(page_to_use, 'height_in_mm', 297) * 72.0 / 25.4
            page_p = doc_placeholder.new_page(width=w_pt, height=h_pt)
            lay_name = getattr(lay_to_draw, 'name', 'Lámina')
            page_p.insert_text((50, 72), f"Lámina: {lay_name}", fontsize=16)
            page_p.insert_text((50, 100), "(Esta lámina no contiene entidades vectoriales visibles o está vacía)", fontsize=10)
            buf = doc_placeholder.tobytes()
            doc_placeholder.close()
            return buf
        except Exception:
            return None

    pdf_doc = pymupdf.open()
    for idx, lay in enumerate(target_layouts):
        lay_name = getattr(lay, 'name', f'Lámina {idx+1}')
        if progress_callback:
            progress_callback(f"Renderizando lámina [{idx+1}/{total_layouts}]: '{lay_name}'...")
        b = _render_layout(lay)
        if b:
            try:
                temp_doc = pymupdf.open("pdf", b)
                if len(temp_doc) > 0:
                    pdf_doc.insert_pdf(temp_doc)
                temp_doc.close()
            except Exception:
                pass

    # Si por alguna razón ninguna lámina produjo contenido, exportar el Modelo
    if len(pdf_doc) == 0:
        if progress_callback:
            progress_callback("Extrayendo geometría de Espacio Modelo de respaldo...")
        b_model = _render_layout(doc.modelspace())
        if b_model:
            try:
                temp_doc = pymupdf.open("pdf", b_model)
                if len(temp_doc) > 0:
                    pdf_doc.insert_pdf(temp_doc)
                temp_doc.close()
            except Exception:
                pass

    if len(pdf_doc) == 0:
        pdf_doc.close()
        raise RuntimeError("El archivo CAD no contiene geometría vectorial legible para exportar.")

    pdf_doc.save(str(output_pdf_path))
    pdf_doc.close()

    if progress_callback:
        progress_callback(f"PDF generado exitosamente ({total_layouts} páginas): {output_pdf_path.name}")
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
    
    # Intentos de conversión: nativa, r2010, r2000, r2004
    attempts = [
        [exe, "-y", "-o", str(output_dxf_path), str(dwg_path)],
        [exe, "-y", "--as", "r2010", "-o", str(output_dxf_path), str(dwg_path)],
        [exe, "-y", "--as", "r2000", "-o", str(output_dxf_path), str(dwg_path)],
        [exe, "-y", "--as", "r2004", "-o", str(output_dxf_path), str(dwg_path)],
    ]
    
    success = False
    for cmd in attempts:
        try:
            if output_dxf_path.exists():
                try: output_dxf_path.unlink()
                except Exception: pass
            
            subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                env=get_linux_env(), timeout=90,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            if output_dxf_path.exists() and output_dxf_path.stat().st_size > 500:
                # Comprobar que el DXF producido sea válido
                try:
                    test_doc = load_dxf_document(output_dxf_path)
                    if test_doc is not None:
                        success = True
                        break
                except Exception:
                    pass
        except Exception:
            pass

    if not success or not output_dxf_path.exists() or output_dxf_path.stat().st_size == 0:
        raise RuntimeError(f"No se pudo extraer geometría del archivo DWG ({dwg_path.name}).")
    if progress_callback:
        progress_callback(f"DXF generado exitosamente: {output_dxf_path.name}")
    return str(output_dxf_path)

def dwg_to_pdf(
    dwg_path, output_pdf_path=None,
    space_mode="all_layouts", specific_layout=None, color_mode="monochrome",
    lineweight_scale=0.5, paper_size="Auto", orientation="landscape",
    progress_callback=None
):
    """
    Convierte un archivo DWG a PDF vectorial con garantias de no omitir laminas:
    1. Extrae todas las capas y geometrias DWG -> DXF con LibreDWG (con fallbacks compatibles).
    2. Renderiza todas las laminas o la lamina seleccionada.
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
            space_mode=space_mode, specific_layout=specific_layout,
            color_mode=color_mode, lineweight_scale=lineweight_scale,
            paper_size=paper_size, orientation=orientation,
            progress_callback=progress_callback
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
