from pathlib import Path
from PIL import Image

def convert_image(input_image_path, target_format="png", output_path=None, quality=95, progress_callback=None):
    """
    Convierte una imagen a otro formato (PNG, JPG, WEBP, BMP, TIFF, ICO).
    Maneja canales alfa (transparencias) adecuadamente.
    """
    input_image_path = Path(input_image_path)
    target_format = target_format.lower().replace(".", "")
    if target_format == "jpeg":
        target_format = "jpg"
        
    if not output_path:
        output_path = input_image_path.with_suffix(f".{target_format}")
    else:
        output_path = Path(output_path)
        
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if progress_callback:
        progress_callback(f"Procesando imagen {input_image_path.name} -> {target_format.upper()}...")
        
    with Image.open(input_image_path) as img:
        # Formatos que no soportan transparencia alfa (como JPEG)
        if target_format in ["jpg", "jpeg", "bmp"]:
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode != "RGBA":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[3])  # 3 es el canal alfa
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")
        elif target_format == "ico":
            # Iconos suelen requerir tamaños estándar
            img = img.resize((256, 256), Image.Resampling.LANCZOS)
            
        save_params = {}
        if target_format in ["jpg", "jpeg", "webp"]:
            save_params["quality"] = quality
            
        format_name = "JPEG" if target_format == "jpg" else target_format.upper()
        img.save(str(output_path), format=format_name, **save_params)
        
    if progress_callback:
        progress_callback(f"Imagen guardada: {output_path.name}")
    return str(output_path)
