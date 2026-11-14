"""Complete selected child path using controlled PBS and synthetic BLAST JSON.

The real producer, custody, numerical worker, Store, action journal and original
return records execute. Fake PBS scripts run locally; no database BLAST, SSH,
HPC submission, model, installation or remote scientific service is invoked.
"""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

from method_loop.episode import EpisodeGoal, EpisodeRequest
from method_loop.identities import EpisodeRef
import pytest

from gene_annotation_episode.communication import form_with_facts, plain
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes, LAUNCH_VERSION, RESULTS_VERSION
from gene_annotation_episode.materials import artifact_path
from gene_annotation_episode.native_blast_standard_database_contracts import requested_job_from_standard_blast_database
from gene_annotation_episode.native_blast_standard_database_result_views import standard_blast_database_fact_sources
from gene_annotation_episode.practical_pbs_operations import PBSPracticalOperations, _REMOTE_WORKER
from gene_annotation_episode.runtime import Record, TypedReportContract
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_native_blast_standard_database_driver import fixture as producer_fixture, write
from test_practical_pbs_operations import remote as remote_fixture, REAL_RUN
from test_execution_episodes_family import native_assignment


def schema_for(*sources):
    descriptors = standard_blast_database_fact_sources()
    fields = {'field_' + str(i): deepcopy(descriptors[s]['report_schema']) for i, s in enumerate(sources)}
    return dict(type='object', properties=fields, required=list(fields), additionalProperties=False)


def selector(*families, metadata_inputs=None, retained_sources=None):
    metrics = {'search': ['reported_hit_count'], 'hsp': ['native_score_bits', 'native_evalue']}
    return dict(version='native_blast_standard_database_selector_v1', acquisition='complete_bound_bundle',
        metadata_inputs=metadata_inputs or [], retained_sources=retained_sources or [],
        projections=[dict(family=f, rows={'offset': 0, 'limit': 5}, metrics=metrics[f],
            booleans=[]) for f in families or ['hsp']])


class SyntheticHost:
    def __init__(self, tmp_path, monkeypatch, program='blastp', *, nonzero=False, metadata=None, tuples=None,
                 empty_logs=False, query_kind='sequence', query_bytes=None, sequence=None, native_hsp=None, model=None,
                 molecule=None, native_report=None, report_format=None, report_fields=None,
                 job_options=None):
        sequence = sequence or ('AC' if query_kind == 'pssm' else 'GCTTGTGGTACC' if program in {'blastx', 'tblastx'} else 'ACGT')
        remote = remote_fixture.__wrapped__(tmp_path, monkeypatch)
        # Keep the established fake PBS scripts, but bind only the transport
        # method. Unrelated local_jobs subprocesses retain their real runner.
        import subprocess
        monkeypatch.setattr(subprocess, 'run', REAL_RUN)
        self.calls = []
        def transport(operations, request):
            self.calls.append(deepcopy(request))
            env = dict(os.environ, PATH=str(tmp_path / 'pbs-bin') + os.pathsep + os.environ['PATH'],
                FAKE_PBS_ROOT=str(remote.database))
            response = REAL_RUN([sys.executable, '-B', '-c', _REMOTE_WORKER], input=canonical(request).encode(),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            if response.returncode:
                raise ValueError('controlled_pbs_worker_failed:' + response.stderr.decode())
            reply = json.loads(response.stdout)
            assert reply['request_sha256'] == digest(request)
            return reply['result']['outcome'], reply['result']['context_after']
        monkeypatch.setattr(PBSPracticalOperations, '_invoke', transport)
        self.tmp_path, self.workspace = tmp_path, remote.workspace
        _, plan, manifest = producer_fixture(self.workspace / 'synthetic-inputs', program=program, query=query_kind)
        job = deepcopy(plan['requested_job']['native_blast_standard_database'])
        if query_kind == 'sequence' and query_bytes is None:
            query_bytes = ('>one\n' + sequence + '\n').encode()
        if query_bytes is not None:
            job['inputs'][0].update(write(Path(job['inputs'][0]['path']), query_bytes))
        job['grading_parameters']['sequence_database_model'] = model
        if job_options is not None:
            job['options'] = list(job_options)
        if report_format is not None:
            selected_output = next(r for r in job['outputs'] if r['role'] == 'primary_report')
            selected_output.update(format=report_format, fields=list(report_fields or []),
                delimiter='\t' if report_format == 'tabular7' else None)
            job['software']['engine_version'] = '2.17.0+'
        if metadata is None:
            job['inputs'] = job['inputs'][:1]; job['metadata_inputs'] = []
        else:
            job['inputs'][1].update(write(Path(job['inputs'][1]['path']), canonical(metadata).encode()))
            job['metadata_inputs'] = tuples
        job['environment']['FAKE_PBS_EXECUTE'] = '1'
        native_program = 'psitblastn' if query_kind == 'pssm' else program
        hsp = dict(query_from=1, query_to=4, hit_from=1, hit_to=4, align_len=4, identity=4,
            qseq='ACGT', hseq='ACGT', gaps=0, bit_score=20, score=40, evalue=0.0)
        if query_kind == 'pssm':
            hsp.update(query_to=len(sequence), hit_to=3*len(sequence), align_len=len(sequence), identity=len(sequence), qseq=sequence, hseq=sequence, hit_frame=1)
        else:
            if program in {'blastx', 'tblastx'}: hsp.update(query_to=12, query_frame=1)
            if program in {'tblastn', 'tblastx'}: hsp.update(hit_to=12, hit_frame=1)
        hsp = native_hsp or hsp
        report = {'BlastOutput2': [{'report': dict(program=native_program, version=native_program.upper() + ' 2.17.0+',
            search_target={'db': 'target'}, params={}, results={'search': dict(query_id='one', query_title='one', query_len=len(sequence),
                hits=[dict(len=max(hsp['hit_from'], hsp['hit_to']), description=[dict(id='A', accession='A.1', title='synthetic A')], hsps=[hsp])])})}]}
        script = ('#!' + sys.executable + '\nimport pathlib, sys\n'
            + ('' if empty_logs else 'print("synthetic stdout")\nsys.stderr.write("synthetic stderr\\n")\n')
            +
            'pathlib.Path(sys.argv[sys.argv.index("-out")+1]).write_bytes(' + repr(json.dumps(report).encode() if native_report is None else native_report) + ')\n'
            'pathlib.Path("synthetic-emitter-invoked").write_text("one synthetic emission")\n'
            'raise SystemExit(' + ('7' if nonzero else '0') + ')\n').encode()
        software = write(Path(job['software']['executable']), script)
        job['software']['sha256'] = software['sha256']
        self.job = job
        config = deepcopy(remote.configuration)
        config['native_blast_standard_database'] = dict(version='native_blast_standard_database_resource_v1',
            producer=dict(module_root=manifest['module_root'], manifest=plan['producer_manifest']), environment={},
            bindings=[dict(program=program, mode='database', software=job['software'],
                database_manifests=[db['manifest_file'] for db in job['databases']])])
        self.config = config
        self.store = Store(tmp_path / 'store')
        self.scope = {'subject_refs': self.store.create_problem(raw_sequence=sequence,
            molecule=molecule or ('dna' if program in {'blastn', 'blastx', 'tblastx'} else 'protein'))['subject_refs']}
        self.run_id = 'synthetic-336-' + program
        self.journal, self.receipts = Journal(self.store, self.run_id), EpisodeReceipts(self.store, self.run_id)
        self.family = ExecutionEpisodes(None, store=self.store, directory=tmp_path / 'run', run_id=self.run_id,
            resources={'synthetic-hpc': config}, initial_information={}, tool_registry=ToolRegistry(self.store),
            handoff_unit=3, acquired_record_unit=2, log_window_bytes=1024, log_roles=['stdout', 'stderr'])
        self.root = self.context((('annotation', 'root'),), {}, None)
        self.receipts.receive(self.root.episode_id, self.scope['subject_refs'], kind='initial')
        self.assignment = native_assignment(self.workspace, 'synthetic-hpc', kind='hpc')
        self.assignment['requested_job'] = requested_job_from_standard_blast_database(job)
        self.assignment['constraints'] = {'account': 'EpiCalib', 'queue': 'selected-queue', 'resources': ['select=1:ncpus=4']}
        launch = dict(version=LAUNCH_VERSION, requests={'synthetic-hpc': self.assignment}, immutable_input_versions=[], constraints={})
        handoff_schema = dict(type='object', properties={'handoffs': self.family.fact_sources('launch')['execution_handoff_refs']['report_schema']},
            required=['handoffs'], additionalProperties=False)
        self.launch = self.child(self.root, 'launch', launch, handoff_schema, index=0)
        selected = self.family.prepare_assignment(self.launch, 'launch_hpc', self.assignment, self.scope, 'commission-hpc')
        self.hpc = self.child(self.launch, 'launch_hpc', selected, handoff_schema, index=0)
        self.family.initialize(self.hpc)
        outcome = self.select(self.hpc, 0, 'practical.job.start', {'queue': 'selected-queue', 'resources': ['select=1:ncpus=4']})
        assert outcome['status'] == 'completed', outcome
        self.handoff = outcome['record_refs'][0]
        self.target = self.family.job_progress_provider.targets.read_target(self.handoff, self.scope)
        self.deliver(self.hpc, self.launch, self.family.facts(self.hpc, {}))
        self.deliver(self.launch, self.root, self.family.facts(self.launch, {}))

    def context(self, path, assignment, contract, parent=None):
        ref = EpisodeRef(self.run_id, path)
        self.receipts.bind(ref.episode_id, None if parent is None else parent.episode_id)
        goal = (EpisodeGoal.root(objective='Synthetic integration verification', result_contract={'role': path[-1][0]})
            if parent is None else EpisodeGoal.child(EpisodeGoal.from_record(plain(parent.request)['goal']),
                objective='Synthetic integration verification', result_contract=contract.schema))
        request = EpisodeRequest(goal, Record({'scope': deepcopy(self.scope), 'initial_report': {}, 'episode_assignment': deepcopy(assignment)}), contract).as_record()
        ctx = BindingContext(self.run_id, ref.episode_id, path[-1][0], path, self.scope, assignment, request)
        self.journal.save('runtime_episodes', dict(episode_id=ctx.episode_id, path=canonical(path), request=canonical(request),
            initial_credit=0, state='active', completion=None, archive=None))
        return ctx

    def child(self, parent, role, assignment, schema, *, index):
        contract = TypedReportContract('Return the explicitly requested frozen values', schema, lambda *_: True)
        child = self.context((*parent.path, (role, 'child_' + str(index))), assignment, contract, parent)
        action = dict(kind='episode_child', role=role, assignment=assignment, scope=self.scope,
            purpose=contract.decision, schema_json=canonical(schema))
        self.journal.save('runtime_actions', dict(episode_id=parent.episode_id, decision_index=index,
            action=canonical(action), result=None, credit=None))
        return child

    def results(self, selection=None, *, index=1, typed=True):
        selected = selection or selector('search', 'hsp')
        assignment = dict(version=RESULTS_VERSION, handoff_ref=self.handoff, selector=selected)
        prepared = self.family.prepare_assignment(self.root, 'results', assignment, self.scope, 'commission-results')
        sources = ['execution_blast_standard_database_' + row['family'] + '_rows' for row in selected['projections']]
        schema = (schema_for(*sources, 'execution_blast_standard_database_acquisition', 'execution_blast_standard_database_failures') if typed else
            dict(type='object', properties={'complete': {'type': 'boolean', 'x-source': 'execution_completed'}},
                required=['complete'], additionalProperties=False))
        child = self.child(self.root, 'results', prepared, schema, index=index)
        self.family.initialize(child)
        self.receipts.receive(child.episode_id, self.family.initial_references(child), kind='initial')
        return child

    def select(self, context, index, name, arguments=None):
        arguments = arguments or {}
        self.journal.save('runtime_actions', dict(episode_id=context.episode_id, decision_index=index,
            action=canonical(dict(kind='tool', tool=name, arguments=arguments)), result=None, credit=None))
        key = f'{context.run_id}:{context.episode_id}:{index}'
        result = asyncio.run(self.family.execute(context, name, arguments, key))
        self.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?',
            (canonical(result), context.run_id, context.episode_id, index))
        if result.get('record_refs'):
            self.receipts.receive(context.episode_id, result['record_refs'], kind='own_action', source_index=index)
        return result

    def returned(self, context):
        return self.deliver(context, self.root, self.family.native_blast_standard_database_results.facts(context))

    def deliver(self, context, parent, facts):
        schema = plain(context.request)['report_contract']['measurements']['schema']
        form = form_with_facts({}, schema, facts)
        self.family.validate_received_report(context, form, schema)
        self.journal.save('runtime_forms', dict(episode_id=context.episode_id, facts=canonical(facts), form=canonical(form)))
        index = int(context.path[-1][1].removeprefix('child_'))
        self.journal.save('runtime_report_attempts', dict(parent_episode_id=parent.episode_id, decision_index=index,
            delivery_ref='delivery_' + digest([context.episode_id, index]), child_episode_id=context.episode_id,
            contract=canonical(context.request['report_contract']), form=canonical(form), failure=None))
        admitted = self.family.received_form_references(parent, form, schema, f'{self.run_id}:{parent.episode_id}:{index}:typed_form')
        self.receipts.receive(parent.episode_id, admitted, kind='child_form', source_index=index)
        return form, schema


@pytest.mark.parametrize('program', ['blastn', 'blastp', 'blastx', 'tblastn', 'tblastx'])
def test_five_selected_pbs_children_collect_and_return_original_facts(tmp_path, monkeypatch, program):
    h = SyntheticHost(tmp_path, monkeypatch, program)
    try:
        child = h.results()
        outcome = h.select(child, 0, 'execution.results.collect')
        assert outcome['status'] == 'completed', outcome
        body = outcome['result']
        assert body['complete'], body['failures']
        assert body['capture']['status'] == 'complete'
        publication = body['publication']
        row, = publication['rows_by_family']['hsp']
        assert row['publication_status'] == 'source_only'
        assert row['observation_ref'] is None
        assert {m['name']: m['value'] for m in row['measurements']} == {'native_score_bits': 20, 'native_evalue': 0.0}
        assert len(list(h.workspace.rglob('synthetic-emitter-invoked'))) == 1
        assert len([r for r in h.calls if r.get('tool_name') == 'practical.job.start']) == 1
        assert all(r['limit'] <= 1024**2 for r in h.calls if r['mode'] == 'read_output')
        proof = h.family.completion_for_action(child, body['operation_key'])
        assert proof is not None and h.family.verify_completion(child, proof)
        form, schema = h.returned(child)
        received = h.family.native_blast_standard_database_returns.received_facts(h.root, schema)
        assert received['execution_blast_standard_database_hsp_rows'] == [row]
        assert h.family.resolve_received_reference(h.root, row['record_key'], 'native_blast_standard_database_row') is True
        assert h.family.resolve_received_reference(h.root, 'unrequested-row', 'native_blast_standard_database_row') is False
        assert h.family.native_blast_standard_database_results.credit_view(child, dict(known_record_refs=body['record_refs'],
            initial_known_record_refs=body['record_refs']))['credit'] == 0
    finally:
        h.store.close()




def test_zero_hits_are_a_complete_selected_result_and_empty_return(tmp_path, monkeypatch):
    raw = canonical({'BlastOutput2': [{'report': dict(program='blastp', version='BLASTP 2.17.0+',
        search_target={'db': 'target'}, params={}, results={'search': dict(query_id='one', query_title='one',
            query_len=4, hits=[])})}]}).encode()
    h = SyntheticHost(tmp_path, monkeypatch, native_report=raw)
    try:
        child = h.results(selector('search', 'hsp'))
        body = h.select(child, 0, 'execution.results.collect')['result']
        assert body['complete'] and body['publication']['native_execution_successful'] and body['publication']['projection_complete']
        assert body['publication']['rows_by_family']['hsp'] == []
        assert body['publication']['rows_by_family']['search'][0]['measurements'][0]['value'] == 0
        form, schema = h.returned(child)
        facts = h.family.native_blast_standard_database_returns.received_facts(h.root, schema)
        assert facts['execution_blast_standard_database_hsp_rows'] == []
        assert h.store.query_records('observation')['total'] == 0
        assert h.family.completion_for_action(child, f'{h.run_id}:{child.episode_id}:0') is not None
        (tmp_path / 'zero-hits-return.json').write_text(canonical(dict(form=form, schema=schema, receipt=body)))
    finally:
        h.store.close()


def test_failed_original_attempt_crosses_all_boundaries_without_handoff_credit(tmp_path, monkeypatch):
    h = SyntheticHost(tmp_path, monkeypatch, nonzero=True)
    try:
        targets = h.family.job_progress_provider.targets
        assert targets.returnable_handoff(h.target) and not targets.usable_handoff(h.target)
        for context in (h.hpc, h.launch):
            facts = h.family.facts(context, {})
            assert facts['execution_handoff_refs'] == [h.handoff]
            assert not facts['execution_completed']
        selection = dict(run_id=h.run_id, episode_id=h.launch.episode_id,
            known_record_refs=[h.handoff], initial_known_record_refs=[])
        assert h.family.project_credit(h.launch, selection)['credit'] == 0
        assert h.handoff in h.receipts.known(h.root.episode_id)
        child = h.results(selector('hsp'))
        body = h.select(child, 0, 'execution.results.collect')['result']
        assert body['capture']['status'] == 'complete'
        assert not body['publication']['native_execution_successful'] and not body['complete']
        assert h.family.completion_for_action(child, body['operation_key']) is None
        original_forms = [dict(row) for row in h.store.db.execute('SELECT * FROM runtime_forms ORDER BY episode_id')]
        form, schema = h.returned(child)
        facts = h.family.native_blast_standard_database_returns.received_facts(h.root, schema)
        assert facts['execution_blast_standard_database_hsp_rows'][0]['measurements'][0]['value'] == 20
        assert not facts['execution_blast_standard_database_acquisition']['complete']
        for old in original_forms:
            assert dict(h.store.db.execute('SELECT * FROM runtime_forms WHERE episode_id=?', (old['episode_id'],)).fetchone()) == old
        bundle = json.loads(h.store.get_artifact(body['capture']['bundle_artifact_ref']))
        assert bundle['process']['returncode'] == 7
        (tmp_path / 'failed-attempt-return.json').write_text(canonical(dict(receipt=body, form=form, schema=schema)))
    finally:
        h.store.close()


def test_five_callable_names_and_results_knowledge_are_distinct(tmp_path, monkeypatch):
    h = SyntheticHost(tmp_path, monkeypatch, program='blastp')
    try:
        entries = h.family.resource_tool_contracts()
        selected = next(row for row in entries if row['name'] == 'native.blastp.database')
        assert selected['invocation_route']['routes'] == [dict(entry_role='launch', resource_id='synthetic-hpc', resource_role='launch_hpc')]
        assert selected['input_schema']['properties']['native_blast_standard_database']['properties']['program']['const'] == 'blastp'
        index = json.loads((Path(__file__).resolve().parents[1] / 'gene_annotation_episode/knowledge/index.json').read_text())
        entry = next(row for row in index['entries'] if row['entry_id'] == 'native-blast-standard-database-results')
        assert entry['tool_names'] == ['native.' + p + '.database' for p in ('blastn', 'blastp', 'blastx', 'tblastn', 'tblastx')]
        assert entry['resource_kinds'] == ['hpc']
    finally:
        h.store.close()
