import os
import math
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
import pymupdf as fitz
from PIL import Image
import io

def parse_color(color_val: Any) -> Tuple[float, float, float]:
    """
    Convierte colores en formato hexadecimal '#RRGGBB', RGB (0-255) o RGB (0.0-1.0)
    a tuplas normalizadas (r, g, b) con valores entre 0.0 y 1.0 para PyMuPDF.
    """
    if isinstance(color_val, str):
        c = color_val.strip().lstrip("#")
        if len(c) == 6:
            r = int(c[0:2], 16) / 255.0
            g = int(c[2:4], 16) / 255.0
            b = int(c[4:6], 16) / 255.0
            return (r, g, b)
        elif len(c) == 8:  # RRGGBBAA
            r = int(c[0:2], 16) / 255.0
            g = int(c[2:4], 16) / 255.0
            b = int(c[4:6], 16) / 255.0
            return (r, g, b)
    elif isinstance(color_val, (tuple, list)):
        if len(color_val) >= 3:
            # Si los valores son > 1.0 se asume escala 0-255
            if any(v > 1.0 for v in color_val[:3]):
                return (color_val[0] / 255.0, color_val[1] / 255.0, color_val[2] / 255.0)
            return (float(color_val[0]), float(color_val[1]), float(color_val[2]))
    # Por defecto negro
    return (0.0, 0.0, 0.0)

def map_point(page: fitz.Page, p: Any) -> fitz.Point:
    """Mapea un punto visual (x, y) a coordenadas nativas de la página respetando su rotación."""
    pt = fitz.Point(float(p[0]), float(p[1]))
    if hasattr(page, "rotation") and page.rotation != 0:
        return pt * page.derotation_matrix
    return pt

def map_rect(page: fitz.Page, r: Any) -> fitz.Rect:
    """Mapea un rectángulo visual a coordenadas nativas de la página respetando su rotación."""
    rect = fitz.Rect(r)
    if hasattr(page, "rotation") and page.rotation != 0:
        return rect * page.derotation_matrix
    return rect

def draw_vector_arrow(
    page: fitz.Page,
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    color: Any = (1.0, 0.0, 0.0),
    width: float = 2.5,
    head_size: float = 12.0,
    fill_head: bool = True,
    opacity: float = 1.0
):
    """
    Dibuja una flecha vectorial profesional desde p1 hasta p2 en la página del PDF.
    Garantiza posicionamiento exacto sin desajustes por rotación de página.
    """
    c = parse_color(color)
    x1, y1 = float(p1[0]), float(p1[1])
    x2, y2 = float(p2[0]), float(p2[1])

    dx = x2 - x1
    dy = y2 - y1
    dist = math.hypot(dx, dy)
    if dist < 1e-4:
        return

    angle = math.atan2(dy, dx)
    head_len = min(head_size, dist * 0.45)
    wing_angle = math.radians(28)

    # Calcular puntos de las aletas de la flecha en espacio visual
    w1_x = x2 - head_len * math.cos(angle - wing_angle)
    w1_y = y2 - head_len * math.sin(angle - wing_angle)
    w2_x = x2 - head_len * math.cos(angle + wing_angle)
    w2_y = y2 - head_len * math.sin(angle + wing_angle)

    # Punto base de la punta de la flecha
    base_x = x2 - (head_len * 0.8) * math.cos(angle)
    base_y = y2 - (head_len * 0.8) * math.sin(angle)

    # Mapear todos los puntos al espacio nativo de la página
    mp1 = map_point(page, (x1, y1))
    mbase = map_point(page, (base_x, base_y))
    mp2 = map_point(page, (x2, y2))
    mw1 = map_point(page, (w1_x, w1_y))
    mw2 = map_point(page, (w2_x, w2_y))

    shape = page.new_shape()
    # Trazar cuerpo de la flecha hasta la base
    shape.draw_line(mp1, mbase)
    shape.finish(color=c, width=width, stroke_opacity=opacity)

    # Trazar cabeza de la flecha (triángulo cerrado estilizado)
    arrowhead = [mp2, mw1, mw2, mp2]
    shape.draw_polyline(arrowhead)
    shape.finish(
        color=c, 
        fill=c if fill_head else None, 
        width=width * 0.75,
        stroke_opacity=opacity,
        fill_opacity=opacity
    )
    shape.commit()

def draw_vector_circle(
    page: fitz.Page,
    rect_or_center: Any,
    radius: Optional[float] = None,
    color: Any = (1.0, 0.0, 0.0),
    fill_color: Optional[Any] = None,
    width: float = 2.0,
    opacity: float = 1.0,
    fill_opacity: float = 1.0
):
    """
    Dibuja un círculo u óvalo vectorial en el PDF con soporte para borde y relleno.
    """
    stroke_c = parse_color(color)
    fill_c = parse_color(fill_color) if fill_color is not None else None

    if radius is not None:
        cx, cy = rect_or_center[0], rect_or_center[1]
        rect = fitz.Rect(cx - radius, cy - radius, cx + radius, cy + radius)
    else:
        rect = fitz.Rect(rect_or_center)

    native_rect = map_rect(page, rect)
    shape = page.new_shape()
    shape.draw_oval(native_rect)
    shape.finish(
        color=stroke_c,
        fill=fill_c,
        width=width,
        stroke_opacity=opacity,
        fill_opacity=fill_opacity if fill_c else 0.0
    )
    shape.commit()

def draw_vector_rect(
    page: fitz.Page,
    rect: Any,
    color: Any = (0.0, 0.4, 0.8),
    fill_color: Optional[Any] = None,
    width: float = 2.0,
    radius: float = 0.0,
    opacity: float = 1.0,
    fill_opacity: float = 1.0
):
    """
    Dibuja un rectángulo o cuadrado vectorial, con esquinas rectas o redondeadas.
    """
    stroke_c = parse_color(color)
    fill_c = parse_color(fill_color) if fill_color is not None else None
    native_rect = map_rect(page, rect)

    shape = page.new_shape()
    shape.draw_rect(native_rect)

    shape.finish(
        color=stroke_c,
        fill=fill_c,
        width=width,
        stroke_opacity=opacity,
        fill_opacity=fill_opacity if fill_c else 0.0
    )
    shape.commit()

def draw_vector_line(
    page: fitz.Page,
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    color: Any = (0.0, 0.0, 0.0),
    width: float = 2.0,
    opacity: float = 1.0,
    dashed: bool = False
):
    """
    Dibuja una línea recta vectorial continua o punteada.
    """
    c = parse_color(color)
    mp1 = map_point(page, p1)
    mp2 = map_point(page, p2)
    shape = page.new_shape()
    shape.draw_line(mp1, mp2)
    shape.finish(
        color=c,
        width=width,
        dashes="[3 3] 0" if dashed else None,
        stroke_opacity=opacity
    )
    shape.commit()

def add_vector_text(
    page: fitz.Page,
    pos: Tuple[float, float],
    text: str,
    fontsize: float = 14.0,
    color: Any = (0.0, 0.0, 0.0),
    bg_color: Optional[Any] = None,
    bold: bool = False,
    italic: bool = False
):
    """
    Inserta texto con formato y fondo opcional en coordenadas (x, y).
    """
    c = parse_color(color)
    fontname = "helv"
    if bold and italic:
        fontname = "hebi"
    elif bold:
        fontname = "hebo"
    elif italic:
        fontname = "heit"

    # Si hay fondo, calcular caja y dibujar primero
    if bg_color is not None:
        bg_c = parse_color(bg_color)
        approx_w = len(text) * fontsize * 0.55 + 10
        approx_h = fontsize * 1.35 + 6
        bg_rect = fitz.Rect(pos[0] - 4, pos[1] - fontsize - 2, pos[0] + approx_w, pos[1] + 4)
        draw_vector_rect(page, bg_rect, color=bg_c, fill_color=bg_c, width=1, fill_opacity=0.85)

    native_pos = map_point(page, pos)
    page.insert_text(
        native_pos,
        text,
        fontsize=fontsize,
        fontname=fontname,
        color=c,
        rotate=page.rotation if hasattr(page, "rotation") else 0
    )

def add_permanent_redaction(
    page: fitz.Page,
    rect: Any,
    fill_color: Any = (0.0, 0.0, 0.0),
    text: str = ""
):
    """
    Aplica una censura / redacción permanente que elimina irreversiblemente
    el contenido vectorial, imágenes y texto debajo del rectángulo.
    """
    c = parse_color(fill_color)
    native_rect = map_rect(page, rect)
    page.add_redact_annot(native_rect, text=text, fill=c)
    page.apply_redactions()

def add_image_overlay(
    page: fitz.Page,
    rect: Any,
    image_input: Union[str, Path, bytes, Image.Image]
):
    """
    Inserta una imagen o firma visual en el rectángulo indicado de la página.
    """
    native_rect = map_rect(page, rect)
    rot_val = page.rotation if hasattr(page, "rotation") else 0
    if isinstance(image_input, (str, Path)):
        page.insert_image(native_rect, filename=str(image_input), rotate=rot_val)
    elif isinstance(image_input, bytes):
        page.insert_image(native_rect, stream=image_input, rotate=rot_val)
    elif isinstance(image_input, Image.Image):
        buf = io.BytesIO()
        image_input.save(buf, format="PNG")
        page.insert_image(native_rect, stream=buf.getvalue(), rotate=rot_val)

def render_pdf_page_to_image(
    pdf_path_or_bytes: Union[str, Path, bytes],
    page_num: int = 0,
    dpi: int = 150
) -> Image.Image:
    """
    Renderiza una página de PDF a un objeto PIL.Image de alta resolución para previsualización.
    """
    if isinstance(pdf_path_or_bytes, bytes):
        doc = fitz.open(stream=pdf_path_or_bytes, filetype="pdf")
    else:
        doc = fitz.open(str(pdf_path_or_bytes))

    if page_num < 0 or page_num >= len(doc):
        page_num = 0

    page = doc[page_num]
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img_data = pix.tobytes("png")
    doc.close()
    return Image.open(io.BytesIO(img_data))

def parse_canvas_json(json_data: dict, default_line_as_arrow: bool = False) -> List[Dict[str, Any]]:
    """
    Convierte la estructura JSON de objetos de Fabric.js (streamlit-drawable-canvas)
    a la lista interna de figuras de pdf_editor (flechas, círculos, rectángulos, trazos).
    """
    elements = []
    if not json_data or "objects" not in json_data:
        return elements

    for obj in json_data.get("objects", []):
        t = obj.get("type", "").lower()
        if t == "line":
            is_arrow = obj.get("is_arrow", default_line_as_arrow)
            elem = {
                "type": "arrow" if is_arrow else "line",
                "x1": float(obj.get("x1", 0) + obj.get("left", 0)),
                "y1": float(obj.get("y1", 0) + obj.get("top", 0)),
                "x2": float(obj.get("x2", 0) + obj.get("left", 0)),
                "y2": float(obj.get("y2", 0) + obj.get("top", 0)),
                "color": obj.get("stroke", "#E53935"),
                "width": float(obj.get("strokeWidth", 2.5)),
                "head_size": 14.0
            }
            elements.append(elem)
        elif t == "rect":
            fill_val = obj.get("fill")
            if fill_val in ["rgba(0,0,0,0)", "transparent", ""]:
                fill_val = None
            elem = {
                "type": "rect",
                "x": float(obj.get("left", 0)),
                "y": float(obj.get("top", 0)),
                "w": float(obj.get("width", 0)) * float(obj.get("scaleX", 1.0)),
                "h": float(obj.get("height", 0)) * float(obj.get("scaleY", 1.0)),
                "color": obj.get("stroke", "#43A047"),
                "fill_color": fill_val,
                "width": float(obj.get("strokeWidth", 2.0))
            }
            elements.append(elem)
        elif t == "circle":
            fill_val = obj.get("fill")
            if fill_val in ["rgba(0,0,0,0)", "transparent", ""]:
                fill_val = None
            rad = float(obj.get("radius", 0)) * float(obj.get("scaleX", 1.0))
            elem = {
                "type": "circle",
                "cx": float(obj.get("left", 0)) + rad,
                "cy": float(obj.get("top", 0)) + rad,
                "radius": rad,
                "color": obj.get("stroke", "#1E88E5"),
                "fill_color": fill_val,
                "width": float(obj.get("strokeWidth", 2.0))
            }
            elements.append(elem)
        elif t == "path":
            pts = []
            for cmd in obj.get("path", []):
                if len(cmd) >= 3 and cmd[0] in ['M', 'L', 'Q']:
                    pts.append((float(cmd[1]), float(cmd[2])))
            if len(pts) >= 2:
                elements.append({
                    "type": "freedraw",
                    "points": pts,
                    "color": obj.get("stroke", "#000000"),
                    "width": float(obj.get("strokeWidth", 2.0))
                })
    return elements

def apply_editor_overlay_to_page(page: fitz.Page, overlay_bytes: bytes):
    """
    Incrusta un overlay transparente sobre la página respetando su rotación y matriz exacta.
    Garantiza posicionamiento milimétrico sin ningún desfase.
    """
    nat_rect = page.rect * page.derotation_matrix
    rot_val = page.rotation if hasattr(page, "rotation") else 0
    page.insert_image(nat_rect, stream=overlay_bytes, rotate=rot_val, overlay=True)

def apply_canvas_elements_to_pdf(
    pdf_input: Union[str, Path, bytes],
    output_path: Union[str, Path],
    elements: List[Dict[str, Any]],
    page_num: int = 0,
    canvas_width: float = 700.0,
    canvas_height: float = 900.0
) -> str:
    """
    Aplica una lista de figuras (flechas, círculos, rectángulos, líneas, textos, dibujos a mano alzada)
    procedentes de un canvas interactivo o generadas programáticamente a la página seleccionada del PDF.
    
    Escala automáticamente las coordenadas de la vista previa (canvas_width/height)
    a las dimensiones reales del documento PDF en puntos tipográficos (72 DPI).
    """
    if isinstance(pdf_input, bytes):
        doc = fitz.open(stream=pdf_input, filetype="pdf")
    else:
        doc = fitz.open(str(pdf_input))

    if page_num < 0 or page_num >= len(doc):
        page_num = 0

    page = doc[page_num]
    page_rect = page.rect
    pdf_w = page_rect.width
    pdf_h = page_rect.height

    # Factores de escala entre canvas y dimensiones del PDF
    scale_x = pdf_w / float(canvas_width) if canvas_width > 0 else 1.0
    scale_y = pdf_h / float(canvas_height) if canvas_height > 0 else 1.0

    for elem in elements:
        elem_type = elem.get("type", "").lower()

        # 1. Flecha
        if elem_type == "arrow":
            x1 = elem["x1"] * scale_x
            y1 = elem["y1"] * scale_y
            x2 = elem["x2"] * scale_x
            y2 = elem["y2"] * scale_y
            color = elem.get("color", "#E53935")
            width = float(elem.get("width", 2.5)) * scale_x
            head_size = float(elem.get("head_size", 14.0)) * scale_x
            opacity = float(elem.get("opacity", 1.0))
            draw_vector_arrow(page, (x1, y1), (x2, y2), color=color, width=width, head_size=head_size, opacity=opacity)

        # 2. Círculo / Óvalo
        elif elem_type in ["circle", "oval"]:
            if "cx" in elem and "cy" in elem:
                cx = elem["cx"] * scale_x
                cy = elem["cy"] * scale_y
                r = elem["radius"] * scale_x
                rect = (cx - r, cy - r, cx + r, cy + r)
            else:
                x = elem["x"] * scale_x
                y = elem["y"] * scale_y
                w = elem["w"] * scale_x
                h = elem["h"] * scale_y
                rect = (x, y, x + w, y + h)

            color = elem.get("color", "#1E88E5")
            fill_c = elem.get("fill_color", None)
            width = float(elem.get("width", 2.0)) * scale_x
            opacity = float(elem.get("opacity", 1.0))
            fill_opacity = float(elem.get("fill_opacity", 0.3 if fill_c else 0.0))
            draw_vector_circle(page, rect, color=color, fill_color=fill_c, width=width, opacity=opacity, fill_opacity=fill_opacity)

        # 3. Rectángulo / Cuadrado
        elif elem_type in ["rect", "rectangle"]:
            x = elem["x"] * scale_x
            y = elem["y"] * scale_y
            w = elem["w"] * scale_x
            h = elem["h"] * scale_y
            rect = (x, y, x + w, y + h)
            color = elem.get("color", "#43A047")
            fill_c = elem.get("fill_color", None)
            width = float(elem.get("width", 2.0)) * scale_x
            radius = float(elem.get("radius", 0.0)) * scale_x
            opacity = float(elem.get("opacity", 1.0))
            fill_opacity = float(elem.get("fill_opacity", 0.3 if fill_c else 0.0))
            draw_vector_rect(page, rect, color=color, fill_color=fill_c, width=width, radius=radius, opacity=opacity, fill_opacity=fill_opacity)

        # 4. Línea
        elif elem_type == "line":
            x1 = elem["x1"] * scale_x
            y1 = elem["y1"] * scale_y
            x2 = elem["x2"] * scale_x
            y2 = elem["y2"] * scale_y
            color = elem.get("color", "#000000")
            width = float(elem.get("width", 2.0)) * scale_x
            opacity = float(elem.get("opacity", 1.0))
            dashed = bool(elem.get("dashed", False))
            draw_vector_line(page, (x1, y1), (x2, y2), color=color, width=width, opacity=opacity, dashed=dashed)

        # 5. Texto
        elif elem_type == "text":
            x = elem["x"] * scale_x
            y = elem["y"] * scale_y
            text = elem.get("text", "")
            fontsize = float(elem.get("fontsize", 14.0)) * scale_y
            color = elem.get("color", "#000000")
            bg_color = elem.get("bg_color", None)
            bold = bool(elem.get("bold", False))
            italic = bool(elem.get("italic", False))
            add_vector_text(page, (x, y), text, fontsize=fontsize, color=color, bg_color=bg_color, bold=bold, italic=italic)

        # 6. Censura / Redact (Función Premium iLovePDF)
        elif elem_type in ["redact", "censura"]:
            x = elem["x"] * scale_x
            y = elem["y"] * scale_y
            w = elem["w"] * scale_x
            h = elem["h"] * scale_y
            rect = (x, y, x + w, y + h)
            fill_color = elem.get("color", "#000000")
            text = elem.get("text", "")
            add_permanent_redaction(page, rect, fill_color=fill_color, text=text)

        # 7. Resaltado (Highlighter)
        elif elem_type in ["highlight", "resaltador"]:
            x = elem["x"] * scale_x
            y = elem["y"] * scale_y
            w = elem["w"] * scale_x
            h = elem["h"] * scale_y
            rect = (x, y, x + w, y + h)
            color = elem.get("color", "#FFEB3B")
            draw_vector_rect(page, rect, color=color, fill_color=color, width=0, opacity=0.5, fill_opacity=0.5)

        # 8. Trazo a mano alzada (Freedraw / Path)
        elif elem_type in ["freedraw", "path"]:
            points = elem.get("points", [])
            if len(points) >= 2:
                shape = page.new_shape()
                c = parse_color(elem.get("color", "#000000"))
                w = float(elem.get("width", 2.0)) * scale_x
                op = float(elem.get("opacity", 1.0))
                
                scaled_pts = [fitz.Point(pt[0] * scale_x, pt[1] * scale_y) for pt in points]
                for i in range(len(scaled_pts) - 1):
                    shape.draw_line(scaled_pts[i], scaled_pts[i + 1])
                shape.finish(color=c, width=w, stroke_opacity=op)
                shape.commit()

        # 9. Imagen / Firma
        elif elem_type in ["image", "signature", "stamp"]:
            x = elem["x"] * scale_x
            y = elem["y"] * scale_y
            w = elem["w"] * scale_x
            h = elem["h"] * scale_y
            rect = (x, y, x + w, y + h)
            img_data = elem.get("data")
            if img_data:
                add_image_overlay(page, rect, img_data)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path), deflate=True, garbage=3)
    doc.close()
    return str(output_path)

def apply_all_figures_to_pdf(
    pdf_input: Union[str, Path, bytes],
    output_path: Union[str, Path],
    figures_by_page: Dict[int, List[Dict[str, Any]]]
) -> str:
    """
    Aplica figuras vectoriales a múltiples páginas de un documento PDF.
    figures_by_page es un diccionario {page_num: [lista_de_figuras]}.
    """
    if isinstance(pdf_input, bytes):
        doc = fitz.open(stream=pdf_input, filetype="pdf")
    else:
        doc = fitz.open(str(pdf_input))

    for page_num, elements in figures_by_page.items():
        if 0 <= page_num < len(doc) and elements:
            page = doc[page_num]
            for elem in elements:
                elem_type = elem.get("type", "").lower()
                if elem_type == "arrow":
                    draw_vector_arrow(
                        page, 
                        (elem["x1"], elem["y1"]), 
                        (elem["x2"], elem["y2"]),
                        color=elem.get("color", "#E53935"),
                        width=float(elem.get("width", 2.5)),
                        head_size=float(elem.get("head_size", 14.0)),
                        opacity=float(elem.get("opacity", 1.0))
                    )
                elif elem_type in ["circle", "oval"]:
                    if "cx" in elem and "cy" in elem:
                        cx = elem["cx"]
                        cy = elem["cy"]
                        r = elem["radius"]
                        rect = (cx - r, cy - r, cx + r, cy + r)
                    else:
                        rect = (elem["x"], elem["y"], elem["x"] + elem["w"], elem["y"] + elem["h"])
                    draw_vector_circle(
                        page, 
                        rect,
                        color=elem.get("color", "#1E88E5"),
                        fill_color=elem.get("fill_color", None),
                        width=float(elem.get("width", 2.0)),
                        opacity=float(elem.get("opacity", 1.0)),
                        fill_opacity=float(elem.get("fill_opacity", 0.3 if elem.get("fill_color") else 0.0))
                    )
                elif elem_type in ["rect", "rectangle"]:
                    rect = (elem["x"], elem["y"], elem["x"] + elem["w"], elem["y"] + elem["h"])
                    draw_vector_rect(
                        page, 
                        rect,
                        color=elem.get("color", "#43A047"),
                        fill_color=elem.get("fill_color", None),
                        width=float(elem.get("width", 2.0)),
                        opacity=float(elem.get("opacity", 1.0)),
                        fill_opacity=float(elem.get("fill_opacity", 0.3 if elem.get("fill_color") else 0.0))
                    )
                elif elem_type == "line":
                    draw_vector_line(
                        page, 
                        (elem["x1"], elem["y1"]), 
                        (elem["x2"], elem["y2"]),
                        color=elem.get("color", "#000000"),
                        width=float(elem.get("width", 2.0)),
                        opacity=float(elem.get("opacity", 1.0)),
                        dashed=bool(elem.get("dashed", False))
                    )
                elif elem_type == "text":
                    add_vector_text(
                        page, 
                        (elem["x"], elem["y"]), 
                        elem.get("text", ""),
                        fontsize=float(elem.get("fontsize", 14.0)),
                        color=elem.get("color", "#000000"),
                        bg_color=elem.get("bg_color", None),
                        bold=bool(elem.get("bold", False)),
                        italic=bool(elem.get("italic", False))
                    )
                elif elem_type in ["redact", "censura"]:
                    rect = (elem["x"], elem["y"], elem["x"] + elem["w"], elem["y"] + elem["h"])
                    add_permanent_redaction(page, rect, fill_color=elem.get("color", "#000000"), text=elem.get("text", ""))
                elif elem_type in ["highlight", "resaltador"]:
                    rect = (elem["x"], elem["y"], elem["x"] + elem["w"], elem["y"] + elem["h"])
                    color = elem.get("color", "#FFEB3B")
                    draw_vector_rect(page, rect, color=color, fill_color=color, width=0, opacity=0.5, fill_opacity=0.5)
                elif elem_type in ["image", "signature", "stamp"]:
                    rect = (elem["x"], elem["y"], elem["x"] + elem["w"], elem["y"] + elem["h"])
                    if elem.get("data"):
                        add_image_overlay(page, rect, elem["data"])

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path), deflate=True, garbage=3)
    doc.close()
    return str(output_path)
