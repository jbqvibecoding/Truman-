import pathlib
import sys

# Ensure src/ is importable when running pytest from the repo root.
SRC = pathlib.Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
