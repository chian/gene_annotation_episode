"""Host/manual proof; retained native bytes, controlled selected service calls."""
from copy import deepcopy
import json
import os
from pathlib import Path
import pytest

from gene_annotation_episode import bvbrc_fastqutils_bundle_adapter as adapter
from gene_annotation_episode.bvbrc_appservice_custody import AppServiceCustodyError
from gene_annotation_episode.bvbrc_fastqutils_contracts import validate_requested_form
from gene_annotation_episode.communication import plain, validate_form
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.state import Store
from samstat_common import (HERE, NAMES, OUTPUTS, HASHES, EXPECTED, host, save,
    configure, action_rows, check_values, check_sheet, checkpoint, reconstruct, disable_reexecution)

@pytest.mark.parametrize('family', ['current', 'legacy'])
def test_native_report_host_returns_reconstruct_and_forgery(tmp_path, monkeypatch, family):
    case = 'host_' + family
    def no_external(*args, **kwargs):
        raise AssertionError('controlled218 host attempted live transport or subprocess')
    for target in ('socket.create_connection', 'socket.socket.connect', 'urllib.request.OpenerDirector.open', 'subprocess.Popen'):
        monkeypatch.setattr(target, no_external)
    fixture_map, native = configure(monkeypatch, family)
    save(case, 'selected_fixture', dict(fixtures=fixture_map, outputs=OUTPUTS,
        native_sha256=HASHES[family], native_byte_count=len(native),
        provider_envelope_injected=False, retained_native_producer_output=True,
        association='Controlled FastqUtils service and Workspace association; not a live service result.'))
    resume = os.environ.get('SAMSTAT_RESUME_CHECKPOINT')
    if resume:
        saved = json.loads(Path(resume).read_text())
        assert saved['selected']['adapter']['parameters'] == fixture_map['parameters']
        save(case, 'resume', dict(checkpoint=resume))
    else:
        with Store(tmp_path / 'state') as store:
            d = host.FastqDriver(store, tmp_path)
            assert list(d.saved.receipts.known(d.saved.root.episode_id)) == []
            assert store.db.execute('SELECT COUNT(*) FROM runtime_record_receipts').fetchone()[0] == 0
            d.start(documents=NAMES)
            save(case, 'frozen_selection_before_acquisition', dict(selection=d.selected,
                assignment=d.frozen_assignment, material=d.material, declarations=d.declarations,
                submitted=d.handoff, schema=d.schema, initial_known_record_refs=[]))
            d.acquire_manifest()
            assert d.api._completion(d.context) is None
            body = d.acquire_native('report')
            saved = json.loads(checkpoint(d, tmp_path, body, case).read_text())

    # Close/reopen durable state before inspecting the requested saved facts.
    attempts, patched = disable_reexecution(monkeypatch)
    save(case, 'disabled_entrypoints', patched)
    with Store(saved['state_path']) as store:
        d = reconstruct(store, saved)
        body = d.api.read_result(saved['body']['source_ref'], d.context.scope)
        assert body == saved['body']
        d.sheet = d.api.appservice.publications.read_content_source(
            body['publication']['adapter_result']['sheet_content']['source_ref'], d.context.scope)
        d.components = d.api.appservice.publications.read_content_source(
            body['publication']['adapter_result']['components_content']['source_ref'], d.context.scope)
        assert d.sheet == saved['sheet'] and d.components == saved['components']
        assert action_rows(store) == saved['actions']
        assert d.selected['adapter']['parameters'] == fixture_map['parameters']
        assert validate_requested_form(d.selected['requested_schema']) == fixture_map['requested_form']
        assert plain(d.context.assignment) == d.frozen_assignment
        pin = adapter.implementation_sha256()
        assert body['publication_inputs']['adapter_implementation_sha256'] == pin
        assert body['publication_inputs']['selector'] == d.selected
        assert body['bundle']['original_task'] == d.handoff['value']['original_task']
        assert body['bundle']['original_task']['submitted_parameters'] == fixture_map['submitted_parameters']
        calls = [call for call in saved['calls'] if call[0] == 'rpc' and call[1]['method'] == 'AppService.start_app2']
        assert len(calls) == 1 and calls[0][1]['params'] == ['FastqUtils', fixture_map['submitted_parameters'], {}]
        parse = dict(d.saved.journal.row('runtime_actions', d.parent.episode_id, 1))
        parsed = json.loads(parse['result'])
        assert json.loads(parse['action'])['tool'] == 'material.parse'
        attempt = parsed['result']['parse_attempt']
        assert (attempt['status'], attempt['code'], attempt['source_ref']) == (
            'completed', 'retained_without_sequence_projection', d.declarations['source_ref'])
        assert store.get_artifact(d.declarations['artifact_ref']) == canonical({'declarations': []}).encode()
        assert d.custody.possession(d.parent, d.declarations['source_ref']) == 'own_completed_action'
        with pytest.raises(AppServiceCustodyError, match='input_not_possessed'):
            d.custody.possession(d.parent, d.declarations['source_ref'], before=1)
        member, = body['bundle']['artifacts']
        assert member['role'] == 'report' and member['requirement_ids'] == ['selected_report']
        assert member['task_association']['task_id'] == '123'
        assert member['workspace_object']['path'] == member['task_association']['output_path'] == OUTPUTS['report'][0]
        assert member['workspace_object']['uuid'] == member['task_association']['output_uuid'] == OUTPUTS['report'][1]
        assert member['task_association']['kind'] == 'task_result_manifest'
        assert member['task_association']['pointer'] == '/output_files/0'
        assert store.get_artifact(member['raw_artifact_ref']) == native
        assert member['sha256'] == HASHES[family] and member['byte_count'] == len(native)
        assert d.custody.possession(d.context, member['source_ref']) == 'own_completed_action'
        assert d.sheet['documents'][0]['artifact']['content_binding']['source_ref'] == member['source_ref']
        numerical = check_sheet(d.sheet, d.components, family, native)
        owner_facts = check_values(body['publication']['adapter_result']['facts'], family)
        proof = d.api._completion(d.context)
        assert body['publication']['requested_form_status'] == 'satisfied'
        assert proof and d.api.verify_completion(d.context, proof)
        assert proof['assignment_sha256'] == digest(d.frozen_assignment)
        assert proof['endpoint'] == 'completed_job_outputs'
        assert proof['validation_keys'] == ['requested_service_result']
        save(case, 'native_publication_and_completion', dict(body=body, sheet=d.sheet,
            components=d.components, numerical=numerical, owner_facts=owner_facts, proof=proof))

        before = action_rows(store)
        typed, key, refs = d.admit_numeric()
        forwarded, forwarded_key, forwarded_refs = d.admit_numeric(to_grandparent=True)
        assert typed == forwarded and refs == forwarded_refs
        check_values(host.native_values(typed), family)
        values = check_values(host.native_values(forwarded), family)
        validate_form(forwarded, d.schema, lambda ref, namespace=None: d.family.resolve(d.parent, ref, namespace))
        assert set(d.family.received_report_facts(d.grandparent)) == {
            'bvbrc_fastqutils_components', 'bvbrc_fastqutils_requirements'}
        for context in (d.parent, d.grandparent):
            assert d.custody.possession(context, body['source_ref']) == 'admitted_return'
        save(case, 'typed_returns', dict(owner=owner_facts, result_to_parent=typed,
            parent_to_grandparent=forwarded, decoded=values, schema=d.schema, references=refs))
        facts_before = deepcopy(d.family.received_report_facts(d.grandparent))
        retained = canonical([body, d.sheet, d.components, typed, forwarded])
        assert d.admit_numeric() == (typed, key, refs)
        assert d.admit_numeric(to_grandparent=True) == (forwarded, forwarded_key, forwarded_refs)
        assert canonical([body, d.sheet, d.components, typed, forwarded]) == retained
        assert d.family.received_report_facts(d.grandparent) == facts_before
        assert action_rows(store) == before and not attempts and d.client.calls == []
        assert store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0
        forged = deepcopy(typed)
        forged['facts_0'][0]['value']['records'][0]['payload']['value'] = 900
        rejections = []
        for label, context in (('owning_results_provider', d.context),
            ('child_to_parent_receiver', d.parent), ('parent_to_grandparent_receiver', d.grandparent)):
            with pytest.raises(ValueError) as error:
                d.family.validate_received_report(context, forged, d.schema)
            rejections.append(dict(boundary=label, episode_id=context.episode_id, code=str(error.value)))
        assert not attempts and action_rows(store) == before
        assert d.family.received_report_facts(d.grandparent) == facts_before
        save(case, 'saved_replay_and_forgery', dict(reconstructed=True, repeated_returns=2,
            action_rows_sha256_before=digest(before), action_rows_sha256_after=digest(action_rows(store)),
            source_refs_before=refs, source_refs_after=d.admit_numeric()[2],
            forbidden_attempts=attempts, forged_value=900, rejections=rejections))
        save(case, 'selected_actions', before)
        save(case, 'controlled_calls', saved['calls'])
        summary = dict(passed=True, family=family, numerical_fractions=EXPECTED[family],
            native_sha256=HASHES[family], provider_pin=pin, selected_actions=len(before),
            completed_own_tool_actions=sum(row['result'] is not None for row in before), runtime_observations=0,
            initial_known_record_refs=[], real_material_parse=True, actual_host=True,
            native_bytes_acquired=True, typed_receivers=2, forgery_rejections=len(rejections),
            reconstructed=True, practical_completion_verified=True, method_loop_run=False,
            controlled_transport=True, live_service_run=False, native_producer_run=False,
            original_input_completeness='unknown', MAPQ255='included_in_high_bin_not_known_mapping_quality')
        save(case, 'summary', summary)
        print(json.dumps(summary, sort_keys=True), flush=True)
