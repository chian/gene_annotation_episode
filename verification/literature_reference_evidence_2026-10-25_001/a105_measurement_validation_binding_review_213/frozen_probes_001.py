"""Root synthetic probes of final scoped projection; no episode/model work."""
from pathlib import Path
import hashlib
import json
import os
import sys

BASE=Path(__file__).resolve().parent
PIN=BASE/'pin_001'
ROOT=Path('/home/chia/repos/gene_annotation_episode')
sys.dont_write_bytecode=True
sys.path=[str(PIN),str(PIN/'tests'),*[p for p in sys.path
    if Path(p or os.getcwd()).resolve() not in (ROOT,ROOT/'tests')]]
from test_literature_measurement_validation_205 import Source,run
from gene_annotation_episode.literature_measurement_validation_inputs import read_measurement_validation_inputs
from gene_annotation_episode.literature_measurement_validation_calculations import populate_measurement_validation
from gene_annotation_episode.literature_measurement_validation_storage import _project_saved

source=Source(content=Source().text.replace('<article><p>',
    '<article><p>Buffer20mM at pH7.4; construct E2. ').encode())
args=source.args()
start=source.content.index(b'<table>')
end=source.content.index(b'</table>')+len(b'</table>')
args['context']['mean_definition']=source.span(start,end)
args['context']['matrix']=source.witness('Buffer20mM at pH7.4')
data,sheet=run(source,args,source.recovery_rows())
saved={'extraction':data,'sheet':sheet,'input_source_ref':source.reference,
       'input_source_refs':[source.reference]}
rows=_project_saved(saved,'source_'+'a'*24,['reported_zprime'])
meaning=rows[0]['source_meanings']['mean_definition']
assert meaning['status']=='numerical_scope_unresolved'
assert meaning['unavailable_reason']=='unrequested_numerical_scope_unresolved'
assert '8.6' not in meaning['display_text'] and '8.72' not in meaning['display_text']
assert rows[0]['source_meanings']['matrix']['display_text']=='Buffer20mM at pH7.4'
assert data['context']['mean_definition']['value']==source.content[start:end].decode()
assert len(rows)==1 and rows[0]['component']=='reported_zprime' and rows[0]['value']==.99

# Deliberately minimal, adversarial context: the identical content-addressed
# bytes are also available as a text representation. A representation label
# must not change whether an unrequested physical numeric span is withheld.
args=source.args()
numeric=source.synthetic_number('within')['witness']
args['context']['mean_definition']={**numeric,'representation':'text'}
def received(reference,representation):
    assert reference==source.reference and representation in ('original','text')
    return {'artifact_ref':source.artifact,'content':source.content}
data=read_measurement_validation_inputs(args,read_source=received)
sheet=populate_measurement_validation(data)
saved={'extraction':data,'sheet':sheet,'input_source_ref':source.reference,
       'input_source_refs':[source.reference]}
rows=_project_saved(saved,'source_'+'b'*24,['reported_zprime'])
meaning=rows[0]['source_meanings']['mean_definition']
assert meaning['representation']=='text'
assert meaning['status']=='unrequested_numbers_withheld'
assert meaning['display_text']=='[unrequested numerical operand]'
assert '0.8' not in meaning['display_text']

# The same component name must preserve both distinct measurement instances.
rows=_project_saved(saved,'source_'+'b'*24,['reported_cv'])
assert [r['basis'] for r in rows]==['within_run','between_run']
assert [r['value'] for r in rows]==[.8,1.7]
assert len({(r['sheet_ref'],r['measurement_key'],r['component']) for r in rows})==2

manifest=json.loads((BASE/'PIN_001.json').read_text())
changed=[p for p,h in manifest['hashes'].items() if hashlib.sha256((PIN/p).read_bytes()).hexdigest()!=h]
assert not changed
imports={n:str(Path(m.__file__).resolve()) for n,m in sys.modules.items()
    if getattr(m,'__file__',None) and n.startswith(('gene_annotation_episode','method_loop','test_'))}
outside={n:p for n,p in imports.items() if not Path(p).is_relative_to(PIN)}
assert not outside
record={'scope':'Synthetic scoped-projection checks only; actual selected typed-return coverage is the separate pytest run.',
    'broad_table_partial_with_source_retained':True,'numeric_conditions_preserved':True,
    'same_artifact_different_representation_masked':True,'two_precision_instances_preserved':True,
    'imports':imports,'imports_outside_pin':outside,'changed_pinned_files':changed}
(BASE/'ROOT_FROZEN_PROBES_001.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='imports'}))
