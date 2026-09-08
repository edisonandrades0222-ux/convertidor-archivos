import sys
from pathlib import Path
from huggingface_hub import HfApi

DEFAULT_REPO = "Edison1231321/convertidor_archivo"
BASE_DIR = Path(__file__).resolve().parent

def upload_space():
    print("=" * 60)
    print("SUBIDOR AUTOMÁTICO A HUGGING FACE SPACES")
    print("=" * 60)
    
    print("\n1. ¿Cuál es el nombre de tu Space en Hugging Face?")
    repo_input = input(f"Presiona ENTER para usar '{DEFAULT_REPO}' o escribe 'TuUsuario/TuSpace': ").strip()
    repo_id = repo_input if repo_input else DEFAULT_REPO
    if "/" not in repo_id:
        repo_id = f"Edison1231321/{repo_id}"

    print(f"\nRepositorio de destino seleccionado: {repo_id}")
    print("\n2. Pega tu Access Token de Hugging Face (con permiso WRITE):")
    print("👉 Puedes crearlo o copiarlo desde: https://huggingface.co/settings/tokens")
    token = input("Pega tu Token aquí y presiona ENTER: ").strip()
    if not token:
        print("\nError: No ingresaste el token.")
        return

    print(f"\nSubiendo todos los archivos a {repo_id}...")
    try:
        api = HfApi(token=token)
        api.upload_folder(
            folder_path=str(BASE_DIR),
            repo_id=repo_id,
            repo_type="space",
            ignore_patterns=[
                "__pycache__*",
                "test_samples*",
                "*.bat",
                "*.log",
                ".git*",
                "bin*",
                "subir_a_huggingface.py"
            ]
        )
        print("\n" + "=" * 60)
        print("¡SUBIDA COMPLETADA CON ÉXITO!")
        print(f"Tu aplicación se está construyendo en:")
        print(f"👉 https://huggingface.co/spaces/{repo_id}")
        print("=" * 60)
    except Exception as e:
        print(f"\nError al subir: {e}")

if __name__ == "__main__":
    upload_space()
