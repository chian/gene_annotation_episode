.venv/bin/python - <<'PY'
from pathlib import Path
p=Path('research/slotted_process_library/CURRENT_SLOT_SOURCES.md')
s=p.read_text().replace('(document root, JSON pointer `""`)','— document root (JSON pointer `""`)')
p.write_text(s)
PY