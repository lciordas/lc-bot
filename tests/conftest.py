import os
import sys
from pathlib import Path

# The engine's modules are flat scripts (constants.py, board.py, ...) at the
# project root, imported with absolute `import board` / `from board import
# ...` style — not a package. Put the root on sys.path so `tests/*.py` can
# import them the same way the modules import each other.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Headless SDL drivers; must be set before gui.py imports pygame.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
