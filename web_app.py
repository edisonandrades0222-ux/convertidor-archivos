import os
import sys
import tempfile
import shutil
import io
from pathlib import Path
import streamlit as st
from PIL import Image

# Configurar path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Importar conversores y herramientas del sistema
from converters.cad_converter import (
    dwg_to_pdf, dwg_to_dxf, dxf_to_pdf, dxf_to_dwg, dxf_to_image,
    ensure_ezdxf_fonts
)
from converters.pdf_converter import pdf_to_docx, pdf_to_images, images_to_pdf, pdf_to_text
from converters.image_converter import convert_image
from converters.pdf_editor import (
    render_pdf_page_to_image, apply_all_figures_to_pdf,
    draw_vector_arrow, draw_vector_circle, draw_vector_rect,
    draw_vector_line, add_vector_text, add_permanent_redaction, add_image_overlay
)
from converters.pdf_advanced_tools import (
    merge_pdfs, split_pdf, remove_pages, extract_pages, rotate_pages,
    compress_pdf, protect_pdf, unlock_pdf, watermark_pdf, add_page_numbers,
    pdf_to_pptx, pdf_to_excel, crop_pdf
)
from converters.gemini_pdf_assistant import (
    get_gemini_client, gemini_ocr_pdf, gemini_summarize_pdf,
    gemini_chat_with_pdf, gemini_translate_pdf_text
)

# Garantizar fuentes disponibles de forma eficiente
@st.cache_resource
def init_fonts():
    ensure_ezdxf_fonts()
    return True

init_fonts()

st.set_page_config(
    page_title="Universal PDF & CAD Suite - iLovePDF Pro Gratuito",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #FF4B4B, #1E88E5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    .badge-pro {
        background-color: #2e7d32;
        color: white;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: bold;
        text-transform: uppercase;
        margin-left: 6px;
    }
    .badge-gemini {
        background: linear-gradient(90deg, #4285F4, #9B51E0);
        color: white;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: bold;
        margin-left: 6px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
        border-radius: 6px 6px 0 0;
        padding: 10px 16px;
    }
</style>
""", unsafe_allow_html=True)

# Encabezado principal
col_t1, col_t2 = st.columns([4, 1])
with col_t1:
    st.markdown('<div class="main-title">⚡ Universal PDF & CAD Suite</div>', unsafe_allow_html=True)
    st.markdown("##### Editor de PDF con Figuras (Flechas, Círculos, Cuadros) & Suite Completa iLovePDF Pro 100% Gratuita")
with col_t2:
    gemini_active = get_gemini_client() is not None
    if gemini_active:
        st.markdown('<span class="badge-gemini">✨ Gemini 3.8 Flash Activo</span>', unsafe_allow_html=True)
    else:
        st.caption("⚠️ Gemini API sin clave")

st.markdown("---")

# Estructura en 5 pestañas principales
tabs = st.tabs([
    "🎨 1. Editar PDF (Figuras y Flechas)",
    "⚡ 2. Convertidor Universal",
    "📑 3. Organizar y Optimizar",
    "🔒 4. Seguridad y Herramientas Pro",
    "🤖 5. Asistente Gemini AI"
])

# =========================================================================
# PESTAÑA 1: EDITAR PDF (FIGURAS, FLECHAS, CÍRCULOS, RECTÁNGULOS, TEXTOS)
# =========================================================================
with tabs[0]:
    st.header("🎨 Editor de PDF con Figuras Vectoriales")
    st.caption("Inserta flechas, círculos, rectángulos, notas de texto, censura permanente (redaction) o sellos con previsualización en tiempo real.")

    edit_uploaded = st.file_uploader(
        "Carga el PDF que deseas editar:",
        type=["pdf"],
        key="editor_pdf_uploader"
    )

    if edit_uploaded:
        pdf_bytes = edit_uploaded.getvalue()
        
        # Inicializar sesión de figuras si no existe
        if "pdf_figures" not in st.session_state:
            st.session_state["pdf_figures"] = {}

        import pymupdf as fitz
        temp_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_p = len(temp_doc)

        col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
        with col_p2:
            current_page = st.number_input(
                f"Página a editar (Total: {total_p}):", 
                min_value=1, 
                max_value=total_p, 
                value=1,
                step=1
            ) - 1

        curr_page_obj = temp_doc[current_page]
        page_w = float(curr_page_obj.rect.width)
        page_h = float(curr_page_obj.rect.height)
        temp_doc.close()

        if current_page not in st.session_state["pdf_figures"]:
            st.session_state["pdf_figures"][current_page] = []

        col_left, col_right = st.columns([1, 1], gap="medium")

        with col_left:
            st.subheader("🛠️ Herramientas de Figura")
            shape_type = st.selectbox(
                "Tipo de elemento a insertar:",
                [
                    "➡️ Flecha",
                    "⭕ Círculo / Elipse",
                    "⏹️ Rectángulo / Caja",
                    "➖ Línea Recta",
                    "🔤 Texto / Nota",
                    "🖍️ Resaltador",
                    "⬛ Censura Permanente (Redact)",
                    "🖋️ Firma / Sello de Imagen"
                ]
            )

            new_elem = None

            # --- FLECHA ---
            if "Flecha" in shape_type:
                st.markdown("**Configuración de la Flecha:**")
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    arrow_mode = st.radio("Modo:", ["Dirección Rápida", "Coordenadas Libres"], horizontal=True)
                    color_arrow = st.color_picker("Color de Flecha:", "#E53935")
                    width_arrow = st.slider("Grosor:", 1.0, 10.0, 3.0, 0.5)
                with col_f2:
                    head_size = st.slider("Tamaño de Punta:", 8.0, 30.0, 14.0, 1.0)
                    opacity_arrow = st.slider("Opacidad:", 0.1, 1.0, 1.0, 0.05)

                if arrow_mode == "Dirección Rápida":
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        orig_x = st.slider("Origen X:", 0.0, page_w, page_w * 0.25, 5.0)
                        orig_y = st.slider("Origen Y:", 0.0, page_h, page_h * 0.25, 5.0)
                    with col_d2:
                        direction = st.selectbox(
                            "Hacia dónde apunta:",
                            ["➡️ Derecha", "⬅️ Izquierda", "⬇️ Abajo", "⬆️ Arriba", "↘️ Diagonal Derecha-Abajo", "↗️ Diagonal Derecha-Arriba"]
                        )
                        length = st.slider("Largo (pt):", 20.0, 350.0, 100.0, 10.0)

                    end_x, end_y = orig_x, orig_y
                    if "Derecha" in direction and "Diagonal" not in direction:
                        end_x = orig_x + length
                    elif "Izquierda" in direction:
                        end_x = orig_x - length
                    elif "Abajo" in direction and "Diagonal" not in direction:
                        end_y = orig_y + length
                    elif "Arriba" in direction and "Diagonal" not in direction:
                        end_y = orig_y - length
                    elif "Derecha-Abajo" in direction:
                        end_x = orig_x + length * 0.707
                        end_y = orig_y + length * 0.707
                    elif "Derecha-Arriba" in direction:
                        end_x = orig_x + length * 0.707
                        end_y = orig_y - length * 0.707

                    new_elem = {
                        "type": "arrow",
                        "x1": orig_x, "y1": orig_y,
                        "x2": end_x, "y2": end_y,
                        "color": color_arrow,
                        "width": width_arrow,
                        "head_size": head_size,
                        "opacity": opacity_arrow
                    }
                else:
                    col_c1, col_c2 = st.columns(2)
                    with col_c1:
                        x1 = st.slider("Punto Inicial X:", 0.0, page_w, 50.0, 5.0)
                        y1 = st.slider("Punto Inicial Y:", 0.0, page_h, 50.0, 5.0)
                    with col_c2:
                        x2 = st.slider("Punta Final X:", 0.0, page_w, 150.0, 5.0)
                        y2 = st.slider("Punta Final Y:", 0.0, page_h, 150.0, 5.0)
                    new_elem = {
                        "type": "arrow",
                        "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                        "color": color_arrow, "width": width_arrow,
                        "head_size": head_size, "opacity": opacity_arrow
                    }

            # --- CÍRCULO / ELIPSE ---
            elif "Círculo" in shape_type:
                st.markdown("**Configuración del Círculo:**")
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    cx = st.slider("Centro X:", 0.0, page_w, page_w * 0.5, 5.0)
                    cy = st.slider("Centro Y:", 0.0, page_h, page_h * 0.5, 5.0)
                    rad = st.slider("Radio:", 10.0, 250.0, 50.0, 5.0)
                with col_c2:
                    color_circle = st.color_picker("Color de Borde:", "#1E88E5")
                    width_circle = st.slider("Grosor de Borde:", 1.0, 10.0, 2.5, 0.5)
                    use_fill = st.checkbox("Relleno Translúcido", value=False)
                    fill_c = st.color_picker("Color de Relleno:", "#90CAF9") if use_fill else None
                    fill_op = st.slider("Opacidad de Relleno:", 0.05, 1.0, 0.3, 0.05) if use_fill else 0.0

                new_elem = {
                    "type": "circle",
                    "cx": cx, "cy": cy, "radius": rad,
                    "color": color_circle,
                    "fill_color": fill_c,
                    "width": width_circle,
                    "fill_opacity": fill_op
                }

            # --- RECTÁNGULO ---
            elif "Rectángulo" in shape_type:
                st.markdown("**Configuración del Rectángulo:**")
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    rx = st.slider("Posición X:", 0.0, page_w, 50.0, 5.0)
                    ry = st.slider("Posición Y:", 0.0, page_h, 50.0, 5.0)
                    rw = st.slider("Ancho:", 20.0, page_w, 150.0, 5.0)
                    rh = st.slider("Alto:", 20.0, page_h, 80.0, 5.0)
                with col_r2:
                    color_rect = st.color_picker("Color de Borde:", "#43A047")
                    width_rect = st.slider("Grosor:", 1.0, 10.0, 2.0, 0.5)
                    use_fill_r = st.checkbox("Relleno Translúcido", value=False, key="rect_fill_check")
                    fill_r_c = st.color_picker("Color de Relleno:", "#A5D6A7") if use_fill_r else None
                    fill_r_op = st.slider("Opacidad de Relleno:", 0.05, 1.0, 0.3, 0.05) if use_fill_r else 0.0

                new_elem = {
                    "type": "rect",
                    "x": rx, "y": ry, "w": rw, "h": rh,
                    "color": color_rect,
                    "fill_color": fill_r_c,
                    "width": width_rect,
                    "fill_opacity": fill_r_op
                }

            # --- LÍNEA ---
            elif "Línea" in shape_type:
                st.markdown("**Configuración de Línea:**")
                col_l1, col_l2 = st.columns(2)
                with col_l1:
                    lx1 = st.slider("X1:", 0.0, page_w, 50.0, 5.0)
                    ly1 = st.slider("Y1:", 0.0, page_h, 100.0, 5.0)
                with col_l2:
                    lx2 = st.slider("X2:", 0.0, page_w, 250.0, 5.0)
                    ly2 = st.slider("Y2:", 0.0, page_h, 100.0, 5.0)
                color_line = st.color_picker("Color:", "#212121")
                width_line = st.slider("Grosor:", 1.0, 10.0, 2.0, 0.5)
                is_dashed = st.checkbox("Línea Punteada", value=False)
                new_elem = {
                    "type": "line",
                    "x1": lx1, "y1": ly1, "x2": lx2, "y2": ly2,
                    "color": color_line, "width": width_line, "dashed": is_dashed
                }

            # --- TEXTO ---
            elif "Texto" in shape_type:
                st.markdown("**Configuración de Texto:**")
                txt_content = st.text_input("Texto a insertar:", "Nota importante de revisión")
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    tx = st.slider("Posición X:", 0.0, page_w, 60.0, 5.0)
                    ty = st.slider("Posición Y (Línea base):", 0.0, page_h, 100.0, 5.0)
                    tsize = st.slider("Tamaño Fuente:", 8, 48, 14)
                with col_t2:
                    tcolor = st.color_picker("Color del Texto:", "#D32F2F")
                    use_bg = st.checkbox("Fondo de color para destacar", value=True)
                    bg_c = st.color_picker("Color de Fondo:", "#FFF9C4") if use_bg else None
                    is_bold = st.checkbox("Negrita", value=True)
                    is_italic = st.checkbox("Cursiva", value=False)

                new_elem = {
                    "type": "text",
                    "x": tx, "y": ty, "text": txt_content,
                    "fontsize": tsize, "color": tcolor,
                    "bg_color": bg_c, "bold": is_bold, "italic": is_italic
                }

            # --- RESALTADOR ---
            elif "Resaltador" in shape_type:
                st.markdown("**Banda de Resaltado:**")
                col_h1, col_h2 = st.columns(2)
                with col_h1:
                    hx = st.slider("X:", 0.0, page_w, 50.0, 5.0)
                    hy = st.slider("Y:", 0.0, page_h, 150.0, 5.0)
                with col_h2:
                    hw = st.slider("Ancho:", 20.0, page_w, 200.0, 5.0)
                    hh = st.slider("Alto:", 10.0, 80.0, 20.0, 2.0)
                hcolor = st.selectbox("Color de resaltado:", ["#FFEB3B (Amarillo)", "#A5D6A7 (Verde)", "#80D8FF (Celeste)", "#F48FB1 (Rosa)"])
                hcolor_hex = hcolor.split()[0]
                new_elem = {
                    "type": "highlight",
                    "x": hx, "y": hy, "w": hw, "h": hh,
                    "color": hcolor_hex
                }

            # --- CENSURA PERMANENTE (REDACT) ---
            elif "Censura" in shape_type:
                st.markdown("**Censura Permanente (Redaction):**")
                st.info("ℹ️ Elimina de raíz e irreversiblemente el texto y gráficos bajo el rectángulo negro.")
                col_red1, col_red2 = st.columns(2)
                with col_red1:
                    cx = st.slider("X:", 0.0, page_w, 50.0, 5.0)
                    cy = st.slider("Y:", 0.0, page_h, 120.0, 5.0)
                with col_red2:
                    cw = st.slider("Ancho:", 20.0, page_w, 180.0, 5.0)
                    ch = st.slider("Alto:", 10.0, 100.0, 30.0, 2.0)
                red_text = st.text_input("Texto de censura (opcional):", "")
                new_elem = {
                    "type": "redact",
                    "x": cx, "y": cy, "w": cw, "h": ch,
                    "color": "#000000", "text": red_text
                }

            # --- FIRMA / SELLO ---
            elif "Firma" in shape_type:
                st.markdown("**Estampar Firma o Sello:**")
                stamp_file = st.file_uploader("Cargar imagen de firma o sello (.png transparente recomendado):", type=["png", "jpg", "jpeg"])
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    sx = st.slider("X:", 0.0, page_w, page_w * 0.6, 5.0)
                    sy = st.slider("Y:", 0.0, page_h, page_h * 0.8, 5.0)
                with col_s2:
                    sw = st.slider("Ancho:", 30.0, 300.0, 120.0, 5.0)
                    sh = st.slider("Alto:", 20.0, 200.0, 60.0, 5.0)
                if stamp_file:
                    new_elem = {
                        "type": "signature",
                        "x": sx, "y": sy, "w": sw, "h": sh,
                        "data": stamp_file.getvalue()
                    }

            # Botones de agregar y gestión
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("➕ Agregar Figura a la Página", type="primary", use_container_width=True):
                    if new_elem:
                        st.session_state["pdf_figures"][current_page].append(new_elem)
                        st.success(f"Figura '{shape_type}' agregada.")
                        st.rerun()
            with col_b2:
                if st.button("↩️ Deshacer última figura", use_container_width=True):
                    if st.session_state["pdf_figures"].get(current_page):
                        st.session_state["pdf_figures"][current_page].pop()
                        st.rerun()

            figs_curr = st.session_state["pdf_figures"].get(current_page, [])
            st.caption(f"📌 Figuras activas en esta página: **{len(figs_curr)}**")

            if figs_curr:
                with st.expander("Ver lista de figuras de esta página"):
                    for idx, f in enumerate(figs_curr):
                        st.write(f"#{idx + 1}: Tipo `{f['type']}` | Color: `{f.get('color', 'N/A')}`")
                    if st.button("🗑️ Borrar todas las figuras de esta página"):
                        st.session_state["pdf_figures"][current_page] = []
                        st.rerun()

            st.markdown("---")
            if st.button("💾 Guardar y Descargar PDF Editado con Figuras", type="primary", use_container_width=True):
                with st.spinner("Generando documento PDF con figuras vectoriales..."):
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f_out:
                        temp_out_p = f_out.name
                    apply_all_figures_to_pdf(pdf_bytes, temp_out_p, st.session_state["pdf_figures"])
                    with open(temp_out_p, "rb") as res_f:
                        edited_bytes = res_f.read()
                    os.unlink(temp_out_p)

                st.success("🎉 ¡PDF generado exitosamente!")
                st.download_button(
                    label="📥 Descargar PDF Editado",
                    data=edited_bytes,
                    file_name=f"{Path(edit_uploaded.name).stem}_editado.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

        with col_right:
            st.subheader(f"👁️ Previsualización en Vivo (Página {current_page + 1} de {total_p})")
            st.caption(f"Dimensiones de página: **{page_w:.1f} x {page_h:.1f} pt** (Aprox. {page_w * 0.3527:.0f} x {page_h * 0.3527:.0f} mm)")

            # Renderizar página con las figuras aplicadas
            preview_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            p_obj = preview_doc[current_page]
            
            # Dibujar temporalmente figuras en la página de preview
            for elem in st.session_state["pdf_figures"].get(current_page, []):
                et = elem.get("type", "")
                if et == "arrow":
                    draw_vector_arrow(p_obj, (elem["x1"], elem["y1"]), (elem["x2"], elem["y2"]),
                                      color=elem.get("color", "#E53935"), width=elem.get("width", 3.0),
                                      head_size=elem.get("head_size", 14.0), opacity=elem.get("opacity", 1.0))
                elif et == "circle":
                    cx, cy, r = elem["cx"], elem["cy"], elem["radius"]
                    draw_vector_circle(p_obj, (cx - r, cy - r, cx + r, cy + r),
                                       color=elem.get("color", "#1E88E5"), fill_color=elem.get("fill_color"),
                                       width=elem.get("width", 2.0), fill_opacity=elem.get("fill_opacity", 0.0))
                elif et == "rect":
                    draw_vector_rect(p_obj, (elem["x"], elem["y"], elem["x"] + elem["w"], elem["y"] + elem["h"]),
                                     color=elem.get("color", "#43A047"), fill_color=elem.get("fill_color"),
                                     width=elem.get("width", 2.0), fill_opacity=elem.get("fill_opacity", 0.0))
                elif et == "line":
                    draw_vector_line(p_obj, (elem["x1"], elem["y1"]), (elem["x2"], elem["y2"]),
                                     color=elem.get("color", "#000000"), width=elem.get("width", 2.0),
                                     dashed=elem.get("dashed", False))
                elif et == "text":
                    add_vector_text(p_obj, (elem["x"], elem["y"]), elem.get("text", ""),
                                    fontsize=elem.get("fontsize", 14.0), color=elem.get("color", "#000000"),
                                    bg_color=elem.get("bg_color"), bold=elem.get("bold", False),
                                    italic=elem.get("italic", False))
                elif et == "highlight":
                    draw_vector_rect(p_obj, (elem["x"], elem["y"], elem["x"] + elem["w"], elem["y"] + elem["h"]),
                                     color=elem.get("color", "#FFEB3B"), fill_color=elem.get("color", "#FFEB3B"),
                                     width=0, opacity=0.5, fill_opacity=0.5)
                elif et == "redact":
                    add_permanent_redaction(p_obj, (elem["x"], elem["y"], elem["x"] + elem["w"], elem["y"] + elem["h"]),
                                           fill_color=elem.get("color", "#000000"), text=elem.get("text", ""))
                elif et == "signature" and elem.get("data"):
                    add_image_overlay(p_obj, (elem["x"], elem["y"], elem["x"] + elem["w"], elem["y"] + elem["h"]), elem["data"])

            pix = p_obj.get_pixmap(dpi=130)
            preview_img = Image.open(io.BytesIO(pix.tobytes("png")))
            preview_doc.close()

            st.image(preview_img, use_container_width=True, caption=f"Página {current_page + 1} renderizada con figuras")

# =========================================================================
# PESTAÑA 2: CONVERTIDOR UNIVERSAL (CAD, OFFICE, IMÁGENES)
# =========================================================================
with tabs[1]:
    st.header("⚡ Convertidor Universal de Archivos")
    st.caption("PDF a Word / Excel / PPTX | AutoCAD DWG / DXF a PDF Vectorial | Imágenes")

    conv_uploaded = st.file_uploader(
        "Selecciona el archivo para convertir:", 
        type=["pdf", "dwg", "dxf", "png", "jpg", "jpeg", "webp", "bmp", "tiff"],
        key="converter_uploader"
    )

    if conv_uploaded:
        fn = conv_uploaded.name
        fext = Path(fn).suffix.lower()
        st.info(f"📄 **Archivo cargado:** `{fn}` ({conv_uploaded.size / 1024:.1f} KB)")

        target_fmt = None
        cad_opts = {}

        if fext == ".pdf":
            target_fmt = st.selectbox(
                "Convertir PDF a:",
                [
                    "Word Editable (.docx)",
                    "Excel con Tablas Estructuradas (.xlsx) ⭐ iLovePDF",
                    "PowerPoint Presentación Diapositivas (.pptx) ⭐ iLovePDF",
                    "Imágenes PNG en ZIP (.png)",
                    "Imágenes JPG en ZIP (.jpg)",
                    "Texto Plano (.txt)"
                ]
            )
        elif fext in [".dwg", ".dxf"]:
            opts = ["Documento PDF Vectorial (.pdf)"]
            if fext == ".dwg":
                opts.append("Plano DXF (.dxf)")
            else:
                opts.extend(["Plano DWG (.dwg)", "Imagen PNG (.png)", "Imagen JPG (.jpg)"])
            target_fmt = st.selectbox("Convertir plano CAD a:", opts)

            if "PDF" in target_fmt:
                with st.expander("📐 Opciones Avanzadas CAD", expanded=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        sc = st.selectbox("Láminas / Layouts:", ["📑 Todos los Layouts", "📄 Solo Primera Lámina", "🗺️ Espacio Modelo"])
                        colr = st.selectbox("Estilo de color:", ["Monocromático (Líneas Negras)", "Color original"])
                    with c2:
                        lw = st.selectbox("Grosor de línea:", ["Fino (0.50x)", "Ultrafino (0.25x)", "Normal (1.00x)", "Grueso (1.50x)"])
                        ps = st.selectbox("Tamaño de hoja:", ["Auto (Detectar en CAD)", "A3", "A4", "A2", "A1", "A0", "Carta", "Oficio"])
                        ori = st.radio("Orientación:", ["Horizontal", "Vertical"], horizontal=True)

                    cad_opts = {
                        "space_mode": "all_layouts" if "Todos" in sc else ("model" if "Modelo" in sc else "layout"),
                        "color_mode": "monochrome" if "Monocromático" in colr else "color",
                        "lineweight_scale": 0.25 if "0.25" in lw else (1.5 if "1.5" in lw else 0.5),
                        "paper_size": "Auto" if "Auto" in ps else ps.split()[0],
                        "orientation": "portrait" if ori == "Vertical" else "landscape"
                    }
        else:
            target_fmt = st.selectbox("Convertir imagen a:", ["Documento PDF (.pdf)", "Imagen PNG (.png)", "Imagen JPG (.jpg)", "Imagen WEBP (.webp)", "Icono (.ico)"])

        if st.button("🚀 Iniciar Conversión", type="primary", use_container_width=True, key="btn_run_conversion"):
            with st.spinner("Procesando conversión..."):
                with tempfile.TemporaryDirectory() as tmpdir:
                    tmpp = Path(tmpdir)
                    in_p = tmpp / fn
                    with open(in_p, "wb") as f:
                        f.write(conv_uploaded.getbuffer())

                    out_p = None
                    mimetype = "application/octet-stream"
                    out_name = f"{in_p.stem}_convertido"

                    try:
                        if fext == ".pdf" and "Word" in target_fmt:
                            out_p = tmpp / f"{in_p.stem}.docx"
                            pdf_to_docx(in_p, out_p)
                            mimetype = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                            out_name = f"{in_p.stem}.docx"
                        elif fext == ".pdf" and "Excel" in target_fmt:
                            out_p = tmpp / f"{in_p.stem}.xlsx"
                            pdf_to_excel(in_p, out_p)
                            mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            out_name = f"{in_p.stem}.xlsx"
                        elif fext == ".pdf" and "PowerPoint" in target_fmt:
                            out_p = tmpp / f"{in_p.stem}.pptx"
                            pdf_to_pptx(in_p, out_p)
                            mimetype = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                            out_name = f"{in_p.stem}.pptx"
                        elif fext == ".pdf" and "Imágenes" in target_fmt:
                            fmt = "png" if "PNG" in target_fmt else "jpg"
                            fld = tmpp / "imgs"
                            pdf_to_images(in_p, fld, img_format=fmt)
                            zip_p = shutil.make_archive(str(tmpp / f"{in_p.stem}_imagenes"), 'zip', fld)
                            out_p = Path(zip_p)
                            mimetype = "application/zip"
                            out_name = f"{in_p.stem}_imagenes.zip"
                        elif fext == ".pdf" and "Texto" in target_fmt:
                            out_p = tmpp / f"{in_p.stem}.txt"
                            pdf_to_text(in_p, out_p)
                            mimetype = "text/plain; charset=utf-8"
                            out_name = f"{in_p.stem}.txt"
                        elif fext == ".dwg" and "PDF" in target_fmt:
                            out_p = tmpp / f"{in_p.stem}.pdf"
                            dwg_to_pdf(in_p, out_p, **cad_opts)
                            mimetype = "application/pdf"
                            out_name = f"{in_p.stem}.pdf"
                        elif fext == ".dxf" and "PDF" in target_fmt:
                            out_p = tmpp / f"{in_p.stem}.pdf"
                            dxf_to_pdf(in_p, out_p, **cad_opts)
                            mimetype = "application/pdf"
                            out_name = f"{in_p.stem}.pdf"
                        elif fext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"] and "PDF" in target_fmt:
                            out_p = tmpp / f"{in_p.stem}.pdf"
                            images_to_pdf([in_p], out_p)
                            mimetype = "application/pdf"
                            out_name = f"{in_p.stem}.pdf"
                        else:
                            fmt_target = target_fmt.split("(")[-1].replace(")", "").replace(".", "").strip().lower()
                            out_p = tmpp / f"{in_p.stem}.{fmt_target}"
                            convert_image(in_p, target_format=fmt_target, output_path=out_p)
                            mimetype = f"image/{fmt_target}"
                            out_name = f"{in_p.stem}.{fmt_target}"

                        if out_p and out_p.exists():
                            with open(out_p, "rb") as rf:
                                res_bytes = rf.read()
                            st.success(f"🎉 Conversión exitosa: `{out_name}`")
                            st.download_button(
                                label=f"📥 Descargar {out_name}",
                                data=res_bytes,
                                file_name=out_name,
                                mime=mimetype,
                                use_container_width=True
                            )
                    except Exception as err:
                        st.error(f"❌ Error durante la conversión: {err}")

# =========================================================================
# PESTAÑA 3: ORGANIZAR Y OPTIMIZAR PDF (iLovePDF GRATUITO)
# =========================================================================
with tabs[2]:
    st.header("📑 Organizar y Optimizar PDF")
    st.caption("Unir, Dividir, Comprimir (Baja, Recomendada, Extrema), Rotar, Eliminar y Extraer páginas.")

    tool_mode = st.radio(
        "Herramienta:",
        [
            "🔗 Unir PDFs (Merge)",
            "✂️ Dividir PDF (Split)",
            "⚡ Comprimir PDF (Reducción de tamaño)",
            "🔄 Rotar Páginas",
            "🗑️ Eliminar Páginas",
            "📑 Extraer Páginas",
            "📐 Recortar PDF (Crop)"
        ],
        horizontal=True
    )

    st.markdown("---")

    # 1. UNIR PDF
    if "Unir" in tool_mode:
        st.subheader("🔗 Unir Múltiples PDFs")
        multi_files = st.file_uploader("Selecciona o arrastra 2 o más archivos PDF:", type=["pdf"], accept_multiple_files=True, key="merge_files")
        if multi_files and len(multi_files) >= 2:
            st.write(f"Archivos a unir ({len(multi_files)}):")
            for i, mf in enumerate(multi_files):
                st.caption(f"{i + 1}. `{mf.name}` ({mf.size / 1024:.1f} KB)")

            if st.button("🚀 Unir PDFs Ahora", type="primary"):
                with tempfile.TemporaryDirectory() as td:
                    paths = []
                    for mf in multi_files:
                        p = Path(td) / mf.name
                        with open(p, "wb") as f:
                            f.write(mf.getbuffer())
                        paths.append(p)
                    out_merged = Path(td) / "documento_unido.pdf"
                    merge_pdfs(paths, out_merged)
                    with open(out_merged, "rb") as rf:
                        data_m = rf.read()
                    st.success("🎉 ¡PDFs unidos exitosamente!")
                    st.download_button("📥 Descargar PDF Combinado", data=data_m, file_name="documentos_unidos.pdf", mime="application/pdf")

    # 2. DIVIDIR PDF
    elif "Dividir" in tool_mode:
        st.subheader("✂️ Dividir PDF por Rangos o Páginas")
        split_f = st.file_uploader("Carga el PDF a dividir:", type=["pdf"], key="split_file")
        if split_f:
            split_opt = st.radio("Modo de división:", ["Por Rangos Específicos (ej: 1-3, 5, 8-10)", "Separar todas las páginas individuales"])
            ranges_val = None
            if "Rangos" in split_opt:
                ranges_val = st.text_input("Ingresa los rangos separados por comas:", "1-2, 3")

            if st.button("🚀 Dividir PDF", type="primary"):
                with tempfile.TemporaryDirectory() as td:
                    in_sp = Path(td) / split_f.name
                    with open(in_sp, "wb") as f:
                        f.write(split_f.getbuffer())
                    out_dir = Path(td) / "divididos"
                    created = split_pdf(in_sp, out_dir, ranges=ranges_val if "Rangos" in split_opt else None)
                    zip_res = shutil.make_archive(str(Path(td) / "paginas_divididas"), 'zip', out_dir)
                    with open(zip_res, "rb") as zf:
                        z_bytes = zf.read()
                    st.success(f"🎉 Se crearon {len(created)} archivos PDF.")
                    st.download_button("📥 Descargar Archivos Divididos (.zip)", data=z_bytes, file_name=f"{in_sp.stem}_dividido.zip", mime="application/zip")

    # 3. COMPRIMIR PDF
    elif "Comprimir" in tool_mode:
        st.subheader("⚡ Comprimir PDF")
        st.markdown('<span class="badge-pro">Función Pro de Pago en iLovePDF - 100% Gratis Aquí</span>', unsafe_allow_html=True)
        comp_f = st.file_uploader("Carga el PDF a comprimir:", type=["pdf"], key="comp_file")
        if comp_f:
            clevel = st.select_slider(
                "Nivel de Compresión:",
                options=["low", "recommended", "extreme"],
                value="recommended",
                format_func=lambda x: "💎 Compresión Baja (Máxima Calidad)" if x == "low" else ("⚖️ Compresión Recomendada (Balance Óptimo)" if x == "recommended" else "⚡ Compresión Extrema (Mínimo Peso)")
            )
            if st.button("🚀 Comprimir PDF Ahora", type="primary"):
                with tempfile.TemporaryDirectory() as td:
                    in_cp = Path(td) / comp_f.name
                    with open(in_cp, "wb") as f:
                        f.write(comp_f.getbuffer())
                    out_cp = Path(td) / f"{in_cp.stem}_comprimido.pdf"
                    _, o_sz, c_sz = compress_pdf(in_cp, out_cp, level=clevel)
                    with open(out_cp, "rb") as rf:
                        comp_bytes = rf.read()
                    ahorro = (1.0 - (c_sz / max(o_sz, 1))) * 100.0
                    col_m1, col_m2, col_m3 = st.columns(3)
                    col_m1.metric("Peso Original", f"{o_sz / 1024:.1f} KB")
                    col_m2.metric("Peso Comprimido", f"{c_sz / 1024:.1f} KB")
                    col_m3.metric("Ahorro de Espacio", f"{ahorro:.1f}%")
                    st.download_button("📥 Descargar PDF Comprimido", data=comp_bytes, file_name=out_cp.name, mime="application/pdf", use_container_width=True)

    # 4. ROTAR PÁGINAS
    elif "Rotar" in tool_mode:
        st.subheader("🔄 Rotar Páginas del PDF")
        rot_f = st.file_uploader("Carga el PDF a rotar:", type=["pdf"], key="rot_file")
        if rot_f:
            rot_deg = st.selectbox("Ángulo de rotación:", [90, 180, 270], format_func=lambda x: f"{x}° en sentido horario")
            if st.button("🚀 Rotar PDF", type="primary"):
                with tempfile.TemporaryDirectory() as td:
                    in_rp = Path(td) / rot_f.name
                    with open(in_rp, "wb") as f:
                        f.write(rot_f.getbuffer())
                    out_rp = Path(td) / f"{in_rp.stem}_rotado.pdf"
                    rotate_pages(in_rp, rot_deg, pages="all", output_path=out_rp)
                    with open(out_rp, "rb") as rf:
                        r_bytes = rf.read()
                    st.success("🎉 ¡Páginas rotadas exitosamente!")
                    st.download_button("📥 Descargar PDF Rotado", data=r_bytes, file_name=out_rp.name, mime="application/pdf")

    # 5. ELIMINAR / EXTRAER PÁGINAS
    elif "Eliminar" in tool_mode or "Extraer" in tool_mode:
        is_remove = "Eliminar" in tool_mode
        st.subheader(f"{'🗑️ Eliminar' if is_remove else '📑 Extraer'} Páginas del PDF")
        pe_f = st.file_uploader("Carga el archivo PDF:", type=["pdf"], key="pe_file")
        if pe_f:
            pages_str = st.text_input(
                f"Ingresa los números de página a {'eliminar' if is_remove else 'conservar'} (separados por coma, ej: 1, 3, 5):",
                "2" if is_remove else "1, 3"
            )
            if st.button(f"🚀 {'Eliminar Páginas' if is_remove else 'Extraer Páginas'}", type="primary"):
                try:
                    num_list = [int(p.strip()) for p in pages_str.split(",") if p.strip().isdigit()]
                    with tempfile.TemporaryDirectory() as td:
                        in_pep = Path(td) / pe_f.name
                        with open(in_pep, "wb") as f:
                            f.write(pe_f.getbuffer())
                        out_pep = Path(td) / f"{in_pep.stem}_{'modificado' if is_remove else 'extraido'}.pdf"
                        if is_remove:
                            remove_pages(in_pep, num_list, out_pep)
                        else:
                            extract_pages(in_pep, num_list, out_pep)
                        with open(out_pep, "rb") as rf:
                            pe_bytes = rf.read()
                        st.success("🎉 Documento procesado con éxito.")
                        st.download_button("📥 Descargar PDF Resultante", data=pe_bytes, file_name=out_pep.name, mime="application/pdf")
                except Exception as e:
                    st.error(f"Error: {e}")

    # 6. RECORTAR PDF
    elif "Recortar" in tool_mode:
        st.subheader("📐 Recortar Márgenes del PDF")
        cr_f = st.file_uploader("Carga el archivo PDF a recortar:", type=["pdf"], key="crop_file")
        if cr_f:
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                m_left = st.slider("Margen Izquierdo (pt):", 0, 150, 20)
                m_top = st.slider("Margen Superior (pt):", 0, 150, 20)
            with col_m2:
                m_right = st.slider("Margen Derecho (pt):", 0, 150, 20)
                m_bottom = st.slider("Margen Inferior (pt):", 0, 150, 20)
            if st.button("🚀 Recortar PDF", type="primary"):
                with tempfile.TemporaryDirectory() as td:
                    in_cr = Path(td) / cr_f.name
                    with open(in_cr, "wb") as f:
                        f.write(cr_f.getbuffer())
                    out_cr = Path(td) / f"{in_cr.stem}_recortado.pdf"
                    crop_pdf(in_cr, out_cr, margins=(m_left, m_top, m_right, m_bottom))
                    with open(out_cr, "rb") as rf:
                        cr_bytes = rf.read()
                    st.success("🎉 PDF recortado exitosamente.")
                    st.download_button("📥 Descargar PDF Recortado", data=cr_bytes, file_name=out_cr.name, mime="application/pdf")

# =========================================================================
# PESTAÑA 4: SEGURIDAD Y HERRAMIENTAS PRO (iLovePDF PREMIUM)
# =========================================================================
with tabs[3]:
    st.header("🔒 Seguridad y Herramientas Avanzadas")
    st.caption("Cifrado AES-256 bits, Desbloqueo, Marcas de agua, Numeración de páginas y Firma de documentos.")

    sec_tool = st.radio(
        "Herramienta Pro:",
        [
            "🔐 Proteger PDF con Contraseña",
            "🔓 Desbloquear PDF",
            "💧 Añadir Marca de Agua",
            "🔢 Numerar Páginas",
            "✍️ Firmar PDF (Firma Digital / Visual)"
        ],
        horizontal=True
    )
    st.markdown("---")

    # 1. PROTEGER PDF
    if "Proteger" in sec_tool:
        st.subheader("🔐 Proteger PDF con Encriptación Militar AES-256")
        st.markdown('<span class="badge-pro">iLovePDF Premium</span>', unsafe_allow_html=True)
        prot_f = st.file_uploader("Carga el PDF a proteger:", type=["pdf"], key="prot_file")
        if prot_f:
            col_pw1, col_pw2 = st.columns(2)
            with col_pw1:
                pwd_user = st.text_input("Contraseña de Apertura:", type="password")
            with col_pw2:
                pwd_confirm = st.text_input("Confirmar Contraseña:", type="password")

            if st.button("🚀 Encriptar y Proteger PDF", type="primary"):
                if not pwd_user or pwd_user != pwd_confirm:
                    st.error("Las contraseñas no coinciden o están vacías.")
                else:
                    with tempfile.TemporaryDirectory() as td:
                        in_pr = Path(td) / prot_f.name
                        with open(in_pr, "wb") as f:
                            f.write(prot_f.getbuffer())
                        out_pr = Path(td) / f"{in_pr.stem}_protegido.pdf"
                        protect_pdf(in_pr, out_pr, pwd_user)
                        with open(out_pr, "rb") as rf:
                            pr_bytes = rf.read()
                        st.success("🎉 ¡PDF encriptado exitosamente con AES-256 bits!")
                        st.download_button("📥 Descargar PDF Protegido", data=pr_bytes, file_name=out_pr.name, mime="application/pdf")

    # 2. DESBLOQUEAR PDF
    elif "Desbloquear" in sec_tool:
        st.subheader("🔓 Desbloquear PDF y Eliminar Restricciones")
        unl_f = st.file_uploader("Carga el PDF protegido:", type=["pdf"], key="unl_file")
        if unl_f:
            pwd_unlock = st.text_input("Ingresa la contraseña del documento:", type="password")
            if st.button("🚀 Desbloquear PDF", type="primary"):
                try:
                    with tempfile.TemporaryDirectory() as td:
                        in_ul = Path(td) / unl_f.name
                        with open(in_ul, "wb") as f:
                            f.write(unl_f.getbuffer())
                        out_ul = Path(td) / f"{in_ul.stem}_desbloqueado.pdf"
                        unlock_pdf(in_ul, out_ul, pwd_unlock)
                        with open(out_ul, "rb") as rf:
                            ul_bytes = rf.read()
                        st.success("🎉 PDF desbloqueado. Se han eliminado las contraseñas y restricciones.")
                        st.download_button("📥 Descargar PDF Desbloqueado", data=ul_bytes, file_name=out_ul.name, mime="application/pdf")
                except Exception as err:
                    st.error(f"Error al desbloquear: {err}")

    # 3. MARCA DE AGUA
    elif "Marca de Agua" in sec_tool:
        st.subheader("💧 Añadir Marca de Agua Personalizada")
        wm_f = st.file_uploader("Carga el PDF para colocar marca de agua:", type=["pdf"], key="wm_file")
        if wm_f:
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                wm_text = st.text_input("Texto de Marca de Agua:", "CONFIDENCIAL")
                wm_angle = st.slider("Ángulo de inclinación:", -90.0, 90.0, 45.0, 5.0)
            with col_w2:
                wm_opacity = st.slider("Opacidad / Transparencia:", 0.05, 1.0, 0.35, 0.05)
                wm_color = st.color_picker("Color de la marca de agua:", "#757575")

            if st.button("🚀 Aplicar Marca de Agua", type="primary"):
                with tempfile.TemporaryDirectory() as td:
                    in_wm = Path(td) / wm_f.name
                    with open(in_wm, "wb") as f:
                        f.write(wm_f.getbuffer())
                    out_wm = Path(td) / f"{in_wm.stem}_marca_agua.pdf"
                    watermark_pdf(in_wm, out_wm, text=wm_text, opacity=wm_opacity, angle=wm_angle, color=wm_color)
                    with open(out_wm, "rb") as rf:
                        wm_bytes = rf.read()
                    st.success("🎉 Marca de agua aplicada en todas las páginas.")
                    st.download_button("📥 Descargar PDF con Marca de Agua", data=wm_bytes, file_name=out_wm.name, mime="application/pdf")

    # 4. NUMERAR PÁGINAS
    elif "Numerar" in sec_tool:
        st.subheader("🔢 Insertar Numeración de Páginas")
        num_f = st.file_uploader("Carga el PDF a numerar:", type=["pdf"], key="num_file")
        if num_f:
            col_n1, col_n2 = st.columns(2)
            with col_n1:
                pos_choice = st.selectbox(
                    "Ubicación del número:",
                    [
                        "Pie de página - Centro (Recomendado)",
                        "Pie de página - Derecha",
                        "Pie de página - Izquierda",
                        "Encabezado - Centro",
                        "Encabezado - Derecha"
                    ]
                )
                fmt_template = st.text_input("Formato:", "Página {page} de {total}")
            with col_n2:
                num_size = st.slider("Tamaño de Fuente:", 8, 16, 10)
                num_color = st.color_picker("Color de texto:", "#424242")

            pos_key = "bottom_center"
            if "Derecha" in pos_choice and "Pie" in pos_choice:
                pos_key = "bottom_right"
            elif "Izquierda" in pos_choice:
                pos_key = "bottom_left"
            elif "Encabezado" in pos_choice and "Centro" in pos_choice:
                pos_key = "top_center"
            elif "Encabezado" in pos_choice:
                pos_key = "top_right"

            if st.button("🚀 Numerar Páginas", type="primary"):
                with tempfile.TemporaryDirectory() as td:
                    in_nm = Path(td) / num_f.name
                    with open(in_nm, "wb") as f:
                        f.write(num_f.getbuffer())
                    out_nm = Path(td) / f"{in_nm.stem}_numerado.pdf"
                    add_page_numbers(in_nm, out_nm, format_template=fmt_template, position=pos_key, font_size=num_size, color=num_color)
                    with open(out_nm, "rb") as rf:
                        nm_bytes = rf.read()
                    st.success("🎉 Páginas numeradas correctamente.")
                    st.download_button("📥 Descargar PDF Numerado", data=nm_bytes, file_name=out_nm.name, mime="application/pdf")

    # 5. FIRMAR PDF
    elif "Firmar" in sec_tool:
        st.subheader("✍️ Estampar Firma Digital / Visual en PDF")
        st.markdown('<span class="badge-pro">iLovePDF Sign</span>', unsafe_allow_html=True)
        sign_doc = st.file_uploader("1. Carga el documento a firmar:", type=["pdf"], key="sign_doc")
        sign_img = st.file_uploader("2. Carga la imagen de tu firma o rúbrica (.png o .jpg):", type=["png", "jpg", "jpeg"], key="sign_img")

        if sign_doc and sign_img:
            col_sg1, col_sg2 = st.columns(2)
            with col_sg1:
                page_to_sign = st.number_input("Página donde estampar la firma:", min_value=1, value=1) - 1
                pos_x = st.slider("Posición Horizontal X:", 0, 500, 350)
            with col_sg2:
                pos_y = st.slider("Posición Vertical Y:", 0, 800, 650)
                stamp_w = st.slider("Ancho de la firma:", 50, 250, 140)
                stamp_h = st.slider("Alto de la firma:", 20, 150, 60)

            if st.button("🚀 Estampar Firma y Certificar", type="primary"):
                with tempfile.TemporaryDirectory() as td:
                    in_sg = Path(td) / sign_doc.name
                    with open(in_sg, "wb") as f:
                        f.write(sign_doc.getbuffer())
                    out_sg = Path(td) / f"{in_sg.stem}_firmado.pdf"

                    figs_dict = {
                        page_to_sign: [
                            {
                                "type": "signature",
                                "x": pos_x, "y": pos_y, "w": stamp_w, "h": stamp_h,
                                "data": sign_img.getvalue()
                            }
                        ]
                    }
                    apply_all_figures_to_pdf(in_sg, out_sg, figs_dict)
                    with open(out_sg, "rb") as rf:
                        sg_bytes = rf.read()
                    st.success("🎉 ¡Firma estampada con éxito!")
                    st.download_button("📥 Descargar PDF Firmado", data=sg_bytes, file_name=out_sg.name, mime="application/pdf")

# =========================================================================
# PESTAÑA 5: ASISTENTE GEMINI AI (gemini-3.8-flash)
# =========================================================================
with tabs[4]:
    st.header("🤖 Asistente Inteligente Gemini AI")
    st.caption("Potenciado por Google Gemini 3.8 Flash con ventana de contexto de 1M de tokens.")

    if not gemini_active:
        st.warning("⚠️ La variable de entorno `GEMINI_API_KEY` no está configurada. Por favor configúrala para habilitar las funciones de IA.")
    else:
        ai_f = st.file_uploader("Carga el PDF para procesar con IA:", type=["pdf"], key="gemini_pdf_uploader")

        if ai_f:
            ai_bytes = ai_f.getvalue()
            ai_task = st.radio(
                "Selecciona la tarea inteligente a realizar:",
                [
                    "🔍 OCR Inteligente (Extraer texto de PDFs escaneados y tablas)",
                    "📋 Resumen Ejecutivo y Puntos Críticos",
                    "💬 Chat con el PDF (Preguntarle al documento)",
                    "🌐 Traducir Documento"
                ],
                horizontal=True
            )
            st.markdown("---")

            # 1. OCR INTELIGENTE
            if "OCR" in ai_task:
                st.subheader("🔍 OCR Multimodal con Gemini 3.8 Flash")
                st.info("Reconoce texto mecanografiado, notas manuscritas, tablas y sellos incluso en scans borrosos.")
                if st.button("🚀 Iniciar OCR Inteligente", type="primary"):
                    with st.spinner("Gemini 3.8 Flash está leyendo y transcribiendo el documento..."):
                        try:
                            ocr_result = gemini_ocr_pdf(ai_bytes)
                            st.markdown("### 📄 Texto y Tablas Extraídas:")
                            st.markdown(ocr_result)
                            st.download_button(
                                "📥 Descargar Transcripción (.txt / Markdown)",
                                data=ocr_result,
                                file_name=f"{Path(ai_f.name).stem}_OCR.md",
                                mime="text/markdown"
                            )
                        except Exception as e:
                            st.error(f"Error durante OCR: {e}")

            # 2. RESUMEN EJECUTIVO
            elif "Resumen" in ai_task:
                st.subheader("📋 Resumen Ejecutivo y Hallazgos")
                sum_type = st.selectbox("Formato del resumen:", ["Resumen Ejecutivo Estructurado", "Puntos Críticos (Bullet Points)", "Análisis Profundo Sección por Sección"])
                type_code = "bullets" if "Puntos" in sum_type else ("deep" if "Profundo" in sum_type else "executive")

                if st.button("🚀 Generar Resumen con Gemini", type="primary"):
                    with st.spinner("Analizando documento con Gemini 3.8 Flash..."):
                        try:
                            summary_res = gemini_summarize_pdf(ai_bytes, summary_type=type_code)
                            st.markdown(summary_res)
                            st.download_button(
                                "📥 Descargar Resumen (.md)",
                                data=summary_res,
                                file_name=f"{Path(ai_f.name).stem}_resumen.md",
                                mime="text/markdown"
                            )
                        except Exception as e:
                            st.error(f"Error al resumir: {e}")

            # 3. CHAT CON EL PDF
            elif "Chat" in ai_task:
                st.subheader("💬 Pregúntale a tu Documento PDF")
                if "chat_messages" not in st.session_state:
                    st.session_state["chat_messages"] = []

                # Mostrar historial
                for msg in st.session_state["chat_messages"]:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])

                user_q = st.chat_input("Escribe tu pregunta sobre el contenido del PDF...")
                if user_q:
                    st.session_state["chat_messages"].append({"role": "user", "content": user_q})
                    with st.chat_message("user"):
                        st.markdown(user_q)

                    with st.chat_message("assistant"):
                        with st.spinner("Consultando al documento..."):
                            try:
                                ans = gemini_chat_with_pdf(ai_bytes, user_q, chat_history=st.session_state["chat_messages"])
                                st.markdown(ans)
                                st.session_state["chat_messages"].append({"role": "assistant", "content": ans})
                            except Exception as e:
                                st.error(f"Error: {e}")

            # 4. TRADUCIR
            elif "Traducir" in ai_task:
                st.subheader("🌐 Traducción Inteligente de Documento")
                target_lang = st.selectbox("Idioma de destino:", ["Español", "Inglés", "Francés", "Alemán", "Portugués", "Italiano", "Chino Mandarín", "Japonés"])
                if st.button("🚀 Traducir Documento Ahora", type="primary"):
                    with st.spinner(f"Traduciendo a {target_lang} con Gemini 3.8 Flash..."):
                        try:
                            trans_res = gemini_translate_pdf_text(ai_bytes, target_language=target_lang)
                            st.markdown(trans_res)
                            st.download_button(
                                "📥 Descargar Traducción (.md)",
                                data=trans_res,
                                file_name=f"{Path(ai_f.name).stem}_traducido_{target_lang}.md",
                                mime="text/markdown"
                            )
                        except Exception as e:
                            st.error(f"Error al traducir: {e}")
