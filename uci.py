"""UCI entry point: `python uci.py` (what lichess-bot runs)."""
from lcbot.uci import UCIEngine

if __name__ == "__main__":
    UCIEngine().run()
