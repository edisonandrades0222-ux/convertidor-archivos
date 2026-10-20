---
title: Convertidor Universal & Suite PDF
emoji: ⚡
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# ⚡ Universal PDF & CAD Suite (iLovePDF Pro 100% Gratuito)

Herramienta autónoma, privada y sin suscripciones para la edición vectorial de PDFs, conversión integral de documentos y planos CAD, optimización, seguridad y asistencia con Inteligencia Artificial.

---

## 🚀 Funcionalidades Principales

### 1. 🎨 Editor de PDF con Figuras Vectoriales (En Vivo)
- **➡️ Flechas:** Dirección rápida (derecha, izquierda, arriba, abajo, diagonales) o coordenadas libres, color, grosor de trazo y punta ajustable.
- **⭕ Círculos y Elipses:** Borde personalizable, relleno translúcido opcional y opacidad regulable.
- **⏹️ Rectángulos y Cuadros:** Cajas de anotación, esquinas rectas, relleno translúcido o sólido.
- **➖ Líneas Rectas:** Líneas continuas o punteadas.
- **🔤 Texto y Notas:** Tipografía profesional, tamaños de fuente, colores, negrita, cursiva y fondos destacados.
- **🖍️ Resaltador:** Bandas translúcidas de resalte en múltiples colores.
- **⬛ Censura Permanente (Redaction):** Función premium de iLovePDF que elimina irreversiblemente texto y gráficos confidenciales debajo de la caja de censura.
- **🖋️ Firma y Sellos:** Estampa tu rúbrica o logotipo con fondo transparente en cualquier coordenada.
- **👁️ Previsualización Vectorial en Vivo:** Renderizado en tiempo real de cada página antes de descargar el PDF.

### 2. ⚡ Convertidor Universal de Archivos
- **PDF a Word Editable (`.docx`):** Mantiene formato, estilos, tablas e imágenes.
- **PDF a Excel con Tablas (`.xlsx`):** Detección automática y estructuración de tablas.
- **PDF a PowerPoint (`.pptx`):** Generación automática de diapositivas de presentación.
- **PDF a Imágenes (`.png`, `.jpg`):** Extracción empaquetada en `.zip`.
- **PDF a Texto Plano (`.txt`).**
- **Planos AutoCAD (DWG / DXF) a PDF Vectorial:** Soporte completo de Láminas / Layouts con cajetín, estilo monocromático (estilo `monochrome.ctb`), tamaños normalizados (A0, A1, A2, A3, A4, Carta, Oficio) y grosores de línea.
- **Imágenes a PDF:** Combina fotos o documentos en un único PDF.

### 3. 📑 Organizar y Optimizar PDF (Suite iLovePDF)
- **🔗 Unir PDFs (Merge):** Combina múltiples archivos en el orden deseado.
- **✂️ Dividir PDF (Split):** Extrae rangos específicos (ej. 1-3, 5, 8-10) o separa cada página en un PDF independiente.
- **⚡ Comprimir PDF (Función de Pago en iLovePDF):**
  - **Compresión Extrema:** Mínimo peso de archivo.
  - **Compresión Recomendada:** Balance óptimo calidad / tamaño.
  - **Compresión Baja:** Máxima fidelidad gráfica.
  - Métricas de ahorro en vivo (% reducido y peso antes/después).
- **🔄 Rotar Páginas:** Giro a 90°, 180° o 270°.
- **🗑️ Eliminar Páginas / 📑 Extraer Páginas:** Gestión granular de hojas.
- **📐 Recortar PDF (Crop):** Ajuste y recorte de márgenes.

### 4. 🔒 Seguridad y Certificación (iLovePDF Premium)
- **🔐 Proteger PDF:** Encriptación militar AES-256 bits y protección con contraseña.
- **🔓 Desbloquear PDF:** Eliminación de contraseñas y desbloqueo de restricciones de copia/impresión.
- **💧 Marca de Agua:** Texto rotado personalizable (ej. "CONFIDENCIAL") o logotipo con opacidad regulable.
- **🔢 Numerar Páginas:** Formato flexible ("Página {page} de {total}"), en encabezado o pie de página.
- **✍️ Firmar PDF:** Certificación visual con firma digitalizada, fecha y datos del firmante.

### 5. 🤖 Asistente Gemini AI (Google Gemini 3.8 Flash)
- **🔍 OCR Multimodal Inteligente:** Transcripción de documentos escaneados, fotos y facturas ilegibles a Markdown limpio.
- **📋 Resumen Ejecutivo:** Síntesis estructurada, puntos críticos y hallazgos clave.
- **💬 Chat Interactivo con tu PDF:** Pregúntale cualquier duda al documento y recibe respuestas fundamentadas.
- **🌐 Traducción Multilingüe:** Traduce documentos completos manteniendo la coherencia conceptual.

---

## 🛠️ Inicio Rápido (Windows)

1. **Lanzar la Aplicación Web (Editor de Figuras & Suite Completa):**
   Haz doble clic en `iniciar_web.bat`. Se abrirá en tu navegador en `http://localhost:8501`.

2. **Lanzar la Aplicación de Escritorio:**
   Haz doble clic en `iniciar.bat`.

3. **Ejecutar Pruebas Automatizadas:**
   ```bash
   python -m pytest test_converters.py -v
   ```
