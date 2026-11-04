"""Complete corrected checks from the terminal run 002 state without execution."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from method_loop.identities import EpisodeRef

import test_bvbrc_fastqutils_episode_flow as host_fixture
import test_native_cutadapt_host as checks
from gene_annotation_episode.api_bvbrc_appservice import BVBRCAppServiceService
from gene_annotation_episode.api_service_execution import APIServiceExecution
from gene_annotation_episode.communication import plain, validate_form
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


def database_rows(store):
    tables = [row[0] for row in store.db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {name: sorted((dict(row) for row in store.db.execute('SELECT * FROM "' + name + '"')),
                         key=canonical) for name in tables}


def test_saved_original_host_and_admissions_complete_remaining_checks(monkeypatch):
    run = Path(os.environ['CUTADAPT_SAVED_RUN'])
    original = checks.HERE / 'host_run_002'
    restored = run / 'restored_host'
    expected_body = json.loads((original / 'evidence/final_publication.json').read_text())
    expected_sheet = json.loads((original / 'evidence/sheet.json').read_text())
    expected_components = json.loads((original / 'evidence/components.json').read_text())
    origin = expected_body['publication']['origin']
    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append(True)
        raise AssertionError('Saved-evidence continuation attempted new selected work or transport')

    # Prevent selected actions before the production host is reconstructed.
    for target, name in ((BVBRCAppServiceService, 'invoke'), (APIServiceExecution, 'execute'),
                         (ToolRegistry, 'execute')):
        monkeypatch.setattr(target, name, forbidden)
    for name in ('socket.create_connection', 'socket.socket.connect',
                 'urllib.request.OpenerDirector.open', 'subprocess.Popen'):
        monkeypatch.setattr(name, forbidden)
    with Store(restored / 'state') as store:
        before = database_rows(store)
        d = host_fixture.FastqDriver.__new__(host_fixture.FastqDriver)
        d.store, d.config = store, host_fixture.configured()
        d.family = ExecutionEpisodes(None, store=store, directory=restored, run_id=origin['run_id'],
            resources={'selected-api': d.config}, initial_information={},
            tool_registry=SimpleNamespace(store=store, clients={}), handoff_unit=2, acquired_record_unit=3,
            log_window_bytes=1024, log_roles=('stdout', 'stderr'))
        d.api = d.family.api_execution
        d.service = d.api.services['selected-api']
        d.client = d.service.client
        d.records, d.custody = d.api.appservice.records, d.api.appservice.custody
        d.context = d.custody.context(origin['episode_id'])
        d.parent = d.custody.context(EpisodeRef(origin['run_id'], d.context.path[:-1]).episode_id)
        d.grandparent = d.custody.context(EpisodeRef(origin['run_id'], d.parent.path[:-1]).episode_id)
        d.schema = plain(d.context.request)['report_contract']['measurements']['schema']
        d.saved = host_fixture.SavedRecords.__new__(host_fixture.SavedRecords)
        d.saved.store, d.saved.run_id = store, origin['run_id']
        d.saved.journal = Journal(store, origin['run_id'])
        d.saved.receipts = EpisodeReceipts(store, origin['run_id'])
        d.saved.root = d.parent
        science_attempts, disabled = checks.disable_reexecution(monkeypatch, d)
        assert checks.adapter.implementation_sha256() == checks.PIN
        assert database_rows(store) == before
        original_typed = json.loads(d.saved.journal.row('runtime_forms', d.context.episode_id)['form'])
        original_forwarded = json.loads(d.saved.journal.row('runtime_forms', d.parent.episode_id)['form'])
        assert original_typed == original_forwarded
        original_attempts = [dict(row) for row in store.db.execute(
            'SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id IN (?,?) '
            'ORDER BY parent_episode_id,decision_index',
            (origin['run_id'], d.parent.episode_id, d.grandparent.episode_id))]
        assert all(row['failure'] is None for row in original_attempts)
        assert len([row for row in original_attempts if row['child_episode_id'] in {
            d.context.episode_id, d.parent.episode_id}]) == 2
        checks.save('original_saved_admissions', dict(results_form=original_typed,
            scientific_parent_form=original_forwarded, attempts=original_attempts,
            source_run_terminal_exit_code=1, source_run_expected_failure='fixture-specific diagnostic assertion'))
        values = checks.assert_values(original_typed)
        checks.assert_values(original_forwarded)
        validate_form(original_forwarded, d.schema,
            lambda ref, namespace=None: d.family.resolve(d.parent, ref, namespace))
        body = d.api.read_result(expected_body['source_ref'], d.context.scope)
        assert body == expected_body
        saved = body['publication']['adapter_result']
        d.sheet = d.api.appservice.publications.read_content_source(saved['sheet_content']['source_ref'], d.context.scope)
        d.components = d.api.appservice.publications.read_content_source(saved['components_content']['source_ref'], d.context.scope)
        assert d.sheet == expected_sheet and d.components == expected_components
        assert all(row['observed_state'] == 'unknown' for row in d.sheet['stages'])
        assert [row['requested_token'] for row in d.sheet['stages']] == ['TRIM']
        assert all(edge['task_stage_ref'] is None and edge['scope'] == 'artifact_local'
                   for edge in d.sheet['native_lineage'])
        assert body['publication']['requested_form_status'] == 'satisfied'
        proof = d.api._completion(d.context)
        assert proof == body['publication']['completion_proof'] and d.api.verify_completion(d.context, proof)
        for member in body['bundle']['artifacts']:
            assert store.get_artifact(member['raw_artifact_ref']) == (checks.NATIVE / checks.FILES[member['role']]).read_bytes()
            assert member['task_association']['task_id'] == '123'
            assert member['workspace_object']['path'] == member['task_association']['output_path']
            assert member['workspace_object']['uuid'] == member['task_association']['output_uuid']
            assert member['requirement_ids'] == ['selected_' + member['role']]
        checks.save('validated_saved_publication', body)
        checks.save('validated_saved_sheet', d.sheet)
        checks.save('validated_saved_components', d.components)
        checks.save('corrected_requirement_check', dict(
            typed_requirements=values['requirements'], stages=d.sheet['stages'],
            measurement_values=checks.EXPECTED_MEASUREMENTS, component_value=28 / 58,
            correction='Removed the older metadata-rich fixture diagnostic expectation only.'))
        actions_before = checks.action_rows(store)
        facts_before = deepcopy(d.family.received_report_facts(d.grandparent))
        typed, key, refs = d.admit_numeric()
        forwarded, forwarded_key, forwarded_refs = d.admit_numeric(to_grandparent=True)
        assert typed == original_typed and forwarded == original_forwarded and refs == forwarded_refs
        checks.assert_values(typed)
        checks.assert_values(forwarded)
        assert set(d.family.received_report_facts(d.grandparent)) == {
            'bvbrc_fastqutils_measurements', 'bvbrc_fastqutils_components', 'bvbrc_fastqutils_requirements'}
        assert d.family.received_form_references(d.parent, typed, d.schema, key) == refs
        assert d.family.received_form_references(d.grandparent, forwarded, d.schema, forwarded_key) == forwarded_refs
        assert d.family.received_report_facts(d.grandparent) == facts_before
        for context in (d.parent, d.grandparent):
            assert d.custody.possession(context, body['source_ref']) == 'admitted_return'
        assert checks.action_rows(store) == actions_before
        assert store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0
        assert not attempts and not science_attempts
        checks.save('typed_returns', dict(schema=d.schema, result_to_parent=typed, parent_to_grandparent=forwarded,
            parent_references=refs, grandparent_references=forwarded_refs, decoded=values))
        forged = deepcopy(typed)
        forged['facts_0'][0]['value']['records'][0]['payload']['value'] = 900
        rejections = []
        for context in (d.context, d.parent, d.grandparent):
            with pytest.raises(ValueError) as error:
                d.family.validate_received_report(context, forged, d.schema)
            rejections.append(dict(role=context.role, episode_id=context.episode_id, code=str(error.value)))
        assert d.family.received_report_facts(d.grandparent) == facts_before
        assert d.api.read_result(body['source_ref'], d.context.scope) == expected_body
        assert database_rows(store) == before
        assert not attempts and not science_attempts
        checks.save('saved_replay_and_forgery', dict(disabled_callables=disabled,
            forbidden_attempts=attempts + science_attempts, rejections=rejections,
            selected_actions_before=len(actions_before), selected_actions_after=len(checks.action_rows(store)),
            original_rows_preserved=True, source_references_before=refs, source_references_after=forwarded_refs,
            practical_completion_proof=proof, transport_and_selected_execution_disabled_before_reconstruction=True))
        checks.save('selected_actions', actions_before)
        modules = []
        for name, module in sorted(sys.modules.items()):
            path = getattr(module, '__file__', None)
            if path is None or not Path(path).is_file():
                continue
            path = Path(path).resolve()
            if name.split('.', 1)[0] in ('gene_annotation_episode', 'method_loop'):
                assert path.is_relative_to(checks.HERE / 'candidate'), (name, path)
            modules.append(dict(module=name, path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        checks.save('actual_import_origins', modules)
        summary = dict(passed=True, verification_kind='saved_evidence_continuation',
            original_full_path_run='host_run_002', original_full_path_terminal_exit_code=1,
            original_full_path_qualified_failure='New fixture-specific diagnostic expectation after both successful typed admissions.',
            provider_pin=checks.PIN, requested_fields=list(checks.EXPECTED_NAMES),
            measurement_values=checks.EXPECTED_MEASUREMENTS, cutadapt_retention=28 / 58,
            cutadapt_numerator=28, cutadapt_denominator=58,
            intermediate_cutadapt_population={'reads': 4, 'bases': 28},
            final_fastq_population={'reads': 3, 'bases': 24},
            first_artifact_completes=False, both_artifacts_complete=True,
            typed_boundary_count=2, saved_replay_preserves_sources_and_values=True,
            forged_value_rejection_count=len(rejections), forbidden_call_attempts=0,
            selected_action_count=len(actions_before), additional_selected_actions=0, runtime_observation_count=0,
            all_original_database_rows_preserved=True, initial_known_record_refs=[],
            material_custody='real_selected_material.parse_in_original_run_002',
            actual_host_objects=True, controlled_task_and_transport=True,
            actual_native_bytes_from_prior_local_producer=True, native_producers_executed=0,
            method_loop_run=False, configured_model_run=False, live_bvbrc_run=False,
            whole_tool_complete=False, production_changes=False)
        checks.save('verified_summary', summary)
        print(json.dumps(summary, sort_keys=True))
