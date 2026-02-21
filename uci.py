"""UCI entry point: `python uci.py` (what lichess-bot and tools/ab_test.py run)."""
from lcbot.uci import UCIEngine

if __name__ == "__main__":
    UCIEngine().run()
