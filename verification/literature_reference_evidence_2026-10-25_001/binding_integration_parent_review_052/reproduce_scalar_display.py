"""Synthetic source-to-render check of qualified binding scalar meanings."""
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from gene_annotation_episode.literature_binding_interaction_storage import LiteratureBindingInteractionRepository
from gene_annotation_episode.literature_binding_interaction_inputs import ROLES
from gene_annotation_episode.literature_binding_interaction_render import render_received
from gene_annotation_episode.literature_experimental_prompt import _section, _table, _values
from test_literature_binding_interaction_storage import setup, project
from test_literature_binding_interaction_inputs import fixture


def main():
    extra = 'reported CI; count at least 73; confidence about 95%'
    _, _, _, enum, literal, _ = fixture(extra=extra)
    def change(args):
        unc = args['roles'][ROLES[0]]['uncertainty']
        unc['statistic'] = enum('confidence_interval', 'reported CI')
        unc['exact_count'] = literal('at least 73')
        unc['confidence_level'] = literal('about 95%')
    store, context, args = setup(OUT / 'scalar_display_001', change, extra=extra)
    with store:
        repo = LiteratureBindingInteractionRepository(store, context.run_id)
        outcome = repo.populate(context, args, 'scalar-display')
        raw, = project(repo, outcome, ['parameter_rr'])
        metadata = raw['roles'][ROLES[0]]
        assert metadata['uncertainty']['exact_count']['status'] == 'qualified'
        assert metadata['uncertainty']['exact_count']['relation'] == 'ge'
        assert metadata['values']['scalar_native']['exact_count'] == 73
        assert metadata['values']['uncertainty']['exact_count'] is None
        assert metadata['uncertainty']['confidence_level']['approximate'] is True
        assert metadata['uncertainty']['confidence_level']['percent'] is True
        parts = []
        render_received(parts, [raw], {r['id']: r for r in store.list('reference')},
            section=_section, table=_table, values=_values)
        rendered = '\n'.join(parts)
        assert '73' in rendered and '95' in rendered
        assert 'qualified' not in rendered and not re.search(r'\bge\b', rendered)
        assert 'approximate' not in rendered and 'percent' not in rendered
        assert not store.list('observation') and not store.list('assessment')
    path = ROOT / 'gene_annotation_episode/literature_binding_interaction_render.py'
    receipt = {'reproduced': True, 'scope': 'Synthetic direct renderer; not actual model/provider transport',
        'helper_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'typed_count': {'reported_value': 73, 'exact_count': None, 'status': 'qualified', 'relation': 'ge'},
        'typed_confidence': {'native_value': 95, 'approximate': True, 'percent': True},
        'displayed_native_numerals': [73, 95], 'display_omits_scalar_qualification_meanings': True,
        'runtime_observations_created': 0, 'scientific_source_read': False}
    with (OUT / 'SCALAR_DISPLAY_BASELINE_001.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
