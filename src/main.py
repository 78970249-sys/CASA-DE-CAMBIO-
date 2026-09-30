# -*- coding: utf-8 -*-
"""Punto de entrada de CasaDeCambio (Célula 3 · Composición).

Uso:
    py src/main.py            -> abre la interfaz gráfica (tkinter)
    py src/main.py cli        -> abre el menú de consola

Para que los módulos del paquete ``src`` sean importables desde la raíz
del proyecto (tanto lanzando ``python src/main.py`` como
``python -m src.main``), se agrega la raíz del proyecto a ``sys.path``.

Los datos persisten en la carpeta ``data/`` del proyecto.
"""

from __future__ import annotations

import os
import sys

RAIZ_PROYECTO: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ_PROYECTO not in sys.path:
    sys.path.insert(0, RAIZ_PROYECTO)

APP_NAME = "CasaDeCambio"
APP_VERSION = "1.0.0"


def _arreglar_consola() -> None:
    """Evita errores de codificación de acentos en consolas Windows."""
    for flujo in (sys.stdout, sys.stderr):
        reconfigure = getattr(flujo, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def _color(texto: str, codigo: str = "") -> str:
    """Añade color a la salida en terminal si está disponible."""
    if not sys.stdout.isatty():
        return texto
    return f"\033[{codigo}m{texto}\033[0m" if codigo else texto


def _mostrar_banner() -> None:
    """Muestra un banner elegante al iniciar la aplicación."""
    banner = [
        "",
        _color("========================================", "1;36"),
        _color(f" {APP_NAME} v{APP_VERSION} ".center(40), "1;33"),
        _color("========================================", "1;36"),
        _color(" Sistema de cambio de divisas ".center(40), "1;32"),
        _color(" Detección de cambios y operaciones ".center(40), "1;32"),
        _color("========================================", "1;36"),
        "",
    ]
    print("\n".join(banner))


def _mostrar_ayuda() -> None:
    """Muestra opciones de arranque disponibles."""
    print(_color(f"{APP_NAME} - Ayuda de ejecución", "1;36"))
    print("")
    print("Uso:")
    print("  py src/main.py                -> inicia la interfaz gráfica")
    print("  py src/main.py cli           -> inicia el menú de consola")
    print("  py src/main.py --cli         -> idem")
    print("  py src/main.py --gui         -> fuerza la GUI")
    print("  py src/main.py --help        -> muestra esta ayuda")
    print("  py src/main.py --version     -> muestra la versión")


def _es_terminal_interactivo() -> bool:
    """Retorna True si la consola acepta interacción humana."""
    try:
        return sys.stdin is not None and sys.stdin.isatty() and sys.stdout is not None and sys.stdout.isatty()
    except Exception:
        return False


def main() -> None:
    from src.services.app_service import AppService

    servicio = AppService()
    argumentos = [arg.strip().lower() for arg in sys.argv[1:]]

    if "--help" in argumentos or "-h" in argumentos:
        _mostrar_banner()
        _mostrar_ayuda()
        return

    if "--version" in argumentos or "-v" in argumentos:
        print(f"{APP_NAME} v{APP_VERSION}")
        return

    if "cli" in argumentos or "--cli" in argumentos:
        _mostrar_banner()
        from src.ui.cli_interface import MenuCLI
        MenuCLI(servicio).ejecutar()
        return

    if "gui" in argumentos or "--gui" in argumentos:
        from src.ui.gui_app import CasaDeCambioApp
        app = CasaDeCambioApp(servicio)
        app.iniciar()
        return

    if _es_terminal_interactivo():
        _mostrar_banner()
        print(_color("Modo de inicio: GUI por defecto (usar 'cli' para consola)", "1;35"))

    try:
        from src.ui.gui_app import CasaDeCambioApp
        app = CasaDeCambioApp(servicio)
        app.iniciar()
    except Exception as exc:
        print(_color(f"No se pudo abrir la interfaz gráfica: {exc}", "1;31"), file=sys.stderr)
        print(_color("Intentando abrir el modo consola como alternativa...", "1;33"))
        try:
            from src.ui.cli_interface import MenuCLI
            MenuCLI(servicio).ejecutar()
        except Exception as cli_error:
            print(_color(f"Error al iniciar la consola: {cli_error}", "1;31"), file=sys.stderr)
            print(_color("Ejecute: py src/main.py --help", "1;36"))
            raise


if __name__ == "__main__":
    _arreglar_consola()
    main()

