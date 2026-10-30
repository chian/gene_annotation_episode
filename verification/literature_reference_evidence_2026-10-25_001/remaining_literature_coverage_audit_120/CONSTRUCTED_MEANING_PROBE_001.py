"""Synthetic-only counterexample: global partner subject and actual arm subject disagree."""
import json
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tests'))
sys.path.insert(0, str(ROOT))
from test_literature_partner_native_storage import fixture
from gene_annotation_episode.literature_partner_storage import LiteraturePartnerRepository

HERE = Path(__file__).parent
store, context, args, records = fixture(HERE / 'constructed_subject_mismatch_state')
args['literals']['subject'] = deepcopy(args['literals']['partner'])
with store:
    repo = LiteraturePartnerRepository(store, context.run_id)
    outcome = repo.populate(context, args, 'audit-constructed-mismatch')
    result = {'kind': 'constructed_only_not_paper_validation', 'status': outcome['status']}
    if outcome['status'] == 'completed':
        saved = repo.read(outcome['result']['sheet_ref'])
        rows = repo.project_cells([outcome['result']['sheet_ref']], permitted_record_refs=outcome['record_refs'])
        result.update({
            'native_arm_subject_quote': args['arms']['reference']['subject']['quote'],
            'global_subject_quote': args['literals']['subject']['quote'],
            'typed_subject_label': store.get(rows[0]['subject_ref'])['label'],
            'reference_rate': rows[0]['value'],
            'values': {row['component']: row['value'] for row in rows},
            'observations': len(store.list('observation')),
            'assessments': len(store.list('assessment')),
            'actual_native_input_mode': saved['extraction']['version'],
        })
    else:
        result['feedback'] = outcome.get('feedback')
(HERE / 'CONSTRUCTED_MEANING_PROBE_001.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
