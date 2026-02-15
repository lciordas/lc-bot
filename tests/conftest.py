import os
import sys
from pathlib import Path

# Project root on sys.path so tests can import gui.py and each other.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Headless SDL drivers; must be set before gui.py imports pygame.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
