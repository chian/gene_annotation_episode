from pathlib import Path
HERE=Path(__file__).resolve().parent
with (HERE/'verify_design_004.py').open('x') as f:f.write((HERE/'verify_design_003.py').read_text().replace('_003','_004'))
