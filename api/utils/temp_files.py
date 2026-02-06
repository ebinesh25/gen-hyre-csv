from pathlib import Path

TEMP_DIR = Path(__file__).parent.parent.parent / "temp"
TEMP_DIR.mkdir(exist_ok=True)
