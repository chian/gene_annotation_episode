"""Reproduce the052 scalar display repair without altering its baseline proof."""
import hashlib
import json
from pathlib import Path
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
    store, context, args = setup(OUT / 'scalar_display_002', change, extra=extra)
    with store:
        repo = LiteratureBindingInteractionRepository(store, context.run_id)
        outcome = repo.populate(context, args, 'scalar-display-repair')
        raw, = project(repo, outcome, ['parameter_rr'])
        role = raw['roles'][ROLES[0]]
        assert role['values']['scalar_native']['exact_count'] == 73
        assert role['values']['scalar_native']['confidence_level'] == 95
        assert role['values']['uncertainty']['exact_count'] is None
        assert role['values']['uncertainty']['confidence_level'] is None
        records = {r['id']: r for r in store.list('reference')}
        def render(rows):
            parts = []
            render_received(parts, rows, records, section=_section, table=_table, values=_values)
            return '\n'.join(parts)
        shown = render([raw])
        assert '| exact_count | qualified | ge | false | false | selected_literal | exact |' in shown
        assert '| confidence_level | qualified | eq | true | true | selected_literal | exact |' in shown
        assert '73' in shown and '95' in shown
        derived = render(project(repo, outcome, ['interaction_ratio']))
        assert 'requested scalar reading meanings' not in derived
        assert '73' not in derived and '95' not in derived
        assert not store.list('observation') and not store.list('assessment')
    receipt = {'passed': True, 'helper_sha256': hashlib.sha256((ROOT / 'gene_annotation_episode/literature_binding_interaction_render.py').read_bytes()).hexdigest(),
        'qualified_count_ge_preserved': True, 'confidence_approximate_percent_preserved': True,
        'derived_unrequested_scalar_numbers_hidden': True, 'observations_created': 0,
        'scope': 'Synthetic direct source-to-return-to-display reproduction; actual provider transport covered by owner005 tests, no real-paper/model claim'}
    with (OUT / 'SCALAR_DISPLAY_RECEIPT_002.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
