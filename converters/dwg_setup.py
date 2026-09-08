import os
import sys
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BIN_DIR = BASE_DIR / "bin"
LIBREDWG_WIN_URL = "https://github.com/LibreDWG/libredwg/releases/download/0.14/libredwg-0.14-win64.zip"
LIBREDWG_LINUX_URL = "https://api.anaconda.org/download/conda-forge/libredwg/0.11.3876/linux-64/libredwg-0.11.3876-py37pl5321h77fd288_2.tar.bz2"

def get_linux_env():
    """Configura las variables de entorno necesarias para LibreDWG en Linux."""
    env = os.environ.copy()
    linux_lib = BIN_DIR / "linux" / "lib"
    if linux_lib.is_dir():
        env["LD_LIBRARY_PATH"] = f"{linux_lib}:{env.get('LD_LIBRARY_PATH', '')}"
    return env

def get_dwg2pdf_path():
    """Retorna la ruta al ejecutable dwg2pdf segun el sistema operativo."""
    if os.name != 'nt':
        return shutil.which("dwg2pdf")
    
    local_exe = BIN_DIR / "dwg2pdf.exe"
    if local_exe.is_file():
        return str(local_exe)
    return shutil.which("dwg2pdf.exe") or shutil.which("dwg2pdf")

def get_dwg2dxf_path():
    """Retorna la ruta a dwg2dxf segun el sistema operativo."""
    # En Linux / Streamlit Cloud:
    if os.name != 'nt':
        sys_exe = shutil.which("dwg2dxf")
        if sys_exe:
            return sys_exe
        local_bin = BIN_DIR / "linux" / "bin" / "dwg2dxf"
        if local_bin.is_file():
            try:
                os.chmod(str(local_bin), 0o755)
            except Exception:
                pass
            return str(local_bin)
        return None

    # En Windows:
    local_exe = BIN_DIR / "dwg2dxf.exe"
    if local_exe.is_file():
        return str(local_exe)
    for p in BIN_DIR.glob("**/dwg2dxf.exe"):
        if p.is_file():
            return str(p)
    return shutil.which("dwg2dxf.exe") or shutil.which("dwg2dxf")

def get_dwg2svg_path():
    """Retorna la ruta a dwg2SVG segun el sistema operativo."""
    if os.name != 'nt':
        sys_exe = shutil.which("dwg2SVG") or shutil.which("dwg2svg")
        if sys_exe:
            return sys_exe
        local_bin = BIN_DIR / "linux" / "bin" / "dwg2SVG"
        if local_bin.is_file():
            try:
                os.chmod(str(local_bin), 0o755)
            except Exception:
                pass
            return str(local_bin)
        return None

    p = BIN_DIR / "dwg2SVG.exe"
    if p.is_file():
        return str(p)
    return shutil.which("dwg2SVG.exe") or shutil.which("dwg2SVG")

def ensure_libredwg(callback=None):
    """
    Verifica que LibreDWG este disponible.
    En Windows: descarga el zip para Windows si falta.
    En Linux: descarga y extrae el paquete para Linux si falta en el sistema.
    """
    if get_dwg2dxf_path():
        return True

    # Caso Linux / Streamlit Cloud
    if os.name != 'nt':
        linux_dir = BIN_DIR / "linux"
        linux_bin = linux_dir / "bin" / "dwg2dxf"
        if linux_bin.is_file():
            try:
                os.chmod(str(linux_bin), 0o755)
            except Exception:
                pass
            return True

        linux_dir.mkdir(parents=True, exist_ok=True)
        try:
            import urllib.request, tarfile, io, ssl
            if callback:
                callback("Instalando componentes CAD para Linux en la nube...")
            ctx = ssl._create_unverified_context()
            req = urllib.request.Request(LIBREDWG_LINUX_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
                data = resp.read()

            with tarfile.open(fileobj=io.BytesIO(data), mode='r:bz2') as tar:
                for m in tar.getmembers():
                    if m.name in ['bin/dwg2dxf', 'bin/dwg2SVG', 'lib/libredwg.so.0', 'lib/libredwg.so.0.0.11']:
                        tar.extract(m, path=str(linux_dir))

            for p in (linux_dir / "bin").glob("*"):
                try:
                    os.chmod(str(p), 0o755)
                except Exception:
                    pass

            return get_dwg2dxf_path() is not None
        except Exception as e:
            if callback:
                callback(f"Advertencia: No se pudo configurar LibreDWG en Linux: {e}")
            return False

    # Caso Windows
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = BIN_DIR / "libredwg.zip"
    try:
        import urllib.request, zipfile
        if callback:
            callback("Descargando componentes CAD (LibreDWG para Windows)...")
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(LIBREDWG_WIN_URL, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp, open(zip_path, 'wb') as out_f:
            shutil.copyfileobj(resp, out_f)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for member in zip_ref.namelist():
                filename = os.path.basename(member)
                if filename.endswith(".exe") or filename.endswith(".dll"):
                    source = zip_ref.open(member)
                    target = open(BIN_DIR / filename, "wb")
                    with source, target:
                        shutil.copyfileobj(source, target)

        if zip_path.exists():
            zip_path.unlink()
        return get_dwg2dxf_path() is not None
    except Exception as e:
        if callback:
            callback(f"Advertencia: No se pudo descargar LibreDWG: {e}")
        return False
