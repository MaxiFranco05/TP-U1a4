"""Script de empaquetado para la entrega final del Parcial Capítulos 1 a 6.

Genera el archivo .zip con las dos carpetas requeridas por la consigna:
- parcial/: Proyecto ampliado (código fuente, migrations/, test/, evidencia/, seed.py, README.md, etc.)
- despliegue/: TP 1-4 dockerizado (app/, migrations/, requirements.txt, Dockerfile, DEPLOY.md, evidencia/, etc.)

Excluye estrictamente:
- .venv / entornos virtuales
- __pycache__ / artefactos compilados (.pyc, etc.)
- .git / historial de control de versiones
- .env / archivos con secretos de entorno local
- Cachés de pytest o editores (.pytest_cache, .vscode, etc.)

Uso:
    python scripts/empaquetar_entrega.py
"""

from pathlib import Path
import sys
import zipfile

EXCLUDED_DIRS = {
    ".venv",
    "venv",
    "env",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".idea",
    ".vscode",
    ".gemini",
    ".agents",
    ".opencode",
    ".atl",
}

EXCLUDED_FILES = {
    ".env",
    ".active-orchestrator-state.json",
}

EXCLUDED_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".zip",
}


def debe_excluir(rel_path: Path) -> bool:
    """Determina si una ruta relativa debe ser excluida del paquete de entrega."""
    for part in rel_path.parts:
        if part in EXCLUDED_DIRS or part.startswith(".venv"):
            return True
        if part.startswith("__pycache__"):
            return True

    filename = rel_path.name
    if filename in EXCLUDED_FILES or filename.endswith(".env"):
        return True

    if rel_path.suffix.lower() in EXCLUDED_EXTENSIONS:
        return True

    return False


def crear_paquete_entrega(
    destino_zip: Path | str | None = None,
    nombre_grupo: str = "LocalHost",
    root_dir: Path | None = None,
) -> Path:
    """Empaqueta el proyecto en un archivo .zip con las carpetas parcial/ y despliegue/."""
    if root_dir is None:
        root_dir = Path(__file__).resolve().parent.parent

    if destino_zip is None:
        destino_zip = root_dir / f"Parcial_Cap1a6_{nombre_grupo}.zip"
    else:
        destino_zip = Path(destino_zip)

    destino_zip.parent.mkdir(parents=True, exist_ok=True)

    archivos_parcial = 0
    archivos_despliegue = 0

    with zipfile.ZipFile(destino_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in root_dir.rglob("*"):
            if not p.is_file():
                continue

            rel_to_root = p.relative_to(root_dir)

            # Evitar empaquetar el propio zip de salida
            if p.resolve() == destino_zip.resolve():
                continue

            # Comprobar exclusiones
            if debe_excluir(rel_to_root):
                continue

            # Mapear según carpeta: despliegue/ va a despliegue/, el resto a parcial/
            if len(rel_to_root.parts) > 0 and rel_to_root.parts[0] == "despliegue":
                arcname = str(rel_to_root).replace("\\", "/")
                zf.write(p, arcname=arcname)
                archivos_despliegue += 1
            else:
                arcname = f"parcial/{str(rel_to_root).replace('\\', '/')}"
                zf.write(p, arcname=arcname)
                archivos_parcial += 1

    print(f"[OK] Archivo de entrega generado: {destino_zip}")
    print(f"     - parcial/:    {archivos_parcial} archivos")
    print(f"     - despliegue/: {archivos_despliegue} archivos")
    return destino_zip


if __name__ == "__main__":
    grupo = sys.argv[1] if len(sys.argv) > 1 else "LocalHost"
    crear_paquete_entrega(nombre_grupo=grupo)
