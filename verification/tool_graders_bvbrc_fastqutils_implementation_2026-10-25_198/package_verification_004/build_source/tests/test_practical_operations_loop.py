"""Iterative repair and explicit retry through actual local episode operations."""
import asyncio
from copy import deepcopy
import hashlib
import json
import sys

from gene_annotation_episode.execution_inventory import make_catalog
from gene_annotation_episode.numerical import NumericBand
from gene_annotation_episode.state import Store
from test_practical_runtime import Choices, host, make_assignment, observations, run, selected


def test_missing_directory_validation_can_be_followed_by_repair(tmp_path):
    spec = make_assignment(tmp_path/'project')
    provider = Choices([
        selected('practical.context.set', {'cwd': str(spec.work), 'environment': {}}),
        selected('practical.directory.create', {'path': str(spec.work)}),
        selected('practical.context.set', {'cwd': str(spec.work), 'environment': {'PREP_VALUE': 'prepared'}}),
        selected('practical.context.set', {'cwd': str(spec.work), 'environment': {'PREP_VALUE': 'prepared'}}),
        selected('practical.file.write', {'path': str(spec.script), 'text': spec.body}),
        selected('practical.job.start')], collect_after=True)
    with Store(tmp_path/'state') as store:
        store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')
        bound = host(store, tmp_path/'run', spec.assignment, provider)
        record = run(bound)
        receipts = bound.binding.state(bound.context).receipts()
        assert receipts[0]['outcome']['native_outcome']['failure']['code'] == 'practical_working_directory_missing'
        assert receipts[0]['context_before'] == receipts[0]['context_after']
        assert receipts[2]['context_after']['revision'] == receipts[3]['context_after']['revision'] == 1
        assert observations(bound)[0]['step']['marginal_credit'] == 0
        assert record.controller_state.estimate.expected_next_gain == NumericBand.exact(0)


def test_failed_requested_job_can_be_explicitly_retried_after_repair(tmp_path):
    spec = make_assignment(tmp_path/'project', reuse=True)
    prefix = ('from pathlib import Path\n'
        'with Path("job-attempts").open("a") as f: f.write("attempt\\n")\n'
        'if not Path("repaired").exists(): raise SystemExit(3)\n')
    spec.script.write_text(prefix+spec.body)
    spec.assignment['progress_requirements'][3]['predicate']['sha256'] = hashlib.sha256(
        (prefix+spec.body).encode()).hexdigest()

    class RepairChoices(Choices):
        def __init__(self):
            super().__init__()
            self.stage = 'start'
            self.failed_id = None

        async def complete(self, episode_id, role, instructions, context, schema):
            self.contexts.append(deepcopy(context))
            if self.stage == 'start':
                self.stage = 'wait_failure'
                return selected('practical.job.start')
            if self.stage == 'retry':
                self.stage = 'wait_success'
                return selected('practical.job.start', {'retry_failed_execution_id': self.failed_id})
            receipt = context['last_local_outcome']['result']
            job = receipt['outcome']['facts'].get('requested_job')
            if self.stage == 'wait_failure' and job and job['status'] == 'failed':
                self.failed_id = job['execution_id']
                self.stage = 'retry'
                return selected('practical.file.write', {'path': str(spec.work/'repaired'), 'text': 'fixed'})
            await asyncio.sleep(.03)
            return selected('practical.job.collect')

    provider = RepairChoices()
    with Store(tmp_path/'state') as store:
        store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')
        bound = host(store, tmp_path/'run', spec.assignment, provider)
        record = run(bound)
        receipts = bound.binding.state(bound.context).receipts()
        starts = [r for r in receipts if r['tool_name'] == 'practical.job.start']
        assert len(starts) == 2
        assert starts[1]['arguments'] == {'retry_failed_execution_id': provider.failed_id}
        identities = {r['outcome']['facts']['requested_job']['execution_id'] for r in starts}
        assert len(identities) == 2
        assert (spec.work/'job-attempts').read_text() == 'attempt\nattempt\n'
        assert json.loads(spec.result.read_text())['nonce'] == spec.nonce
        assert record.controller_state.estimate.expected_next_gain == NumericBand.exact(0)


def test_selected_inventory_refresh_retains_original_bytes_and_snapshot(tmp_path):
    spec = make_assignment(tmp_path/'project', reuse=True)
    catalog = make_catalog(resource_id='local-fixture', workspace=str(spec.workspace), components=[])
    path = spec.workspace/'inventory.json'
    raw = json.dumps(catalog, indent=2).encode()
    path.write_bytes(raw)
    provider = Choices([selected('practical.inventory.refresh', {'path': str(path)}),
                        selected('practical.job.start')], collect_after=True)
    with Store(tmp_path/'state') as store:
        store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')
        bound = host(store, tmp_path/'run', spec.assignment, provider)
        run(bound)
        first = bound.binding.state(bound.context).receipts()[0]['outcome']
        import base64
        assert base64.b64decode(first['inventory_bytes_base64']) == raw
        assert first['inventory_snapshot']['catalog'] == catalog
        assert provider.contexts[1]['practical_current_inventory'] == first['inventory_snapshot']
        assert observations(bound)[0]['step']['marginal_credit'] == 0


def test_invalid_catalog_read_is_recorded_and_can_be_repaired(tmp_path):
    spec = make_assignment(tmp_path/'project', reuse=True)
    catalog = make_catalog(resource_id='local-fixture', workspace=str(spec.workspace), components=[])
    path = spec.workspace/'inventory.json'
    path.write_bytes(b'{bad-json')
    provider = Choices([selected('practical.inventory.refresh', {'path': str(path)}),
        selected('practical.file.write', {'path': str(path), 'text': json.dumps(catalog)}),
        selected('practical.inventory.refresh', {'path': str(path)}),
        selected('practical.job.start')], collect_after=True)
    with Store(tmp_path/'state') as store:
        store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')
        bound = host(store, tmp_path/'run', spec.assignment, provider)
        run(bound)
        receipts = bound.binding.state(bound.context).receipts()
        assert receipts[0]['outcome']['inventory_failure']['code'] == 'practical_inventory_catalog_invalid'
        assert 'inventory_snapshot' not in receipts[0]['outcome']
        assert receipts[2]['outcome']['inventory_snapshot']['catalog'] == catalog
        assert [row['step']['marginal_credit'] for row in observations(bound)[:3]] == [0, 0, 0]


def test_diagnostic_logs_and_selected_file_bytes_reach_next_decision(tmp_path):
    spec = make_assignment(tmp_path/'project', reuse=True)
    provider = Choices([selected('practical.command.run', {'argv': [sys.executable, '-c',
        'import sys; print("diagnostic-output"); print("repair-detail",file=sys.stderr); sys.exit(2)'],
        'environment': {}}),
        selected('practical.file.read', {'path': str(spec.script), 'offset': 7, 'limit': 29}),
        selected('practical.job.start')], collect_after=True)
    with Store(tmp_path/'state') as store:
        store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')
        bound = host(store, tmp_path/'run', spec.assignment, provider)
        run(bound)
        diagnostic = provider.contexts[1]['last_local_outcome']['result']['outcome']
        assert diagnostic['facts']['command']['returncode'] == 2
        assert 'diagnostic-output' in diagnostic['native_outcome']['stdout']['tail_utf8']
        assert 'repair-detail' in diagnostic['native_outcome']['stderr']['tail_utf8']
        window = provider.contexts[2]['last_local_outcome']['result']['outcome']['native_outcome']
        import base64
        assert window['offset'] == 7 and window['returned_bytes'] == 29
        assert base64.b64decode(window['bytes_base64']) == spec.body.encode()[7:36]


def test_malformed_command_is_rejected_before_durable_intent(tmp_path):
    spec = make_assignment(tmp_path/'project', reuse=True)
    provider = Choices([selected('practical.command.run', {'argv': ['bad\0argument'], 'environment': {}}),
                        selected('practical.job.start')], collect_after=True)
    with Store(tmp_path/'state') as store:
        store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')
        bound = host(store, tmp_path/'run', spec.assignment, provider)
        record = run(bound)
        receipts = bound.binding.state(bound.context).receipts()
        assert all(receipt['tool_name'] != 'practical.command.run' for receipt in receipts)
        assert len(provider.contexts) == record.units_consumed+1
        assert provider.contexts[1]['feedback']['code'] == 'invalid_practical_command_argument'
