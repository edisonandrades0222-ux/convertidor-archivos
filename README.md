---
title: Convertidor Universal de Archivos
emoji: ⚡
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# ⚡ Convertidor Universal de Archivos

Herramienta autónoma y privada para la conversión integral de documentos, planos de arquitectura e ingeniería e imágenes. Funciona tanto en aplicación de escritorio (CustomTkinter) como en aplicación web (Streamlit / Streamlit Cloud / Docker).

## 🚀 Funcionalidades Principales

1. **Documentos PDF:**
   - PDF ➔ Word Editable (`.docx`) conservando texto, estilos y estructura.
   - PDF ➔ Extracción por lotes de imágenes (`.png`, `.jpg`) empaquetadas en `.zip`.
   - PDF ➔ Extracción de texto plano (`.txt`).
2. **Planos CAD (DWG y DXF):**
   - DWG / DXF ➔ PDF Vectorial nítido.
   - Selección de espacio: Espacio Modelo o Láminas / Layouts con cajetín.
   - Modos de color: Monocromático (estilo `monochrome.ctb`) o capas en color.
   - Tamaños de papel normalizados: A0, A1, A2, A3, A4, Carta, Oficio.
   - Control de grosor de línea y orientación (horizontal / vertical).
   - Conversión cruzada DWG ➔ DXF y DXF ➔ DWG.
   - DXF ➔ Renderizado de alta resolución en PNG / JPG.
3. **Imágenes:**
   - Imágenes (`.png`, `.jpg`, `.webp`, `.bmp`, `.tiff`) ➔ Documento PDF.
   - Conversión entre múltiples formatos gráficos con soporte para transparencia alfa e iconos (`.ico`).

---

## 🛠️ Requisitos e Instalación

### Requisitos:
- **Python 3.10** o superior.
- Windows (para la app de escritorio) o Linux/macOS/Windows (para la app web).

### Inicio Rápido (Windows):

1. **Configuración Automática del Entorno:**
   Ejecuta `setup_env.bat` haciendo doble clic. Creará automáticamente el entorno virtual `.venv` e instalará todas las dependencias necesarias.

2. **Lanzar la Aplicación de Escritorio:**
   Haz doble clic en `iniciar.bat`.

3. **Lanzar la Aplicación Web (Streamlit):**
   Haz doble clic en `iniciar_web.bat`. Se abrirá en tu navegador en `http://localhost:8501`.

4. **Ejecutar Pruebas Automatizadas:**
   Haz doble clic en `run_tests.bat` o ejecuta:
   ```bash
   python -m pytest test_converters.py -v
   ```

---

## ☁️ Despliegue en Streamlit Cloud / Linux

El repositorio ya incluye los archivos necesarios para despliegue directo en **Streamlit Community Cloud**:
- `requirements.txt`: Librerías Python requeridas (`streamlit`, `ezdxf`, `pymupdf`, `pdf2docx`, `pillow`, `matplotlib`, `python-docx`, etc.).
- `packages.txt`: Dependencias a nivel de sistema operativo Linux (`libredwg-tools` y fuentes TrueType `fonts-dejavu-core`).
- Carpeta `fonts/`: Fuentes base DejaVu para garantizar el renderizado de texto CAD en entornos headless/cloud.

Entrypoint en la nube: `web_app.py`.
