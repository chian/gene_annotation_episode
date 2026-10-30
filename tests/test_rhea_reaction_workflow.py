"""Opt-in Workflow custody proof using the unchanged authentic Rhea210 response.

Decisions and the numerical stopping fixture are scripted. The acquisition port
replays retained native bytes, request, retrieval time and transport; this case
does not make a fresh HTTP request or establish a control protein's function.
"""
import asyncio
from copy import deepcopy
import hashlib
from importlib import import_module
import json
import os
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from method_loop.archive import iter_json

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.communication import plain, validate_closed_schema
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.runtime import FACT_MEANINGS, FACT_SOURCES, Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


G = import_module('verification.tool_graders_expression_nmf_episode_path_2026-10-27_490.fixture_helpers')
ROOT = Path(__file__).resolve().parents[1]
PUBLICATION = ROOT / 'research/slotted_process_library/publications/2026-10-24-001'
CAPTURE_SHA = 'a8f987d37abf10904d30b235eaf2cee8481307b8e4ea1105f0dbfabac484e641'
BODY_SHA = 'e6e0533ec0df9f0d7b9920cdc64bb3efb30038ab4c21bd4b7b85ce835c14a0df'
RUN_ID = 'retained-rhea-reaction-workflow'
QUALIFICATION = ('Scripted ordinary nested scientific Workflow and automatic typed record custody, '
    'using unchanged authentic Rhea210 native bytes and original request/time/transport. '
    'No fresh HTTP request, autonomous scientific choice, new assay, target annotation, model edit or FBA solve.')


def _controller(path, initial):
    # This engineering fixture exercises one lookup and a parent-selected read.
    # It does not install a production action limit or scientific stopping rule.
    horizon = 2 if len(path) == 2 else 1
    def estimate(raw, parameters, contexts):
        return YieldEstimate(len(raw), NumericBand.exact(0 if len(raw) >= horizon else 1),
            parameters, {'fixture': 'retained_rhea_typed_custody_only'})
    return YieldController(str(path), initial, 0, YieldParameters(100, 50), estimate_with_context=estimate)


@pytest.mark.skipif(not os.environ.get('HMMER_NATIVE_ORACLE_RHEA_WORKFLOW_CAPTURE'),
    reason='requires explicit authentic retained210 capture within bounded529')
def test_retained_native_rhea_reaction_returns_mapping_through_scientific_child(tmp_path, monkeypatch):
    assert os.environ.get('HMMER529_ATTEMPT'), 'requires the selected bounded529 runtime'
    capture_path = Path(os.environ['HMMER_NATIVE_ORACLE_RHEA_WORKFLOW_CAPTURE'])
    assert capture_path.is_absolute()
    capture_raw = capture_path.read_bytes()
    assert hashlib.sha256(capture_raw).hexdigest() == CAPTURE_SHA
    capture = json.loads(capture_raw)
    assert capture['schema'] == 'rhea_live_reaction_acquisition_v1' and capture['replay_verified']
    assert capture['request'] == {'operation': 'public.rhea.reaction',
        'arguments': {'accession': 'RHEA:11740'}}
    original_source = capture['source_record']
    metadata = capture['request_metadata']
    body_path = Path(capture['native_body']['path'])
    body = body_path.read_bytes()
    assert len(body) == capture['native_body']['size_bytes'] == 1010
    assert hashlib.sha256(body).hexdigest() == capture['native_body']['sha256'] == BODY_SHA
    assert original_source['artifact_ref'] == capture['native_body']['artifact_ref'] == 'artifact_' + BODY_SHA
    assert metadata['request'] == {'format': 'json', 'limit': 1, 'query': 'RHEA:11740'}
    assert metadata['transport']['response']['status'] == 200
    assert metadata['transport']['representation'] == 'http_entity_bytes_via_installed_client'
    assert metadata['transport']['script_sha256'] == capture['selected_client']['sha256']
    expected = {row['id']: row for row in [original_source, *capture['reaction_records'],
        *capture['reaction_references'], *capture['chemical_references']]}
    mapping_refs = capture['outcome']['record_refs']
    assert len(mapping_refs) == len(expected) == 8 and set(mapping_refs) == set(expected)

    class RetainedNativeRhea:
        def __init__(self):
            self.calls = []

        def rhea_reaction(self, accession):
            assert accession == 'RHEA:11740'
            self.calls.append({'operation': 'public.rhea.reaction', 'arguments': {'accession': accession}})
            return SourceSnapshot('rhea', original_source['uri'], deepcopy(metadata['request']),
                original_source['retrieved_at'], body, 'application/json', deepcopy(metadata['transport']))

    client = RetainedNativeRhea()
    directory = tmp_path / 'retained-rhea-workflow'
    directory.mkdir()
    store_path = directory / 'state'
    with Store(store_path) as store:
        problem = store.create_problem(raw_sequence='MKWAA', molecule='protein')
        scope = store.validate_scope()
        tools = ToolRegistry(store, clients=client)
        binding = prepare_scientific_binding(run_directory=directory / 'run', source_directory=PUBLICATION,
            tool_catalog=tools.catalog(), child_roles=('scientific_process',))
        library = ScientificProcessLibrary(directory / 'run/scientific-process-library')
        axis, pattern = library.reference('A110'), library.reference('P10')
        assert library.resolve(axis)['name'] == 'Biochemical feasibility and chemical/resource accounting'
        assert library.resolve(pattern)['name'] == 'Account for the coupled chemical system'
        assert 'committed_record_refs' in FACT_SOURCES
        assert FACT_MEANINGS['committed_record_refs'] == \
            'Semantic records returned by completed own work and completed child investigations.'
        form = validate_closed_schema({'type': 'object', 'additionalProperties': False,
            'required': ['reaction_mapping_refs'], 'properties': {'reaction_mapping_refs': {
                'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference'},
                'x-source': 'committed_record_refs'}}})

        def assignment(owner, selected):
            return {'selection': {'version': 'scientific_process_selection_v3', 'evidence_axis': axis,
                'thought_pattern': pattern, 'child_tool_info': selected},
                'evidence_refs': scope['subject_refs'], 'constraints': {}, 'context': {
                    'fixture_owner': owner, 'acquisition_qualification': QUALIFICATION,
                    'hypothetical_reaction_question': 'What source reaction correspondence could support or '
                        'challenge glutathione oxidation coupled to NADP+ reduction?',
                    'control_material_interpretation': 'Engineering scope only; no correspondence of MKWAA '
                        'to this candidate reaction is asserted.'}}

        parent_assignment = assignment('mapping_parent', [{'name': 'state.query', 'resources': 'local'}])
        child_assignment = assignment('mapping_lookup', [
            {'name': name, 'resources': resource} for name, resource in (
                ('public.rhea.search', 'api'), ('public.rhea.reaction', 'api'),
                ('state.query', 'local'), ('source.read', 'local'))])

        class Choices:
            def __init__(self):
                self.calls, self.turns, self.episodes = [], {}, {}
                self.returned = None

            async def complete(self, episode_id, role, instructions, current, schema):
                assert not current.get('feedback'), current.get('feedback')
                self.turns[episode_id] = self.turns.get(episode_id, 0) + 1
                turn = self.turns[episode_id]
                scientific = current.get('scientific_process')
                owner = 'annotation' if scientific is None else scientific['assignment']['context']['fixture_owner']
                self.episodes[owner] = episode_id
                self.calls.append({'episode_id': episode_id, 'owner': owner,
                    'instructions': instructions, 'context': deepcopy(plain(current))})
                if owner == 'annotation':
                    assert turn == 1
                    answer = G.commission('scientific_process', parent_assignment, scope, form,
                        objective='Investigate the supplied hypothetical reaction correspondence, preserve the '
                            'source chemical account and retain the requested actual mapping records.')
                elif owner == 'mapping_parent' and turn == 1:
                    assert not set(mapping_refs).intersection(flow.receipts.known(episode_id))
                    answer = G.commission('scientific_process', child_assignment, scope, form,
                        objective='Investigate source reaction correspondence for the hypothetical glutathione/'
                            'NADP+ conversion; preserve species, stoichiometry, cofactors and unresolved '
                            'direction without assigning the control protein or inferring physiological flux.')
                elif owner == 'mapping_lookup':
                    assert turn == 1 and not store.list('reaction_record')
                    tool_info = {row['name']: row for row in scientific['child_tool_info']}
                    assert tool_info['public.rhea.reaction']['resources'] == 'api'
                    assert tool_info['public.rhea.reaction']['description'] and tool_info['public.rhea.reaction']['instructions']
                    assert 'public.rhea.reaction' in {row['name'] for row in current['tools']}
                    answer = G.action('public.rhea.reaction', {'accession': 'RHEA:11740'})
                else:
                    assert owner == 'mapping_parent' and turn == 2
                    self.returned = deepcopy(plain(current['child_reports'][-1]))
                    assert self.returned == {'reaction_mapping_refs': mapping_refs}
                    assert set(mapping_refs) <= set(flow.receipts.known(episode_id))
                    # The records exist in shared storage, but annotation has
                    # not yet received this parent's requested typed return.
                    assert not set(mapping_refs).intersection(flow.receipts.known(self.episodes['annotation']))
                    answer = G.action('state.query', {'refs': self.returned['reaction_mapping_refs']})
                if answer['selection']['kind'] == 'episode_child':
                    answer['selection']['purpose'] = ('Return the actual retained source, reaction and chemical '
                        'record references for later inspection of the hypothetical reaction correspondence; '
                        'the references establish custody rather than target activity or measured flux.')
                assert answer['report_update'] == {}
                answer = G.provider_value(plain(answer), plain(schema))
                Draft202012Validator(plain(schema)).validate(answer)
                return answer

            async def release(self, episode_id):
                pass

        provider = Choices()
        flow = Workflow(store, tools, provider, directory / 'run', RUN_ID,
            controller_factory=_controller, project_credit=lambda *_args, **_kwargs: 0,
            annotation_child_roles=('scientific_process',), episode_record_receipts=True,
            initial_known_record_refs=[], episode_binding_descriptors=(binding,))

        async def run():
            root = flow.build('annotation', 'root', 'Retain source reaction mapping for the supplied '
                'hypothetical chemical account without inferring target function', scope)
            record = await root.run_async(flow.context)
            await root.build_result(record)
            return record

        record = asyncio.run(run())
        archive = json.loads(''.join(iter_json(record.as_record())))
        assert len(provider.calls) == 4 and provider.turns == {
            provider.episodes['annotation']: 1, provider.episodes['mapping_parent']: 2,
            provider.episodes['mapping_lookup']: 1}
        assert client.calls == [capture['request']]
        returns = EpisodeReturnRecords(store, RUN_ID, failure_prefix='rhea_workflow_')
        root_context = returns.context(record.episode_id)
        parent_context, returned_parent, parent_schema = returns._attempt(root_context, 0)
        child_context, returned_child, child_schema = returns._attempt(parent_context, 0)
        assert parent_context.episode_id == provider.episodes['mapping_parent']
        assert child_context.episode_id == provider.episodes['mapping_lookup']
        assert parent_schema == child_schema == form
        assert returned_parent == returned_child == provider.returned == {'reaction_mapping_refs': mapping_refs}
        for context, count, kind in ((root_context, 1, 'child_form'),
                (parent_context, 2, 'child_form'), (child_context, 1, 'own_action')):
            assert set(mapping_refs) <= set(flow.receipts.known(context.episode_id))
            receipts = list(store.db.execute('SELECT record_ref,receipt_kind,source_index FROM '
                'runtime_record_receipts WHERE run_id=? AND episode_id=? AND record_ref IN '
                '(SELECT value FROM json_each(?))', (RUN_ID, context.episode_id, json.dumps(mapping_refs))))
            assert len(receipts) == len(mapping_refs)
            assert all(row['receipt_kind'] == kind and row['source_index'] == 0 for row in receipts)
            observations = list(store.db.execute('SELECT observation FROM runtime_observations '
                'WHERE run_id=? AND episode_id=?', (RUN_ID, context.episode_id)))
            assert len(observations) == count
            assert all(json.loads(row['observation'])['credit']['credit'] == 0 for row in observations)
        for context in (parent_context, child_context):
            saved = flow.journal.row('runtime_forms', context.episode_id)
            assert json.loads(saved['facts'])['committed_record_refs'] == mapping_refs
            assert json.loads(saved['facts'])['interpretations'] == {}
            assert json.loads(saved['form']) == returned_parent
        lookup_row = flow.journal.row('runtime_actions', child_context.episode_id, 0)
        frozen_lookup = json.loads(lookup_row['result'])
        assert frozen_lookup['status'] == 'completed' and frozen_lookup['record_refs'] == mapping_refs
        read_row = flow.journal.row('runtime_actions', parent_context.episode_id, 1)
        assert json.loads(read_row['action']) == {'kind': 'tool', 'tool': 'state.query',
            'arguments': {'refs': mapping_refs}}
        read = json.loads(read_row['result'])
        assert read['status'] == 'completed'
        assert {row['id']: row for row in read['result']['records']} == expected
        source = store.get(original_source['id'])
        assert source == original_source and store.get_artifact(source['artifact_ref']) == body
        assert json.loads(store.get_artifact(source['request_ref'])) == metadata
        reaction, = capture['reaction_records']
        reference, = capture['reaction_references']
        assert store.get(reference['id'])['native_record_ref'] == reaction['id']
        assert reaction['source_direction'] == 'undefined' and reaction['source_arrow'] == '='
        for participant in store.get(reaction['id'])['participants']:
            chemical = store.get(participant['chemical_ref'])
            assert chemical['source_ref'] == reaction['source_ref'] == source['id']
            assert chemical['accession'] == participant['source_accession']
            assert participant['source_location'] == ''
        assert store.problem() == problem
        assert store.count('observation') == store.count('assessment') == store.count('annotation') == 0
        lookup_key = f'{RUN_ID}:{child_context.episode_id}:0'
        known_before = {name: list(flow.receipts.known(episode)) for name, episode in provider.episodes.items()}
        verification = {
            'schema': 'retained_rhea_reaction_workflow_verification_v1', 'qualification': QUALIFICATION,
            'original_capture': {'path': str(capture_path), 'sha256': CAPTURE_SHA},
            'native_body': {'path': str(body_path), 'sha256': BODY_SHA, 'size_bytes': len(body)},
            'original_request_metadata': metadata, 'original_retrieved_at': source['retrieved_at'],
            'evidence_axis': {'reference': axis, 'name': library.resolve(axis)['name']},
            'thought_pattern': {'reference': pattern, 'name': library.resolve(pattern)['name']},
            'episodes': provider.episodes, 'lookup_operation_key': lookup_key,
            'automatic_return': returned_parent, 'parent_selected_read': read,
            'known_record_refs': known_before, 'model_calls': provider.calls, 'archive': archive,
            'store_path': str(store_path), 'replay_verified': False}
        report_path = Path(os.environ['HMMER529_ATTEMPT']) / 'rhea-reaction-workflow.json'
        G.write(report_path, verification)

    def forbidden(*args, **kwargs):
        raise AssertionError('closed retained native operation attempted another acquisition')
    monkeypatch.setattr(client, 'rhea_reaction', forbidden)
    with Store(store_path) as reopened:
        replay = ToolRegistry(reopened, clients=client).execute('public.rhea.reaction',
            {'accession': 'RHEA:11740'}, scope=scope, operation_key=lookup_key)
        # Workflow adds pending metadata after the registry's own saved outcome.
        assert replay == {key: value for key, value in frozen_lookup.items() if key != 'pending_work_after_action'}
        assert {reference: reopened.get(reference) for reference in mapping_refs} == expected
        assert reopened.get_artifact(original_source['artifact_ref']) == body
        receipts = EpisodeReceipts(reopened, RUN_ID)
        assert {name: list(receipts.known(episode)) for name, episode in provider.episodes.items()} == known_before
        assert reopened.count('observation') == reopened.count('assessment') == reopened.count('annotation') == 0
    verification['replay_verified'] = True
    G.write(report_path, verification)
