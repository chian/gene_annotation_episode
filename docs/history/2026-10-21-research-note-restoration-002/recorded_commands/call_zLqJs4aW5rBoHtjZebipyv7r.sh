rg -n 'JSON pointer `/`|causal_cas2' research/slotted_process_library/CURRENT_SLOT_SOURCES.md && .venv/bin/python - <<'PY'
from pathlib import Path
p=Path('research/slotted_process_library/CURRENT_SLOT_SOURCES.md')
text=p.read_text()
old='(JSON pointer `/`)'
print('Incorrect root locators:',text.count(old))
text=text.replace(old,'(document root, JSON pointer `""`)')
p.write_text(text)
PY