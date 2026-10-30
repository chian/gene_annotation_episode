"""Synthetic recovery probe: completed contract reply must have a valid own query."""
import hashlib
import json
from pathlib import Path
import runpy
import sys
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
STAGE = BASE / 'a105_contract_information_design_059/connected_stage_004'
PIN = STAGE / 'pin_006'
sys.path.insert(0, str(PIN))
sys.path.insert(0, str(PIN / 'tests'))

from gene_annotation_episode.composition_information import requested_contract_information
from gene_annotation_episode.runtime import WorkflowError
from method_loop.durable import canonical


def main():
    helpers = runpy.run_path(str(PIN / 'tests/test_contract_information_runtime_059.py'))
    provider = helpers['PresentedProvider']([])
    directory = HERE / 'invalid_query_fixture_001'
    directory.mkdir()
    store, workflow, episode, args = helpers['workflow'](directory, provider)
    provider.script = iter([helpers['information']('episode.operation_contract',
        operation='literature.kinetic.populate', extra='invalid_closed_query')])
    original_resolve = workflow.decision_exchanges.resolve_lookup

    def interrupt_after_committed_reply(*args, **kwargs):
        original_resolve(*args, **kwargs)
        raise OSError('synthetic interruption immediately after recorded reply')

    try:
        with patch.object(workflow.decision_exchanges, 'resolve_lookup', interrupt_after_committed_reply):
            try:
                helpers['run_child'](episode, workflow)
            except OSError as error:
                assert 'immediately after' in str(error)
            else:
                raise AssertionError('Expected the explicit synthetic interruption')
        rows = workflow.decision_exchanges.rows(episode.source.episode_id, 0)
        assert len(rows) == 1 and rows[0]['lookup_result']['status'] == 'invalid'
        saved = json.loads(workflow.journal.row('runtime_model_calls', episode.source.episode_id, 0)['request'])
        episode.source.validate_contract_exchange_history(saved, 0)
        record = workflow.validate_contract_information(saved)
        replacement = workflow.contract_information_reply(saved, record, 'episode.operation_contract',
            {'operation': 'literature.kinetic.populate'})
        assert replacement['status'] == 'completed'
        # Deliberate corruption of ONE owned synthetic fixture row. Original
        # inputs/query/frame/schema remain untouched, as do all other runs.
        store.db.execute('update runtime_decision_exchanges set lookup_result=? where run_id=? and episode_id=? and decision_index=0 and exchange_index=0',
                         (canonical(replacement), workflow.run_id, episode.source.episode_id))
        rejected = None
        try:
            episode.source.validate_contract_exchange_history(saved, 0)
        except WorkflowError as error:
            rejected = str(error)
        changed = workflow.decision_exchanges.rows(episode.source.episode_id, 0)
        explicit_information = requested_contract_information([{'lookup_result': changed[0]['lookup_result']}])
        counts = {name: store.db.execute('select count(*) from ' + name).fetchone()[0]
                  for name in ('runtime_actions', 'runtime_observations')}
        assert counts == {'runtime_actions': 0, 'runtime_observations': 0}
        imports = {name: str(Path(module.__file__).resolve().relative_to(PIN.resolve()))
                   for name, module in tuple(sys.modules.items())
                   if name.startswith(('gene_annotation_episode', 'method_loop')) and getattr(module, '__file__', None)}
        receipt = {'scope': 'Owned invented fixture only. Deliberate saved-reply corruption after a valid original invalid-query result; no scientific/model execution or oldrun/shared modification.',
                   'pin': str(PIN), 'runtime_sha256': hashlib.sha256((PIN / 'gene_annotation_episode/runtime.py').read_bytes()).hexdigest(),
                   'original_closed_query_has_extra_field': True, 'original_reply_status': rows[0]['lookup_result']['status'],
                   'original_query_and_frame_unchanged': rows[0]['request'] == changed[0]['request'] and rows[0]['response'] == changed[0]['response'],
                   'substituted_completed_contract_reply_rejected': rejected is not None,
                   'rejection': rejected, 'selected_information_records_after_substitution': len(explicit_information),
                   'counts': counts, 'imports_from_pin': len(imports), 'new_scientific_source_or_model_run': False}
        with (HERE / 'INVALID_QUERY_REPLY_RECEIPT_001.json').open('x') as stream:
            json.dump(receipt, stream, indent=2)
            stream.write('\n')
        print(json.dumps(receipt))
    finally:
        store.close()


if __name__ == '__main__':
    main()
