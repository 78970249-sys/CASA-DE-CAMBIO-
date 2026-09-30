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


def _arreglar_consola() -> None:
    """Evita errores de codificación de acentos en consolas Windows."""
    for flujo in (sys.stdout, sys.stderr):
        reconfigure = getattr(flujo, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def main() -> None:
    from src.services.app_service import AppService
    servicio = AppService()

    if len(sys.argv) > 1 and sys.argv[1].strip().lower() in ("cli", "--cli"):
        from src.ui.cli_interface import MenuCLI
        MenuCLI(servicio).ejecutar()
        return

    from src.ui.gui_app import CasaDeCambioApp
    app = CasaDeCambioApp(servicio)
    app.iniciar()


if __name__ == "__main__":
    _arreglar_consola()
    main()