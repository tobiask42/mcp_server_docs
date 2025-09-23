from pathlib import Path

    
def count_lines(path: Path) -> int:
    with path.open("r", encoding="utf-8") as f:
        return sum(1 for ln in f if ln.strip())