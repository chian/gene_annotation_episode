"""Genuine selected LUMPY SR resource execution and shared VCF delivery.

Scripted decisions exercise the real episode owners. This contains no native
output substitution, manual receipt insertion or alternate VCF calculation.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import native_lifecycle
from gene_annotation_episode import native_lumpy_execution as native
from gene_annotation_episode import lumpy_request_binding as compact
from gene_annotation_episode import vcf_result_tools as vcf
from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_episodes import RESULTS_VERSION
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.local_file_capture_results import LUMPY_SELECTOR_VERSION
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate
from gene_annotation_episode.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

from test_macs2_peak_workflow import _action, _commission, _provider_value, HANDOFF_FORM, CAPTURE_FORM


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / 'fixtures/lumpy_sr'
PUBLICATION = ROOT / 'research/slotted_process_library/publications/2026-10-24-001'
QUESTION = ('Which structural-variant candidates does LUMPY report from these supplied split-read signals, '
    'with their native measurements and sample/reference associations? Return the selected controlled VCF groups.')
INFO = ['SVTYPE', 'SVLEN', 'END', 'SU', 'PE', 'SR', 'CIPOS', 'CIEND', 'MATEID', 'EVENT', 'SECONDARY']


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _zero(*args, **kwargs):
    return 0


def _controller(path, initial):
    """Stable engineering controller; practical completion can end earlier."""
    horizon = {'scientific_process': 5, 'launch_local': 2}.get(path[-1][0], 1)
    def estimate(history, parameters, contexts):
        return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= horizon else 1),
            parameters, dict(engineering_fixture='explicit selected native and retained-result operations'))
    return YieldController(str(path), initial, 0, estimate_with_context=estimate)


def _selection(**changes):
    value = dict(version='vcf_result_selection_v1', record_ordinals=None, sample_ordinals=None,
        info_keys=INFO, format_keys=['GT', 'SU', 'PE', 'SR'], offset=0, limit=2)
    value.update(changes)
    return value


def _assemble(store, proof, provider):
    factory = ExecutionServiceFactory.from_record(proof['factory'])
    tools = ToolRegistry(store, job_limits=deepcopy(native.POLICY))
    application = factory(store, run_id=proof['run_id'], directory=Path(proof['directory']) / 'run', tool_registry=tools)
    workflow = Workflow(store, tools, provider, Path(proof['directory']) / 'run', proof['run_id'],
        _controller, _zero, project_child_credit=_zero, episode_record_receipts=True,
        initial_known_record_refs=proof['initial_refs'],
        episode_binding_descriptors=[proof['scientific_binding'], *application.episode_binding_descriptors],
        role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider)
    return workflow, tools


class LumpyChoices:
    def __init__(self, store, proof, save):
        self.store, self.proof, self.save = store, proof, save
        self.previous, self.owner, self.handoff = {}, None, None
        self.session = object.__new__(_SessionConnection)
        self.session.scientific_prompt_states = {}
        self.result_sources = []

    async def complete(self, episode_id, role, instructions, current, schema):
        store, proof, save = self.store, self.proof, self.save
        run_id, scope = proof['run_id'], proof['scope']
        runtime, directory = proof['software']['native_runtime'], Path(proof['directory'])
        scientific_assignment, launch = proof.get('scientific_assignment'), proof['launch']
        parent_schema = proof['parent_schema']
        current = plain(current)
        row = store.db.execute('SELECT path FROM runtime_episodes WHERE run_id=? AND episode_id=?',
            (run_id, episode_id)).fetchone()
        episode_role = json.loads(row[0])[-1][0]
        turn = store.db.execute('SELECT count(*) FROM runtime_actions WHERE run_id=? AND episode_id=?',
            (run_id, episode_id)).fetchone()[0] + 1
        frame = state_frame(current, self.previous.get(episode_id))
        text, _ = self.session._presentation(episode_id, 'REASONING', instructions, frame)
        self.previous[episode_id] = deepcopy(current)
        if episode_role in ('scientific_process', 'launch', 'launch_local', 'results'):
            assert text.startswith('TASK\n') and QUESTION in text and 'STEERING' in text
            assert runtime['executable']['sha256'] not in text and str(directory / 'software') not in text
        proof['wire'].append(dict(episode_id=episode_id, role=episode_role, turn=turn, text=text))
        save()


        if 'practical_assignment' in current:
            if turn == 1:
                answer = _action('practical.job.start')
            else:
                assert turn == 2
                context = EpisodeReturnRecords(store, run_id, failure_prefix='lumpy_fixture_').context(episode_id)
                state = self.owner.state(context)
                job = state.receipts()[-1]['outcome']['facts']['requested_job']
                result = await asyncio.to_thread(native_lifecycle.wait_job,
                    native_lifecycle.NativeJobHandle(Path(job['execution_id'])))
                proof['observed_native_driver_returncode'] = result.returncode
                save()
                answer = _action('practical.job.collect')
        elif current.get('execution_assignment', {}).get('version') == compact.LAUNCH_VERSION:
            assert turn == 1
            answer = _commission('launch_local', current['execution_assignment']['requests']['here'],
                scope, HANDOFF_FORM, QUESTION)
        elif current.get('execution_assignment', {}).get('version') == RESULTS_VERSION:
            if turn > 1:
                prior = store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? '
                    'ORDER BY decision_index DESC LIMIT 1', (run_id, episode_id)).fetchone()
                outcome = json.loads(prior[0])
                assert turn == 2 and outcome.get('status') == 'invalid'
                assert outcome.get('feedback', {}).get('code') == 'invalid_resource_progress_observation'
            answer = _action('execution.results.collect')
        elif 'scientific_process' not in current:
            assert turn == 1
            answer = _commission('scientific_process', scientific_assignment, scope, parent_schema, QUESTION)
        elif turn == 1:
            answer = _commission('launch', launch, scope, HANDOFF_FORM, QUESTION)
        elif turn == 2:
            reader = PracticalReceiptInformation(store, run_id)
            self.handoff = next(ref for ref in reversed(current['child_reports'][-1]['references'])
                if reader.read(ref, scope)['receipt']['tool_name'] in ('practical.job.start', 'practical.job.collect'))
            target = self.owner.job_progress_provider.targets.read_target(self.handoff, scope)
            plan = native.read_local_lumpy_plan(target['assignment'], target['execution_id'])
            seal = native.validate_lumpy_seal(json.loads((Path(plan['attempt_directory']) / native.SEAL_FILENAME).read_text()), plan=plan)
            proof.update(native_plan=plan, native_seal=seal, phase='native_completed')
            save()
            assert seal['outcome'] == 'succeeded' and seal['returncode'] == 0
            answer = _commission('results', dict(version=RESULTS_VERSION, handoff_ref=self.handoff,
                selector=dict(version=LUMPY_SELECTOR_VERSION, output_roles=list(compact.OUTPUT_ROLES))),
                scope, CAPTURE_FORM, QUESTION)
        elif turn == 3:
            capture = deepcopy(current['child_reports'][-1])
            proof['capture_form'] = capture
            self.native_source, = [ref for ref in capture['sources']
                if store.get(ref).get('artifact_ref') == 'artifact_' + next(row['declaration']['sha256']
                    for row in proof['native_seal']['outputs'] if row['specification']['role'] == 'vcf')]
            answer = _action(vcf.TOOL, dict(mode='analyze', namespace='source', reference=self.native_source,
                max_bytes=8 * 1024**2, capture_state='complete', original_size_bytes=next(row['declaration']['size_bytes']
                    for row in proof['native_seal']['outputs'] if row['specification']['role'] == 'vcf'), selection=_selection()))
        elif turn == 4:
            operation, = list(store.db.execute('SELECT result FROM tool_operations WHERE name=? ORDER BY rowid', (vcf.TOOL,)))
            previous = json.loads(operation[0])
            self.result_sources = [previous['result']['source_ref']]
            answer = _action(vcf.TOOL, dict(mode='calculate_saved', result_ref=self.result_sources[0],
                selection=_selection(record_ordinals=[1, 0], limit=2)))
        else:
            assert turn == 5
            operations = list(store.db.execute('SELECT result FROM tool_operations WHERE name=? ORDER BY rowid', (vcf.TOOL,)))
            derived = json.loads(operations[-1][0])
            self.result_sources.append(derived['result']['source_ref'])
            answer = _action(vcf.TOOL, dict(mode='read_stored', result_ref=self.result_sources[-1]))
        answer = _provider_value(plain(answer), plain(schema))
        Draft202012Validator(plain(schema)).validate(answer)
        return answer

    async def release(self, episode_id):
        pass


def _verify_delivery(store, proof):
    run_id = proof['run_id']
    rows = list(store.db.execute('SELECT result FROM tool_operations WHERE name=? ORDER BY rowid', (vcf.TOOL,)))
    assert len(rows) == 3
    original, derived, read = [json.loads(row[0]) for row in rows]
    assert all(row['status'] in ('completed', 'partial') for row in (original, derived, read))
    assert derived['result'] == read['result'] and read['changed_record_refs'] == []
    group = [original['result'], derived['result']]
    forms = list(store.db.execute('SELECT form FROM runtime_forms WHERE run_id=? AND json_extract(form,\'$.variants\') IS NOT NULL', (run_id,)))
    assert len(forms) == 1 and json.loads(forms[0][0]) == dict(variants=group)
    native_vcf = Path(proof['native_plan']['attempt_directory']) / 'native/result.vcf'
    proof.update(passed=True, phase='closed_typed_delivery', returned=group,
        native_vcf=dict(path=str(native_vcf), sha256=_sha(native_vcf), size_bytes=native_vcf.stat().st_size),
        upstream_expected_vcf_sha256=_sha(FIXTURES / 'test_onlysplit.bam.vcf'),
        upstream_expected_byte_equality=native_vcf.read_bytes() == (FIXTURES / 'test_onlysplit.bam.vcf').read_bytes(),
        runtime_counts={name: store.db.execute('SELECT count(*) FROM ' + name + ' WHERE run_id=?', (run_id,)).fetchone()[0]
            for name in ('runtime_episodes', 'runtime_actions', 'runtime_observations', 'runtime_model_calls', 'runtime_forms')})


def test_actual_SR_resource_child_capture_shared_VCF_saved_selection_and_parent_return(tmp_path, monkeypatch):
    selected = os.environ.get('HMMER_NATIVE_ORACLE_LUMPY_RUNTIME_SELECTION')
    expected = os.environ.get('HMMER_NATIVE_ORACLE_LUMPY_RUNTIME_SELECTION_SHA256')
    if not selected or not expected:
        pytest.skip('requires the explicit real LUMPY software selection and digest')
    selection_path = Path(selected).resolve(strict=True)
    assert _sha(selection_path) == expected
    runtime = json.loads(selection_path.read_text())['native_runtime']
    provenance = json.loads((FIXTURES / 'provenance.json').read_text())
    for row in provenance['objects']:
        path = FIXTURES / row['name']
        assert _sha(path) == row['sha256'] and path.stat().st_size == row['size_bytes']
    directory = tmp_path / 'genuine_SR_workflow'
    directory.mkdir()
    proof_path = directory / 'lumpy_resource_workflow_audit.json'
    proof = dict(version='lumpy_resource_workflow_proof_v1', directory=str(directory), question=QUESTION,
        passed=False, phase='selected', external_model_rpc_calls=0, native_command_budget=1,
        software_selection=dict(path=str(selection_path), sha256=expected), provenance=provenance,
        wire=[], native_plan=None, native_seal=None, capture_form=None, returned=None)
    def save():
        proof_path.write_text(json.dumps(proof, indent=2, allow_nan=False) + '\n')
    save()
    store = None
    def no_http(*args, **kwargs):
        raise AssertionError('local LUMPY resource proof attempted network acquisition')
    monkeypatch.setattr('socket.create_connection', no_http)
    try:
        software = native.freeze_lumpy_software_binding(module_root=str(ROOT),
            snapshot_directory=str(directory / 'software'), native_runtime=runtime)
        proof['software'] = software
        proof['phase'] = 'software_frozen'
        save()
        store = Store(directory / 'store')
        store.create_problem(raw_sequence='ACGTACGT', molecule='dna')
        scope = store.validate_scope()
        bam = FIXTURES / 'test.filtered_split.bam'
        supplied = store.register_material(input_path=bam, name='official_LUMPY_SR_BAM', use='evidence')
        input_ref = store.get(supplied['source_ref'])['artifact_ref']
        request = dict(version=native.REQUEST_VERSION, operation=native.OPERATION, mode=native.MODE,
            run_key='official_split_read_candidates', parameters=dict(minimum_sample_weight=4,
                trim_threshold='0', probability_output=True), signals=[dict(signal_key='supplied_SR',
                kind='split_read', output_sample_label='test', declared_sample_id=None, reference_id=None,
                bam=dict(artifact_ref=input_ref, format='bam'), read_group=None,
                parameters=dict(back_distance=10, min_non_overlap=25, weight=1,
                    min_mapping_threshold=20, min_clip=20))])
        assignment = dict(version=compact.ASSIGNMENT_VERSION, resource_id='here', resource_kind='local',
            binding_ordinal_0based=0, endpoint='completed_job_outputs', request=request,
            progress_requirements=[dict(key='calls', credit=3,
                predicate=dict(kind='requested_job_outputs', output_roles=['vcf', 'seal']))],
            completion_keys=['calls'], constraints=dict(allocation=deepcopy(native.POLICY)))
        launch = dict(version=compact.LAUNCH_VERSION, requests=dict(here=assignment),
            constraints=dict(allowed_resource_ids=['here'], allowed_kinds=['local'], allocation=deepcopy(native.POLICY)))
        workspace = directory / 'workspace'
        workspace.mkdir()
        factory = ExecutionServiceFactory(dict(here=dict(kind='local', workspace=str(workspace),
            policy=deepcopy(native.POLICY), native_lumpy=[dict(operation=native.OPERATION,
                mode=native.MODE, software=software)])), {}, 3, 2, 1, log_window_bytes=128)
        tools = ToolRegistry(store, job_limits=deepcopy(native.POLICY))
        run_id = 'genuine-LUMPY-SR-resource'
        application = factory(store, run_id=run_id, directory=directory / 'run', tool_registry=tools)
        scientific = prepare_scientific_binding(run_directory=directory / 'run', source_directory=PUBLICATION,
            tool_catalog=tools.catalog(), resource_catalogs=application.resource_tool_catalogs,
            child_roles=['scientific_process', 'launch', 'results'])
        library = ScientificProcessLibrary(directory / 'run/scientific-process-library')
        scientific_assignment = dict(selection=dict(version='scientific_process_selection_v3',
            evidence_axis=library.reference('A103'), thought_pattern=library.reference('P14'),
            child_tool_info=[dict(name=native.OPERATION, resources='local'), dict(name=vcf.TOOL, resources='local')]),
            evidence_refs=scope['subject_refs'], constraints=dict(no_external_acquisition=True),
            context=dict(supplied_lumpy_request=request, reference_build=None, biological_sample_identity=None,
                target_locus=None, interpretation_limit='Retain candidate calls as possible genomic-organization evidence. '
                    'Unknown target-locus and assembly associations do not establish affected genes or function.'))
        parent_schema = dict(type='object', additionalProperties=False, required=['variants'],
            properties=dict(variants=deepcopy(vcf.vcf_result_fact_sources()[vcf.FACT_SOURCE]['report_schema'])))
        proof.update(factory=factory.as_record(), run_id=run_id, scope=scope, initial_refs=[input_ref],
            scientific_binding=scientific, parent_schema=parent_schema, scientific_assignment=scientific_assignment, launch=launch, phase='configured')
        save()


        provider = LumpyChoices(store, proof, save)
        workflow, tools = _assemble(store, proof, provider)
        provider.owner = workflow.episode_bindings.for_role('results')
        root = workflow.build('annotation', 'root', QUESTION, scope)
        completed = asyncio.run(root.run_async(workflow.context))
        assert plain(asyncio.run(root.build_result(completed)).as_record()) == dict(credit=0, pending_handles=[])
        _verify_delivery(store, proof)
    except BaseException as error:
        proof['failure'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        if store is not None:
            proof['store_directory'] = str(store.path)
            store.close()
        save()


def test_resume_original_SR_workflow_after_observation_repair(tmp_path, monkeypatch):
    selected = os.environ.get('HMMER_NATIVE_ORACLE_LUMPY_RESOURCE_PREFIX')
    expected = os.environ.get('HMMER_NATIVE_ORACLE_LUMPY_RESOURCE_PREFIX_SHA256')
    if not selected or not expected:
        pytest.skip('requires the explicitly selected original completed-native Workflow prefix')
    original_path = Path(selected).resolve(strict=True)
    assert _sha(original_path) == expected
    proof = json.loads(original_path.read_text())
    assert proof['version'] == 'lumpy_resource_workflow_proof_v1' and proof['question'] == QUESTION
    assert proof['phase'] == 'native_completed' and proof['passed'] is False
    assert proof['native_seal']['outcome'] == 'succeeded' and proof['native_seal']['returncode'] == 0
    proof['prior_integration_attempt'] = dict(path=str(original_path), sha256=expected,
        failure=proof.pop('failure', None))
    proof.update(passed=False, phase='resuming_original_scope', new_native_execution_allowed=False)
    output = tmp_path / 'lumpy_resource_workflow_resumed_audit.json'
    def save():
        output.write_text(json.dumps(proof, indent=2, allow_nan=False) + '\n')
    def forbidden(*args, **kwargs):
        raise AssertionError('retained Workflow continuation attempted new native execution or network acquisition')
    attempt = Path(proof['native_plan']['attempt_directory'])
    original_native_files = {str(path): _sha(path) for path in attempt.rglob('*') if path.is_file()}
    store = None
    save()
    try:
        for name in ('prepare_job', 'start_prepared', 'resume_start'):
            monkeypatch.setattr(native_lifecycle, name, forbidden)
        for name in ('run_lumpy', 'prepare_local_lumpy', 'freeze_lumpy_software_binding'):
            monkeypatch.setattr(native, name, forbidden)
        monkeypatch.setattr('socket.create_connection', forbidden)
        store = Store(proof['store_directory'])
        preserved = [tuple(row) for row in store.db.execute('SELECT episode_id,decision_index,action,result,credit,timing '
            'FROM runtime_actions WHERE run_id=? AND result IS NOT NULL ORDER BY rowid', (proof['run_id'],))]
        root_action = json.loads(store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? '
            'ORDER BY rowid LIMIT 1', (proof['run_id'],)).fetchone()[0])
        assert root_action['role'] == 'scientific_process' and root_action['scope'] == proof['scope']
        assert root_action['goal'] == QUESTION
        proof['scientific_assignment'] = root_action['assignment']
        provider = LumpyChoices(store, proof, save)
        workflow, _ = _assemble(store, proof, provider)
        provider.owner = workflow.episode_bindings.for_role('results')
        root = workflow.build('annotation', 'root', QUESTION, proof['scope'])
        completed = asyncio.run(root.run_async(workflow.context))
        assert plain(asyncio.run(root.build_result(completed)).as_record()) == dict(credit=0, pending_handles=[])
        _verify_delivery(store, proof)
        for old in preserved:
            current = store.db.execute('SELECT episode_id,decision_index,action,result,credit,timing '
                'FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?',
                (proof['run_id'], old[0], old[1])).fetchone()
            assert tuple(current) == old
        assert original_native_files == {str(path): _sha(path) for path in attempt.rglob('*') if path.is_file()}
        assert _sha(original_path) == expected
        proof.update(original_completed_actions_unchanged=True, original_native_files_unchanged=True,
            original_failed_prefix_unchanged=True, new_native_execution_performed=False)
    except BaseException as error:
        proof.update(passed=False, failure=dict(type=type(error).__name__, message=str(error)))
        raise
    finally:
        if store is not None:
            store.close()
        save()
