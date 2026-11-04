"""Explicitly selected bounded API fixture; no network or model is configured."""
import asyncio
from dataclasses import replace

from gene_annotation_episode.api_execution import HMMERAPIExecution
from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.execution_contracts import canonical


class APIHarness:
    def __init__(self, tools, *, subject_ref=None, algorithm='phmmer', database='swissprot',
                 parameters=None, page_size=50, scope=None, assignment=None, episode_id='api-child', run_id='api-run'):
        self.store, self.tools = tools.store, tools
        subject_ref = subject_ref or self.store.targets()[0]['id']
        scope = scope or self.store.validate_scope(None)
        assignment = assignment or {'version': 'api_execution_assignment_v1', 'resource_id': 'ebi',
            'service': 'ebi_hmmer', 'subject_ref': subject_ref, 'algorithm': algorithm, 'database': database,
            'parameters': parameters or {}, 'page_size': page_size, 'endpoint': 'usable_handoff', 'constraints': {}}
        self.api = HMMERAPIExecution(self.store, run_id=run_id, directory=self.store.path/'api-run',
            configuration={'ebi': {'kind': 'hmmer_api'}}, tool_registry=tools,
            handoff_unit=2., acquired_record_unit=.25)
        role = 'results' if assignment['version'] == 'execution_results_assignment_v1' else 'launch_api'
        self.context = BindingContext(run_id, episode_id, role, ((role, episode_id),), scope, assignment,
            {'message': {'scope': scope, 'episode_assignment': assignment}})
        self.journal = Journal(self.store, run_id)
        original = self.store.db.execute('SELECT * FROM runtime_episodes WHERE run_id=? AND episode_id=?',
                                        (run_id, episode_id)).fetchone()
        if original is None:
            with self.store.transaction():
                self.journal.save('runtime_episodes', {'episode_id': episode_id,
                    'path': canonical(plain(self.context.path)), 'request': canonical(self.context.request),
                    'initial_credit': 0, 'state': 'running'})
        self.index = self.store.db.execute('SELECT COALESCE(MAX(decision_index)+1,0) FROM runtime_actions '
            'WHERE run_id=? AND episode_id=?', (run_id, episode_id)).fetchone()[0]
        self.api.initialize(self.context)

    async def act_async(self, name, arguments=None, *, index=None):
        arguments = arguments or {}
        if index is None:
            index = self.index
            self.index += 1
            with self.store.transaction():
                self.journal.save('runtime_actions', {'episode_id': self.context.episode_id, 'decision_index': index,
                    'action': canonical({'kind': 'tool', 'tool': name, 'arguments': arguments}), 'result': None, 'credit': None})
        key = f'{self.context.run_id}:{self.context.episode_id}:{index}'
        result = await self.api.execute(self.context, name, arguments, key)
        with self.store.transaction():
            self.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?',
                (canonical(result), self.context.run_id, self.context.episode_id, index))
        return result

    def act(self, name, arguments=None, *, index=None):
        return asyncio.run(self.act_async(name, arguments, index=index))

    def handoff(self):
        submitted = self.act('api.hmmer.submit')
        assert submitted['status'] == 'completed', submitted
        checked = self.act('api.hmmer.check_handoff')
        assert checked['status'] == 'completed', checked
        return checked['result']['handoff_ref']

    def results(self, handoff_ref, *, page=1, page_size=None, episode_id='results-child'):
        selector = {'page': page}
        if page_size is not None:
            selector['page_size'] = page_size
        return APIHarness(self.tools, scope=plain(self.context.scope), episode_id=episode_id,
            run_id=self.context.run_id, assignment={'version': 'execution_results_assignment_v1',
            'handoff_ref': handoff_ref, 'selector': selector})

    def received_selection(self, refs=None, initial=()):
        refs = refs if refs is not None else [ref for result in self.api._own_results(self.context)
                                            for ref in result['record_refs']]
        return {'run_id': self.context.run_id, 'episode_id': self.context.episode_id,
                'known_record_refs': list(dict.fromkeys(refs)), 'initial_known_record_refs': list(initial)}
