from pathlib import Path
import sys,hashlib,json
P=Path(__file__).parent;R=P.parents[1];out=P/sys.argv[1]
if out.exists():raise RuntimeError('Receipt already exists')
files=['gene_annotation_episode/literature_measurement_comparison_inputs.py','gene_annotation_episode/literature_measurement_comparison_calculations.py','gene_annotation_episode/literature_measurement_comparison_prompt.py','tests/test_literature_measurement_comparison_components_258.py']
rows=[]
for name in files:
 raw=(R/name).read_bytes();target=out/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);rows.append({'path':name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
(out/'MANIFEST.json').write_text(json.dumps(rows,indent=2)+'\n')
