"""Actual nonempty NMF input admission through the preserved owner callback.

Original recorded software metadata is a declaration for this unexecuted test
request. No native preparation, fit, grading, producer or new fact is claimed.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import resources
from ..state import Store
from ..episode_journal import Journal
from ..episode_receipts import EpisodeReceipts
from ..episode_bindings import BindingContext
from ..method_loop.identities import EpisodeRef
from ..method_loop.episode import EpisodeGoal, EpisodeRequest
from ..runtime import Record
from ..execution_contracts import canonical
from ..native_expression_nmf_contracts import expression_nmf_environment, requested_job_from_expression_nmf
from ..hpc_work_planning.execution_job_submission.episode import ExecutionEpisode

RAW = b'gene,A,B,B\ng,1,2,0\ng,0,1,3\ng3,1,3,3\n'
PLAN_SHA = '46e67006d31de1455f80de7c79d482793587e15960d54e9629954cc9ccfed0c3'


def test_nonempty_nmf_input_admission_retains_bound_owner_and_received_identity(tmp_path, monkeypatch):
    with Store(tmp_path / 'store') as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        scope, run_id = store.validate_scope(), 'bound-nmf-input-callback'
        journal, receipts = Journal(store, run_id), EpisodeReceipts(store, run_id)
        path = (('annotation', 'root'),)
        episode_id = EpisodeRef(run_id, path).episode_id
        inheritance = receipts.bind(episode_id, None)
        goal = EpisodeGoal.root(objective='Authenticate the provided matrix metadata', result_contract={'role': 'annotation'})
        request = EpisodeRequest(goal, Record({'scope': scope, 'episode_assignment': {},
            'initial_report': {}, 'knowledge_inheritance': inheritance}), None).as_record()
        context = BindingContext(run_id, episode_id, 'annotation', path, scope, {}, request)
        journal.save('runtime_episodes', {'episode_id': episode_id, 'path': canonical(path),
            'request': canonical(request), 'initial_credit': 0, 'state': 'active'})
        reference = store.artifact(RAW, 'text/csv')
        receipts.receive(episode_id, [reference], kind='initial')
        original = Path(__file__).parent / 'fixtures/expression_nmf/selected-native-plan.json'
        raw_plan = original.read_bytes()
        assert hashlib.sha256(raw_plan).hexdigest() == PLAN_SHA
        job = deepcopy(json.loads(raw_plan)['requested_job']['native_expression_nmf'])
        digest = hashlib.sha256(RAW).hexdigest()
        input_path = store.path / 'artifacts' / digest[:2] / digest
        job['input'] = {'artifact_ref': reference, 'path': str(input_path), 'sha256': digest,
            'size_bytes': len(RAW), 'delimiter': ',', 'metadata': {'units': 'counts'}}
        selected = requested_job_from_expression_nmf(job,
            environment=expression_nmf_environment(job['software'], attempt_directory=str(tmp_path / 'unexecuted')))
        owner = ExecutionEpisode(SimpleNamespace(annotation_task_required=lambda: False), store=store,
            run_id=run_id, directory=tmp_path / 'workflow', resources=resources(), initial_information={},
            tool_registry=None, handoff_unit=3., acquired_record_unit=2., log_window_bytes=1024, log_roles=('stdout',))
        assignment = {'requested_job': selected}
        versions = [{'reference': reference, 'version': None, 'content_sha256': digest}]
        before = list(store.db.iterdump())
        assert owner._expression_nmf_inputs(context, assignment) == [reference]
        input_path.unlink()
        monkeypatch.setattr(store, 'get_artifact', lambda *_: pytest.fail('input admission reread scientific bytes'))
        owner._versions(versions, scope, context=context, nmf_assignments=[assignment])
        assert owner._expression_nmf_inputs(context, assignment) == [reference]
        changed = deepcopy(versions)
        changed[0]['content_sha256'] = 'f' * 64
        with pytest.raises(ValueError, match='version_conflict'):
            owner._versions(changed, scope, context=context, nmf_assignments=[assignment])
        assert list(store.db.iterdump()) == before
