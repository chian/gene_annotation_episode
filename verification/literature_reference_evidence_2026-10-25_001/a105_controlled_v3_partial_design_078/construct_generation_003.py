"""Additive dependency precision correction; keep001/002 unchanged."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE/'build_declarations_002.py').read_text().replace("_002.json'","_003.json'")
s=s.replace("'unresolved_readings':arr(ref('ReadingSelector'),uniqueItems=True)})", "'unresolved_readings':arr(ref('ReadingSelector'),uniqueItems=True),\n    'numeric_fields':arr(obj({'reading':ref('ReadingSelector'),'fields':arr(enum('value','threshold','relation','approximate','unit','status','origin','digitization_interval','digitization_interval_presence'),uniqueItems=True)})),\n    'full_source_covariance_required':B})")
with (HERE/'build_declarations_003.py').open('x') as f:f.write(s)
exec(compile(s,str(HERE/'build_declarations_003.py'),'exec'),{'__file__':str(HERE/'build_declarations_003.py'),'__name__':'__main__'})
