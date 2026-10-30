"""Static proposal grammar/resource check, not a new selected implementation."""
from pathlib import Path
import json
import os
import sys
from copy import deepcopy

OWN=Path(__file__).resolve().parent;REPO=OWN.parents[1]
PIN=REPO/'verification/literature_reference_evidence_2026-10-25_001/a105_summary_precision_integration_review_256/joined_pin_008'
sys.dont_write_bytecode=True
sys.path[:]=[str(PIN),str(PIN/'tests'),*[p for p in sys.path if p and Path(p).resolve() not in (OWN,REPO)]]
os.chdir(PIN)
from gene_annotation_episode.communication import validate_closed_schema,validate_form,reference_resolver
from test_literature_compiled_assay_185 import readonly

def read(name):return json.loads((OWN/name).read_text())
declared=read('WORKSHEET_DECLARATION_PROPOSAL_001.json')
original=read('ORIGINAL_SCHEMA_001.json')
expanded=deepcopy(declared)
for field,source in [('native_parameter','literature_kinetic_cells'),('precision','literature_kinetic_summary_precision_cells')]:
    assert declared['properties'][field]=={'$ref':'episode-fact:'+source}
    expanded['properties'][field]=deepcopy(original['properties'][field])
validate_closed_schema(expanded)
form=read('ADMITTED_JOINT_FORM_001.json');form.pop('qualification')
form['assessment_context']={'version':'a105_source_evidence_worksheet_v1','assertion_refs':[],'quantity_links':[],'assertion_links':[]}
with readonly(OWN/'joint_existing_boundary_001/state') as cold:
    cold.db.create_function('library_scope_record',2,cold._scope_filter_record)
    scope=json.loads(cold.db.execute('SELECT request FROM runtime_episodes ORDER BY rowid LIMIT 1').fetchone()[0])['message']['scope']
    validate_form(form,expanded,reference_resolver(cold.references(scope)))
    assert cold.db.total_changes==0
result={'proposal_only':True,'closed_grammar':'passed','original_native_schema_nodes_unchanged':True,
    'summary_local_defs_resource_scope_preserved':True,'empty_discovery_context_valid':True,
    'actual_alias_runtime_expansion_executed':False,'constructor_implemented':False,'link_semantic_validator_implemented':False,
    'new_selected_actions':0,'new_scientific_observations':0}
(OWN/'PROPOSAL_GRAMMAR_CHECK_001.json').write_text(json.dumps(result,indent=2)+'\n')
