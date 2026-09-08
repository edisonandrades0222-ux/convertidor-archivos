import os
import sys
import tempfile
import shutil
from pathlib import Path
import streamlit as st

# Configurar path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from converters.cad_converter import (
    dwg_to_pdf, dwg_to_dxf, dxf_to_pdf, dxf_to_dwg, dxf_to_image,
    ensure_ezdxf_fonts
)
from converters.pdf_converter import pdf_to_docx, pdf_to_images, images_to_pdf, pdf_to_text
from converters.image_converter import convert_image

# Garantizar fuentes disponibles de forma eficiente
@st.cache_resource
def init_fonts():
    ensure_ezdxf_fonts()
    return True

init_fonts()

st.set_page_config(
    page_title="Convertidor Universal de Archivos",
    page_icon="⚡",
    layout="centered"
)

st.title("⚡ Convertidor Universal de Archivos")
st.markdown("##### PDF ➔ Word | DWG / DXF ➔ PDF (Layout, Monocromo, Hoja) | Imágenes")
st.caption("100% Autónomo y Privado. Convierte tus archivos directamente sin suscripciones.")

# 1. Selector de Archivo
uploaded_file = st.file_uploader(
    "Selecciona o arrastra tu archivo aquí:", 
    type=["pdf", "dwg", "dxf", "png", "jpg", "jpeg", "webp", "bmp", "tiff"]
)

if uploaded_file:
    filename = uploaded_file.name
    file_ext = Path(filename).suffix.lower()
    
    # Reiniciar resultado previo si se sube otro archivo
    current_file_id = f"{filename}_{uploaded_file.size}"
    if st.session_state.get("last_uploaded_id") != current_file_id:
        st.session_state["last_uploaded_id"] = current_file_id
        st.session_state.pop("converted_result", None)

    st.info(f"📄 **Archivo cargado:** `{filename}` ({uploaded_file.size / 1024:.1f} KB)")

    # 2. Opciones de conversion segun el formato
    st.markdown("---")
    st.subheader("⚙️ Configuración de Conversión")

    target_format = None
    cad_options = {}

    if file_ext == ".pdf":
        target_format = st.selectbox(
            "Convertir PDF a:",
            [
                "Word Editable (.docx)",
                "Imágenes PNG (.png)",
                "Imágenes JPG (.jpg)",
                "Texto Plano (.txt)"
            ]
        )

    elif file_ext in [".dwg", ".dxf"]:
        options = ["Documento PDF Vectorial (.pdf)"]
        if file_ext == ".dwg":
            options.append("Plano DXF (.dxf)")
        else:
            options.extend(["Plano DWG (.dwg)", "Imagen PNG (.png)", "Imagen JPG (.jpg)"])

        target_format = st.selectbox("Convertir plano CAD a:", options)

        # Opciones avanzadas CAD si el destino es PDF
        if "PDF" in target_format:
            with st.expander("📐 Opciones Avanzadas de Exportación CAD", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    space_choice = st.selectbox(
                        "Extraer espacio:",
                        ["Lámina / Layout (Presentación)", "Todos los Layouts (PDF multipágina)", "Espacio Modelo (ModelSpace)"],
                        help="Extrae el Layout armado con cajetín y ventanas gráficas en vez del modelo infinito."
                    )
                    color_choice = st.selectbox(
                        "Estilo de color:",
                        ["Monocromático (Líneas Negras)", "Color (Capas originales)"],
                        help="Monocromático imprime todo en tinta negra sobre fondo blanco, equivalente a monochrome.ctb."
                    )
                with col2:
                    weight_choice = st.selectbox(
                        "Grosor de línea:",
                        ["Fino (0.50x) - Recomendado", "Ultrafino (0.25x)", "Normal (1.00x)", "Grueso (1.50x)"],
                        help="Reduce el grosor para evitar empastes en zonas densas."
                    )
                    paper_choice = st.selectbox(
                        "Tamaño de hoja:",
                        ["A3 (420 x 297 mm)", "A4 (297 x 210 mm)", "A2 (594 x 420 mm)", "A1 (841 x 594 mm)", "A0 (1189 x 841 mm)", "Carta / Letter", "Oficio / Legal"],
                        index=0
                    )
                    orient_choice = st.radio("Orientación:", ["Horizontal", "Vertical"], horizontal=True)

                space_mode = "all_layouts" if "Todos" in space_choice else ("model" if "Modelo" in space_choice else "layout")
                color_mode = "monochrome" if "Monocromático" in color_choice else "color"
                
                weight_val = 0.50
                if "0.25" in weight_choice:
                    weight_val = 0.25
                elif "1.50" in weight_choice:
                    weight_val = 1.50
                elif "1.00" in weight_choice:
                    weight_val = 1.00

                paper_val = "A3"
                for p in ["A0", "A1", "A2", "A3", "A4", "Carta", "Oficio"]:
                    if p in paper_choice:
                        paper_val = p
                        break

                cad_options = {
                    "space_mode": space_mode,
                    "color_mode": color_mode,
                    "lineweight_scale": weight_val,
                    "paper_size": paper_val,
                    "orientation": "portrait" if orient_choice == "Vertical" else "landscape"
                }

    elif file_ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]:
        target_format = st.selectbox(
            "Convertir imagen a:",
            [
                "Documento PDF (.pdf)",
                "Imagen PNG (.png)",
                "Imagen JPG (.jpg)",
                "Imagen WEBP (.webp)",
                "Imagen BMP (.bmp)",
                "Icono (.ico)"
            ]
        )

    # 3. Boton de Conversion
    st.markdown("---")
    if st.button("🚀 Iniciar Conversión", type="primary", use_container_width=True):
        with st.spinner("Procesando y convirtiendo archivo... por favor espera unos segundos"):
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir)
                in_file = tmp_path / filename
                with open(in_file, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                out_file = None
                mime_type = "application/octet-stream"
                download_name = f"{in_file.stem}_convertido"

                try:
                    # PDF -> DOCX
                    if file_ext == ".pdf" and "Word" in target_format:
                        out_file = tmp_path / f"{in_file.stem}.docx"
                        pdf_to_docx(in_file, out_file)
                        mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        download_name = f"{in_file.stem}.docx"

                    # PDF -> Imagenes
                    elif file_ext == ".pdf" and "Imágenes" in target_format:
                        fmt = "png" if "PNG" in target_format else "jpg"
                        out_folder = tmp_path / "imgs"
                        imgs = pdf_to_images(in_file, out_folder, img_format=fmt)
                        zip_base = tmp_path / f"{in_file.stem}_imagenes"
                        zip_path = shutil.make_archive(str(zip_base), 'zip', out_folder)
                        out_file = Path(zip_path)
                        mime_type = "application/zip"
                        download_name = f"{in_file.stem}_imagenes.zip"

                    # PDF -> Texto
                    elif file_ext == ".pdf" and "Texto" in target_format:
                        out_file = tmp_path / f"{in_file.stem}.txt"
                        pdf_to_text(in_file, out_file)
                        mime_type = "text/plain; charset=utf-8"
                        download_name = f"{in_file.stem}.txt"

                    # DWG -> PDF
                    elif file_ext == ".dwg" and "PDF" in target_format:
                        out_file = tmp_path / f"{in_file.stem}.pdf"
                        dwg_to_pdf(in_file, out_file, **cad_options)
                        mime_type = "application/pdf"
                        download_name = f"{in_file.stem}.pdf"

                    # DWG -> DXF
                    elif file_ext == ".dwg" and "DXF" in target_format:
                        out_file = tmp_path / f"{in_file.stem}.dxf"
                        dwg_to_dxf(in_file, out_file)
                        mime_type = "application/dxf"
                        download_name = f"{in_file.stem}.dxf"

                    # DXF -> PDF
                    elif file_ext == ".dxf" and "PDF" in target_format:
                        out_file = tmp_path / f"{in_file.stem}.pdf"
                        dxf_to_pdf(in_file, out_file, **cad_options)
                        mime_type = "application/pdf"
                        download_name = f"{in_file.stem}.pdf"

                    # DXF -> DWG
                    elif file_ext == ".dxf" and "DWG" in target_format:
                        out_file = tmp_path / f"{in_file.stem}.dwg"
                        dxf_to_dwg(in_file, out_file)
                        mime_type = "application/acad"
                        download_name = f"{in_file.stem}.dwg"

                    # DXF -> Imagen
                    elif file_ext == ".dxf" and ("PNG" in target_format or "JPG" in target_format):
                        fmt = "png" if "PNG" in target_format else "jpg"
                        out_file = tmp_path / f"{in_file.stem}.{fmt}"
                        dxf_to_image(in_file, out_file, img_format=fmt)
                        mime_type = f"image/{fmt}"
                        download_name = f"{in_file.stem}.{fmt}"

                    # Imagen -> PDF
                    elif file_ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"] and "PDF" in target_format:
                        out_file = tmp_path / f"{in_file.stem}.pdf"
                        images_to_pdf([in_file], out_file)
                        mime_type = "application/pdf"
                        download_name = f"{in_file.stem}.pdf"

                    # Imagen -> Imagen
                    else:
                        fmt = target_format.split("(")[-1].replace(")", "").replace(".", "").strip().lower()
                        out_file = tmp_path / f"{in_file.stem}.{fmt}"
                        convert_image(in_file, target_format=fmt, output_path=out_file)
                        mime_type = f"image/{fmt}"
                        download_name = f"{in_file.stem}.{fmt}"

                    if out_file and out_file.exists():
                        with open(out_file, "rb") as f_res:
                            data_bytes = f_res.read()

                        st.session_state["converted_result"] = {
                            "bytes": data_bytes,
                            "filename": download_name,
                            "mime": mime_type
                        }
                    else:
                        st.error("No se pudo generar el archivo de salida.")

                except Exception as e:
                    err_msg = str(e)
                    if "LibreDWG" in err_msg or "dwg2dxf" in err_msg or "dxf2dwg" in err_msg:
                        st.error(
                            f"⚠️ **Error con archivo DWG:** {err_msg}\n\n"
                            "Los archivos `.dwg` propietarios requieren componentes LibreDWG. "
                            "Si estás en la nube (Streamlit Cloud), asegúrate de que el repositorio incluya el archivo `packages.txt` con `libredwg-tools`."
                        )
                    else:
                        st.error(f"❌ Ocurrió un error durante la conversión: {err_msg}")

    # 4. Mostrar botón de descarga si el archivo fue convertido
    if "converted_result" in st.session_state:
        res = st.session_state["converted_result"]
        st.success(f"🎉 **¡Conversión completada con éxito!** Archivo listo: `{res['filename']}`")
        st.download_button(
            label=f"📥 Descargar {res['filename']}",
            data=res["bytes"],
            file_name=res["filename"],
            mime=res["mime"],
            use_container_width=True
        )
