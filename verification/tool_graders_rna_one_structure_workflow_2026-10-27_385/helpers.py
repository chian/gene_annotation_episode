"""One original360 supplied structure followed by a selected retained return.

Only the controlled parent's third commission changes from360's saved-sheet
example. Production assignment validation, inheritance, source authentication,
results collection, typed return and completion remain the actual Workflow.
The original setup runs supplied_features with energy_mode=none. It does not
predict a fold or measure an energy. The later selected return cannot reacquire.
"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

from jsonschema import Draft202012Validator

from gene_annotation_episode.communication import plain
from gene_annotation_episode.rna_structure_comparison_contracts import validate_rna_comparison_selector
from gene_annotation_episode.rna_structure_comparison_views import PROJECTION_SOURCE
import test_native_rna_structure_results_integration as original360
from test_scientific_process_prompt_delivery import ScientificWire

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('rna_one_structure_shared372',
    ROOT / 'tests/fixtures/rna_comparison_shared_372/helpers.py')
shared372 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(shared372)

FIELD = 'requested_structure'
MEMBER = 'supplied-RNA'
OPENING = ("Return the requested sequence or structure information for the parent’s single selected RNA input "
    + MEMBER + ". Include only the explicitly selected fields below.")


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def selected_structure(descriptor, fields=('original_sequence', 'dot_bracket')):
    """Use the exact existing schema and full received saved descriptor."""
    selector = shared372.b.selector(
        [{'member_id': MEMBER, 'kind': 'saved_sheet', 'saved_input': deepcopy(descriptor)}],
        [], baseline=MEMBER, scan=shared372.b.scan_request(None), projections=[{
            'projection_id': 'requested-structure', 'family': 'structures',
            'member_ids': [MEMBER], 'fields': list(fields)}])
    return validate_rna_comparison_selector(selector)


def parent_form(*, completed):
    form = shared372.comparison_form(completed=completed)
    form['properties'][FIELD] = form['properties'].pop('comparison')
    form['required'][form['required'].index('comparison')] = FIELD
    return form


def denied(*args, **kwargs):
    raise AssertionError('one retained structure return attempted new native work or acquisition')


class ControlledActionWire(ScientificWire):
    """Existing actual provider boundary with a declared test action response."""
    answer = None

    async def _rpc(self, method, params):
        result = await super()._rpc(method, params)
        if method == 'turn/start':
            for event in self.pending:
                item = event.get('params', {}).get('item', {})
                if item.get('type') == 'agentMessage':
                    item['text'] = json.dumps(self.answer, allow_nan=False)
        return result


def workflow_case(directory, monkeypatch, *, status=False):
    directory.mkdir(parents=True, exist_ok=True)
    evidence = SimpleNamespace(calls=[], guarded=False)
    old_child, old_form, old_workflow = original360.child, original360.result_form, original360.Workflow

    def form(fields=('summary', 'references', 'saved'), *, completed=True):
        return parent_form(completed=completed) if fields == (FIELD,) else old_form(fields, completed=completed)

    def child(role, assignment, scope, form):
        if role == 'results' and assignment.get('selector', {}).get('version') == 'native_rna_structure_saved_sheet_selector_v1':
            assert evidence.guarded
            assert assignment['selector']['saved_input'] == evidence.descriptor
            assignment = {'version': 'execution_results_assignment_v1',
                'handoff_ref': evidence.descriptor['handoff_ref'],
                'selector': selected_structure(evidence.descriptor)}
            form = parent_form(completed=True)
            answer = old_child(role, assignment, scope, form)
            answer['selection']['goal'] = 'Return the requested original sequence and dot-bracket for the single supplied RNA structure.'
            answer['selection']['purpose'] = 'Return only the two selected strings with their retained origin and validity.'
            evidence.assignment = deepcopy(assignment)
            evidence.selected_parent_commission = deepcopy(answer)
            return answer
        return old_child(role, assignment, scope, form)

    def guarded(fixture):
        evidence.descriptor = deepcopy(fixture.descriptor)
        evidence.original_form = deepcopy(fixture.returned)
        evidence.original_body = fixture.owner.native_rna_structure_results.read_receipt_key(
            fixture.descriptor['result_receipt_key'], fixture.store.validate_scope())
        evidence.original_receipt_path = fixture.owner.native_rna_structure_results._saved_directory(
            evidence.original_body['episode_id'], evidence.original_body['operation_key']) / 'receipt.json'
        evidence.original_receipt = evidence.original_receipt_path.read_bytes()
        evidence.original_sheet = fixture.store.get_artifact(fixture.descriptor['sheet_artifact_ref'])
        evidence.source_count = fixture.store.count('source')
        evidence.native_count = fixture.store.count('native_execution')
        evidence.original_episode_ids = [row['episode_id'] for row in fixture.store.db.execute(
            "SELECT episode_id FROM runtime_episodes WHERE run_id=? AND completion IS NOT NULL", (original360.RUN_ID,))]
        evidence.old_observations = [dict(row) for row in fixture.store.db.execute(
            'SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')
            if row['episode_id'] in evidence.original_episode_ids]
        original_run = Path(fixture.plan['identity']['execution_id']).parent
        shutil.copytree(original_run, directory / 'original-setup-run')
        (directory / 'original-receipt.json').write_bytes(evidence.original_receipt)
        (directory / 'original-sheet.json').write_bytes(evidence.original_sheet)
        shutil.rmtree(original_run)
        Path(fixture.job['operands'][0]['path']).unlink()
        monkeypatch.setattr('gene_annotation_episode.native_rna_structure_results.capture_local_rna_structure_bundle', denied)
        monkeypatch.setattr('gene_annotation_episode.native_rna_structure_local.local_rna_structure_plan', denied)
        monkeypatch.setattr(type(fixture.owner.job_progress_provider.targets), 'observe_target', denied)
        evidence.guarded = True

    def workflow(store, tools, scripted, *args, **kwargs):
        wire = ControlledActionWire(directory / 'actual-provider-wire')
        evidence.wire = wire

        class Choices:
            async def complete(self, episode_id, role, instructions, current, schema):
                answer = await scripted.complete(episode_id, role, instructions, current, schema)
                selected = current.get('execution_assignment', {})
                if selected.get('selector', {}).get('version') != 'native_rna_structure_comparison_selector_v1':
                    return answer
                if status and not evidence.calls:
                    answer = original360.provider_value(original360.selected('execution.results.status'), plain(schema))
                Draft202012Validator(plain(schema)).validate(answer)
                wire.answer = deepcopy(answer)
                evidence.calls.append({'episode_id': episode_id, 'role': role, 'instructions': instructions,
                    'context': deepcopy(current), 'schema': plain(schema), 'answer': deepcopy(answer)})
                delivered = await wire.complete(episode_id, role, instructions, current, plain(schema))
                assert delivered == answer
                return delivered

            async def release(self, episode_id):
                await scripted.release(episode_id)

        return old_workflow(store, tools, Choices(), *args, **kwargs)

    monkeypatch.setattr(original360, 'result_form', form)
    monkeypatch.setattr(original360, 'child', child)
    monkeypatch.setattr(original360, 'Workflow', workflow)
    case = original360.workflow_case(directory, prediction=False, energy=False, saved=True,
        selection=original360.selector(metrics=['pair_count']), results_fields=('saved',),
        parent_fields=(FIELD,), before_saved=guarded)
    case.evidence = evidence
    case.comparison_context = case.result_contexts[-1]
    case.body = json.loads(case.flow.journal.row('runtime_actions',
        case.comparison_context.episode_id, int(status))['result'])['result']
    case.projections = case.returned[-1][FIELD]
    case.selection = deepcopy(evidence.assignment['selector'])
    case.directory = directory
    write_json(directory / 'ONE_STRUCTURE_CASE.json', {
        'provenance': 'actual supplied-topology original360 Workflow setup; retained one-input comparison collection; controlled provider choices',
        'assignment': evidence.assignment, 'original_received_form': evidence.original_form,
        'selected_parent_commission': evidence.selected_parent_commission,
        'returned': case.returned[-1], 'forwarded': case.forwarded,
        'body': case.body, 'original_body': evidence.original_body,
        'histories': {row['episode_id']: row['controller_state'] for row in case.records},
        'controlled_provider_calls': evidence.calls,
    })
    for index, turn in enumerate(evidence.wire.turns_sent()):
        (directory / f'ACTUAL_PROVIDER_TURN_{index:03d}.txt').write_text(turn['input'][0]['text'] + '\n')
    return case
