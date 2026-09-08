import os
import sys
import re
import time
import subprocess
import webbrowser
import socket
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CLOUDFLARED_EXE = BASE_DIR / "bin" / "cloudflared.exe"

def port_is_open(port, host="127.0.0.1"):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False

def main():
    print("=" * 65)
    print("   CONVERTIDOR UNIVERSAL - COMPARTIR EN LINEA (100% GRATIS)")
    print("=" * 65)

    if not CLOUDFLARED_EXE.is_file():
        print("Error: No se encontro cloudflared.exe en bin/")
        input("Presiona ENTER para salir...")
        return

    # 1. Iniciar servidor Streamlit
    print("\n[1/3] Iniciando servidor web local en puerto 8501...")
    streamlit_cmd = [
        sys.executable, "-m", "streamlit", "run", "web_app.py",
        "--server.port=8501",
        "--server.headless=true",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false"
    ]

    streamlit_proc = subprocess.Popen(
        streamlit_cmd,
        cwd=str(BASE_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW
    )

    # 2. Esperar a que Streamlit este listo
    print("[2/3] Esperando a que el servidor este listo", end="", flush=True)
    for i in range(30):
        if port_is_open(8501):
            print(" OK!")
            break
        print(".", end="", flush=True)
        time.sleep(1)
    else:
        print("\nError: El servidor no inicio a tiempo.")
        streamlit_proc.terminate()
        input("Presiona ENTER para salir...")
        return

    time.sleep(1)

    # 3. Iniciar tunel Cloudflare
    print("[3/3] Generando enlace publico seguro con Cloudflare...\n")
    tunnel_proc = subprocess.Popen(
        [str(CLOUDFLARED_EXE), "tunnel", "--url", "http://127.0.0.1:8501"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    public_url = None
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    start = time.time()
    while time.time() - start < 15:
        line = tunnel_proc.stdout.readline()
        if not line:
            break
        match = url_pattern.search(line)
        if match:
            public_url = match.group(0)
            break

    if public_url:
        print("=" * 65)
        print("")
        print("  TU CONVERTIDOR ESTA PUBLICADO Y ACTIVO EN LA WEB!")
        print("")
        print("  Abre este enlace desde CUALQUIER computador o celular:")
        print(f"  >>> {public_url}")
        print("")
        print("=" * 65)
        print("")
        print("  IMPORTANTE: Mantene esta ventana abierta mientras")
        print("  quieras que el enlace siga funcionando.")
        print("  Para apagar el servicio: cierra esta ventana o Ctrl+C")
        print("")
        print("=" * 65)

        try:
            webbrowser.open(public_url)
        except Exception:
            pass

        try:
            while True:
                time.sleep(1)
                if streamlit_proc.poll() is not None:
                    print("\nEl servidor web se detuvo inesperadamente.")
                    break
                if tunnel_proc.poll() is not None:
                    print("\nEl tunel se desconecto.")
                    break
        except KeyboardInterrupt:
            print("\nApagando...")
    else:
        print("No se pudo obtener el enlace publico de Cloudflare.")
        print("Intenta cerrar y ejecutar nuevamente.")

    try:
        tunnel_proc.terminate()
    except Exception:
        pass
    try:
        streamlit_proc.terminate()
    except Exception:
        pass

if __name__ == "__main__":
    main()
