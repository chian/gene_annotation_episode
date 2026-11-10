"""Real native algorithms in a scripted two-wing root wiring mock-up.

The decisions and finite horizons are explicit fixtures. No independent model
or biological-function conclusion is claimed. Native custody, grading, shared
parent deliveries and root credit use the actual application.
"""
from collections import defaultdict
from copy import deepcopy
import asyncio
import json
from pathlib import Path

from gene_annotation_episode.a101_credit import A101SequenceCredit
from gene_annotation_episode.a101_investigation import A101Subtree, initial_report as sequence_report
from gene_annotation_episode.a102_investigation import A102Subtree, initial_report as structure_report
from gene_annotation_episode.a102_publication import received_grade
from gene_annotation_episode.a102_tools import A102ToolRegistry
from gene_annotation_episode.assembled_service_setup import bind_assembled_services
from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE
from gene_annotation_episode.decision_context import PROTOCOL, apply_state_frame
from gene_annotation_episode.domain import obj
from gene_annotation_episode.evidence_root import NativeEvidenceRootCredit, create_evidence_root_workflow
from gene_annotation_episode.homology_episodes import HomologyEpisodes
from gene_annotation_episode.homology_jobs import HomologyJobs, FileAsset, digest
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.numerical import YieldController, YieldEstimate, NumericBand
from gene_annotation_episode.resource_estimation import ResourceToolEstimator
from a102_native_fixture import coordinate_source


ROOT = Path(__file__).resolve().parents[1]
PUBLICATION = ROOT/'research/slotted_process_library/publications/2026-10-24-001'
REAL = Path(__file__).with_name('fixtures')/'a101/real'
PROGRAM = ROOT/'resources/software/infernal-1.1.5/hmmer/src/phmmer'
POLICY = LocalJobPolicy(1024**3, 64*1024**2)
ROLES = ('scientific_process', 'literature', 'launch', 'monitor', 'results')
CASES = {
    'lacy': ('transporter_lacy_P02920.faa', 'AF_P02920.pdb', 'P18817', 'AF_P18817.pdb'),
    'atpg': ('complex_subunit_atpg_P0ABA6.faa', 'AF_P0ABA6.pdb', 'Q9KNH4', 'AF_Q9KNH4.pdb'),
}


def fact_form(**sources):
    return obj({name: {'$ref': 'episode-fact:'+source} for name, source in sources.items()})


def child(role, assignment, scope, schema, goal):
    return {'kind': 'episode_child', 'role': role, 'assignment': assignment, 'scope': scope,
        'goal': goal, 'purpose': goal, 'schema_json': json.dumps(schema), 'initial_report_json': '{}'}


class EvidenceRootCase:
    def __init__(self, directory, store, *, case, usalign, sequence_only=False):
        self.directory, self.store, self.case = directory, store, case
        sequence_file, target_file, accession, reference_file = CASES[case]
        sequence = ''.join(line.strip() for line in (REAL/sequence_file).read_text().splitlines() if not line.startswith('>'))
        self.target, = store.create_problem(raw_sequence=sequence, molecule='protein')['subject_refs']
        self.scope = {'subject_refs': [self.target]}
        self.target_source = coordinate_source(store, target_file) if not sequence_only else None
        self.comparison_source = coordinate_source(store, '1PV7.cif') if sequence_only else None
        # The parent has a small caller-supplied model inventory. Which model
        # gets selected must come from the actual received A101 native hit.
        self.inventory = {key: coordinate_source(store, name) for key, name in (
            ('P18817', 'AF_P18817.pdb'), ('Q9KNH4', 'AF_Q9KNH4.pdb'))}
        self.expected_accession = accession
        panel = directory/'reference-panel.faa'
        panel.write_text(''.join((REAL/name).read_text() for name in (
            'reference_tpi_Q8ZKP7.faa', 'reference_lacy_P18817.faa', 'reference_atpg_Q9KNH4.faa')))
        self.jobs = HomologyJobs.create(directory/'jobs', executable=FileAsset(PROGRAM, digest(PROGRAM)),
            reference_database=FileAsset(panel, digest(panel)), policy=POLICY, max_cpu=1)
        self.homology = HomologyEpisodes(self.jobs, parser_policy=POLICY,
            credit_projector=lambda *a, **k: 0, credit_binding={'fixture': 'unused_legacy_channel'},
            monitoring_projector=lambda *a, **k: 0, monitoring_binding={'fixture': 'unused_legacy_channel'})
        self.tools = A102ToolRegistry(store, a102_work_directory=directory/'native', usalign_executable=usalign)
        self.trait_definition = (self.tools._source('fixture.local_trait_question',{
            'meaning':'Compare reference acidic-role and region traits; these are engineering probes, not characterized functional sites.',
            'reference_source_ref':self.inventory['P18817']}) if sequence_only else None)
        self.stages = defaultdict(int)
        self.asked = set()
        self.states, self.tasks, self.last = {}, {}, {}
        self.resource_views, self.root_views, self.bindings = [], [], {}
        self.capacity_retries = defaultdict(int)
        self.flow = create_evidence_root_workflow(store, self.tools, self, directory/'workflow',
            'a101-a102-root-mock', self.controller, job_episodes=self.homology,
            resource_estimator=ResourceToolEstimator(), decision_protocol=PROTOCOL,
            episode_service_factory=self.setup, episode_service_binding={'fixture': 'two_wing_native_mock_v1'},
            episode_service_inputs='actual_tool_registry_v1', annotation_child_roles=ROLES,
            initial_known_record_refs=[r for r in [self.target, self.target_source, self.comparison_source,
                self.trait_definition, *self.inventory.values()] if r])
        self.a101, self.a102 = A101Subtree(directory/'workflow'), A102Subtree(directory/'workflow')

    def setup(self, store, *, run_id, directory, job_episodes, resource_estimator, tool_catalog, tool_registry):
        # Existing homology launch/results ports and direct bounded structural
        # tools share one Workflow and host admission pool. This prototype does
        # not replace the independent A101/A102 service factories or CLI.
        return bind_assembled_services(store, run_id=run_id, directory=directory,
            job_episodes=job_episodes, resource_estimator=resource_estimator, source_directory=PUBLICATION,
            tool_catalog=tool_catalog, tool_registry=tool_registry,
            tool_retrieval={'version': 'scientific_tool_retrieval_v1', 'mode': 'literal_test_v1'},
            scientific_child_roles=ROLES, handoff_unit=1, acquired_record_unit=1,
            monitoring_information_unit=1, literature_outcome_page_size=8,
            monitor_outcome_page_size=8, log_window_bytes=128, log_roles=('native_text',),
            scientific_contract_information_profile=CONTRACT_INFORMATION_PROFILE)

    def has_session(self, episode_id, role): return episode_id in self.states
    def conversation_key(self, episode_id, role): return (episode_id+'-mock', 0) if episode_id in self.states else None
    async def release(self, episode_id): pass

    def controller(self, path, initial):
        from method_loop.identities import EpisodeRef
        episode_id = EpisodeRef('a101-a102-root-mock', path).episode_id
        role = path[-1][0]
        horizon = ((2 if path[-1][1] == 'child_0' else 3 if path[-1][1] == 'child_1' else 4) if role == 'scientific_process'
            else {'annotation': 6, 'launch': 1, 'launch_local': 4, 'results': 2}[role])
        def estimate(history, parameters, contexts):
            return YieldEstimate(len(history), NumericBand.exact(0 if len(history)>=horizon+self.capacity_retries[episode_id] else 1),
                parameters, {'fixture': 'explicit_finite_two_wing_wiring_mock', 'budget': horizon})
        return YieldController(str(path), initial, 0, estimate_with_context=estimate)

    async def complete(self, episode_id, role, instructions, frame, output_schema):
        if frame['kind'] in ('decision_bootstrap', 'decision_update'):
            self.states[episode_id] = apply_state_frame(self.states.get(episode_id), frame)
        else:
            assert frame['result']['status'] == 'completed', frame
        state = self.states[episode_id]
        if (state.get('feedback') or {}).get('code') == 'local_resource_busy':
            self.capacity_retries[episode_id] += 1
            for _ in range(1200):
                if self.tools.local_resources.snapshot()['available']['job_slots']:
                    return deepcopy(self.last[episode_id])
                await asyncio.sleep(.5)
            raise TimeoutError('Shared host remained busy')
        assert not state.get('feedback'), state.get('feedback')
        path = json.loads(self.store.db.execute('SELECT path FROM runtime_episodes WHERE episode_id=?', (episode_id,)).fetchone()[0])
        episode_role = path[-1][0]
        self.resource_views.append({'role': episode_role, 'resource_context': deepcopy(state['resource_context'])})
        stage = self.stages[episode_id]
        if episode_role == 'scientific_process' and state['scientific_process']['assignment']['context']['mock_task'] == 'sequence_search':
            contracts = ((('launch', 'execution_handoff'),) if stage == 0 else
                (('results', 'committed_record_refs'), ('results', 'job_result_progress')) if stage == 1 else ())
            for target_role, source in contracts:
                key = (episode_id, target_role, source)
                if key not in self.asked:
                    self.asked.add(key)
                    return {'response': {'response_type': 'request_context', 'lookup': {
                        'view': 'composition_information', 'operation': 'episode.return_contract',
                        'arguments': {'role': target_role, 'source': source}}}}
        self.stages[episode_id] += 1
        report = {}
        if episode_role == 'annotation':
            known = list(self.flow.receipts.known(episode_id))
            view = NativeEvidenceRootCredit().read_details(self.store, self.scope, known_record_refs=known, details_limit=0, details_offset=0)
            self.root_views.append({'stage': stage, **view})
            if stage == 0:
                selection = self.a102.commission(self.store, target_ref=self.target, scope=self.scope,
                    completeness='unknown', task='model_inventory', child_tool_info=[{'name': 'state.query', 'resources': 'local'}],
                    question='Request sequence-homolog leads from the parent before selecting structural comparisons.',
                    context={'mock_task': 'request_seed'})
            elif stage == 1:
                self.need = state['child_reports'][-1]['information_need_refs'][0]
                selection = self.a101.commission(self.store, target_ref=self.target, scope=self.scope,
                    completeness='unknown', child_tool_info=[{'name': 'state.query', 'resources': 'local'}],
                    question='Find sequence homologs in the explicitly supplied small reference panel; return actual native results for the parent to seed a sibling structural investigation.',
                    context={'mock_task': 'sequence_search', 'information_need_ref': self.need})
            elif stage == 2:
                returned = state['child_reports'][-1]
                self.sequence_refs = returned['records']
                seq = A101SequenceCredit().read_details(self.store, self.scope, known_record_refs=known, details_limit=64, details_offset=0)
                strongest = max(seq['source_contributions'], key=lambda row: row['bits'])
                accession = strongest['target_name'].split('|')[1]
                assert accession in self.inventory and accession == self.expected_accession
                self.reference_source = self.inventory[accession]
                self.seed_trace = {'accession': accession, 'native_sequence_source_ref': strongest['source_ref'],
                    'native_sequence_observation_ref': strongest['observation_ref'],
                    'grading_artifact_ref': strongest['grading_artifact_ref'],
                    'selected_coordinate_source_ref': self.reference_source,
                    'relationship': 'actual_received_sequence_hit_selects_model_from_parent_inventory',
                    'connection_credit': 'unscored'}
                selection = {'kind': 'tool', 'tool': 'shared.resolve_information_need', 'arguments': {
                    'need_ref': self.need, 'status': 'fulfilled', 'evidence_refs': [*self.sequence_refs, self.reference_source]}}
            elif stage == 3:
                self.disposition = state['last_local_outcome']['result']['publication_ref']
                selection = self.a102.commission(self.store, target_ref=self.target, scope=self.scope,
                    completeness='unknown', task='native_comparison', child_tool_info=[{'name': name, 'resources': 'local'}
                        for name in ('structure.bind', 'structure.inspect', 'structure.align')],
                    evidence_refs=[*self.sequence_refs, self.target_source, self.reference_source, self.need, self.disposition],
                    question='Use the parent-delivered A101 homolog lead to establish actual native structural correspondence; preserve the seed lineage and unknown exact function.',
                    context={'mock_task': 'native_comparison', 'seed_trace': self.seed_trace})
            elif stage == 4:
                self.structure_form = deepcopy(state['child_reports'][-1])
                # The restricted root sees current_credit and the native axis
                # vector in its decision context. It uses only coordination
                # operations; detailed science inspection belongs to a child.
                selection = {'kind': 'tool', 'tool': 'shared.list_information',
                    'arguments': {'kind': 'all', 'offset': 0, 'limit': 24}}
            else:
                selection = {'kind': 'tool', 'tool': 'shared.read_information', 'arguments': {'publication_ref': self.disposition}}
        elif episode_role == 'scientific_process':
            task = state['scientific_process']['assignment']['context']['mock_task']
            self.tasks[episode_id] = task
            if task == 'request_seed':
                report = structure_report()
                if stage == 0:
                    selection = {'kind': 'tool', 'tool': 'shared.request_information', 'arguments': {
                        'target_ref': self.target, 'question': 'Which nonidentical sequence homologs can seed structural comparisons?',
                        'required_information': 'Native sequence correspondence, homolog identifier and reference sequence provenance.',
                        'reason': 'Select actual corresponding structural models from the parent inventory.',
                        'blocking': True, 'available_record_refs': [self.target]}}
                else:
                    report['information_need_refs'] = [state['last_local_outcome']['result']['publication_ref']]
                    selection = {'kind': 'tool', 'tool': 'episode.credit', 'arguments': {'limit': 8, 'offset': 0}}
            elif task == 'sequence_search':
                report = sequence_report()
                if stage == 0:
                    assignment = {'version': 'resource_launch_assignment_v1', 'job_request': {'query_ref': self.target, 'cpu': 1},
                        'immutable_input_versions': [], 'constraints': {'cpu': 1}, 'resource_selection': None,
                        'software_knowledge_refs': [], 'resource_knowledge_refs': []}
                    selection = child('launch', assignment, self.scope, fact_form(handoff='execution_handoff'), 'Acquire native sequence-search handoff.')
                elif stage == 1:
                    selection = child('results', {'version': 'resource_results_assignment_v1',
                        'handoff': state['child_reports'][-1]['handoff'], 'requested_data_selector': {}}, self.scope,
                        fact_form(records='committed_record_refs', coverage='job_result_progress'), 'Acquire actual parsed native sequence evidence.')
                else:
                    report['family']['status'] = 'unresolved'
                    report['limitations'] = ['unknown_full_length', 'unassessed_alternatives']
                    selection = {'kind': 'tool', 'tool': 'episode.credit', 'arguments': {'limit': 24, 'offset': 0}}
            else:
                assert task == 'native_comparison'
                report = structure_report()
                if stage in (1, 2): self.bindings[stage-1] = state['last_local_outcome']['result']['binding_ref']
                if stage < 2:
                    selection = {'kind': 'tool', 'tool': 'structure.bind', 'arguments': {
                        'file_source_ref': self.target_source if stage == 0 else self.reference_source,
                        'target_ref': self.target if stage == 0 else None, 'format': 'pdb_3x_text', 'chain_id': 'A',
                        'model_ordinal': 0, 'block_ordinal': 0, 'origin': 'predicted',
                        'origin_witness_refs': [self.target_source if stage == 0 else self.reference_source],
                        'qualifications': ['Retained AlphaFold model; confidence is not a geometry weight.']}}
                elif stage == 2:
                    selection = {'kind': 'tool', 'tool': 'structure.align', 'arguments': {
                        'target_binding_ref': self.bindings[0], 'reference_binding_ref': self.bindings[1], 'primary': True}}
                else:
                    report.update(structural_summary='native_geometry_retained', scope_status='represented', functional_support='fold_only',
                        limitations=['predicted_target', 'predicted_reference', 'unknown_full_length', 'function_features_unassessed', 'alternatives_unassessed'])
                    selection = {'kind': 'tool', 'tool': 'episode.credit', 'arguments': {'limit': 24, 'offset': 0}}
        elif episode_role == 'launch':
            binding = self.flow.episode_bindings.for_role('launch'); adapter, = binding.adapters.values()
            assignment = deepcopy(state['assignment']); assignment['resource_selection'] = adapter._selection(1)
            selection = child('launch_local', assignment, self.scope, state['requested_form'], 'Establish selected native sequence job.')
        elif episode_role == 'launch_local':
            selection = {'kind': 'tool', 'tool': ('homology.configure', 'homology.stage', 'homology.submit', 'homology.check_handoff')[stage], 'arguments': {}}
        else:
            assert episode_role == 'results'
            selection = {'kind': 'tool', 'tool': 'homology.extract' if stage == 0 else 'homology.coverage',
                'arguments': {'offset': 0, 'limit': 20} if stage == 0 else {'snapshot_ref': state['last_local_outcome']['result']['snapshot_ref']}}
        response = {'response': {'response_type': 'select_action', 'selection': selection, 'report_update': report}}
        self.last[episode_id] = deepcopy(response)
        return response

    async def run(self):
        root = self.flow.build('annotation', 'root', 'Coordinate A101 and A102 as independent sibling wings on one supplied protein.', self.scope)
        record = await root.run_async(self.flow.context)
        await root.build_result(record)
        parent = root.source
        view = NativeEvidenceRootCredit().read_details(self.store, self.scope,
            known_record_refs=self.flow.receipts.known(parent.episode_id), details_limit=64, details_offset=0)
        assert view['credit'] == record.controller_state.current_credit
        grades = [received_grade(self.store, r[0])['grade'] for r in self.store.db.execute('SELECT source_ref FROM a102_native_publications')]
        assert len(grades) == 1
        assert view['axis_components']['A102'] == grades[0]['components']['B']
        assert self.structure_form['structural_credit'] == view['axis_components']['A102']
        assert self.root_views[1]['credit'] == 0
        assert self.root_views[2]['credit'] == self.root_views[2]['axis_components']['A101'] > 0
        assert self.root_views[2]['axis_components']['A102'] == 0
        assert self.root_views[4]['credit'] == self.root_views[5]['credit'] == view['credit']
        assert len({r['resource_context']['local']['resource_id'] for r in self.resource_views}) == 1
        assert all(r['resource_context']['local']['limits']['max_running_jobs'] == 1 for r in self.resource_views)
        assert self.jobs.db.execute('SELECT count(*), sum(submission_requested) FROM orders').fetchone()[:] == (1, 1)
        result = {'case': self.case, 'decision_mode': 'scripted_wiring_mock_with_real_phmmer_and_USalign',
            'credit': view, 'root_timeline': self.root_views, 'seed_trace': self.seed_trace,
            'native_structural_components': grades[0]['components'], 'structure_form': self.structure_form,
            'sequence_searches_submitted': 1, 'structural_comparisons': 1,
            'shared_host_resource_id': self.resource_views[0]['resource_context']['local']['resource_id'],
            'connection_credit': None, 'connection_status': 'tool_specific_attribution_without_an_axis_wide_multiplier'}
        (self.directory/'RESULTS.json').write_text(json.dumps(result, indent=2)+'\n')
        return result
