"""Actual direct owner fixtures; engineering controls, no scientific execution.

The retained required LaunchConnected helper constructs a real mathematical HPC
plan only to supply a validated original practical assignment. This helper then
constructs every direct Launch/Results/native binding and the actual registry at
annotation/scientific paths, without any HPC ancestor in the selected path.
There is no own-axis annotation parent binding. Scientific ancestor request
metadata is controlled and is not a prepared/executed scientific invocation.
Selected task methods use the documented detached __new__ fixture; the separate
Workflow.build check exercises the real constructor. No provider/network/native
process executes. Results' target visibility and received set are controlled.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import replace
import os
from types import SimpleNamespace

import pytest
from gene_annotation_episode.episodic_workflow.root.a107.tests.launch_connected import LaunchConnectedChecks


class DirectPrivateTaskFixture:
    module = LaunchConnectedChecks.module
    source = LaunchConnectedChecks.source
    task = LaunchConnectedChecks.task

    def workflow(self, value):
        w = LaunchConnectedChecks.workflow(self, value)
        w.specialist = lambda source: value.runtime.Workflow.specialist(w, source)
        w.is_scientific_source = lambda source: value.runtime.Workflow.is_scientific_source(w, source)
        return w

    @pytest.fixture
    def connected(self, tmp_path):
        seed = LaunchConnectedChecks()
        seed.binding_path = 'hpc_work_planning/execution_job_submission'
        original = LaunchConnectedChecks.connected.__wrapped__(seed, tmp_path)
        baseline = next(original)
        try:
            v = SimpleNamespace(**baseline.__dict__)
            constructors = list(v.all_bindings)
            original_science = next(item for item in constructors if item.binding_path == 'scientific_process')
            scientific = self.module('scientific_process/episode').ScientificProcessEpisode(
                original_science.services, library=original_science.library,
                tool_library=original_science.tool_library,
                child_roles=('scientific_process', 'hpc', 'launch', 'results'))
            constructors[constructors.index(original_science)] = scientific
            direct = {}
            native = ('api_job_execution', 'local_job_execution', 'hpc_job_execution') if 'a107' == 'a107' else ('local_job_execution', 'hpc_job_execution')
            for prefix in ('', 'scientific_process/'):
                homes = [prefix + 'execution_job_submission',
                    *(prefix + 'execution_job_submission/' + name for name in native),
                    prefix + 'execution_result_acquisition']
                for home in homes:
                    binding = self.module(home + '/episode').ExecutionEpisode(baseline.launch.services,
                        **baseline.execution_options)
                    direct[home] = binding
                    constructors.append(binding)
            v.registry = self.module('episode_bindings').EpisodeBindingRegistry(constructors)
            v.all_bindings, v.direct_bindings = constructors, direct
            v.contexts = dict(v.contexts)
            prefix = 'scientific_process/' if self.binding_path.startswith('scientific_process/') else ''
            path = (('annotation', 'root'),) + ((('scientific_process', 'science'),) if prefix else ())
            identity = self.module('method_loop.identities').EpisodeRef
            def context(role, path, assignment):
                request = {'message': {'scope': v.runtime._plain(baseline.context.scope),
                    'episode_assignment': deepcopy(assignment), 'initial_report': {}}}
                # BindingContext freezes mapping values. Use original plain
                # JSON operands rather than deepcopy of MappingProxyType.
                request['message']['scope'] = v.runtime._plain(baseline.context.scope)
                value = self.module('episode_bindings').BindingContext(v.run_id,
                    identity(v.run_id, path).episode_id, role, path,
                    request['message']['scope'], assignment, request)
                v.journal.save('runtime_episodes', {'episode_id': value.episode_id,
                    'path': v.runtime._json(path), 'request': v.runtime._json(request),
                    'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})
                v.contexts[value.episode_id] = value
                return value
            v.parent_context = context(path[-1][0], path, {})
            v.parent = v.registry.for_path(path) if prefix else None
            if v.parent is None:
                with pytest.raises(LookupError, match='episode_role_not_bound:annotation'):
                    v.registry.for_path(path)
            v.launch = direct[prefix + 'execution_job_submission']
            original_assignment = deepcopy(v.plan['launch_assignment'])
            # Actual child validation; the direct parent is not an HPC plan
            # authenticator. No HPC commissioning reservation is inferred.
            admitted = v.launch.prepare_assignment(v.parent_context, 'launch', original_assignment,
                v.parent_context.scope, 'direct-original-launch')
            assert admitted == original_assignment
            v.context = context('launch', path + (('launch', 'child_3'),), admitted)
            v.launch.initialize(v.context)
            v.native_context = context('launch_hpc', v.context.path + (('launch_hpc', 'child_5'),),
                deepcopy(v.plan['practical_assignment']))
            v.native = v.registry.for_path(v.native_context.path)
            assert v.registry.for_path(v.context.path) is v.launch
            assert v.registry.for_child(path, 'launch') is v.launch
            assert not any(role == 'hpc' for role, _ in v.context.path)
            yield v
        finally:
            original.close()

    @pytest.fixture
    def selected(self, connected, monkeypatch):
        v = connected
        role = 'launch' if self.binding_path.endswith('execution_job_submission') else 'results'
        if role == 'launch':
            context, binding = v.context, v.launch
        else:
            path = v.parent_context.path + (('results', 'child_9'),)
            episode_id = self.module('method_loop.identities').EpisodeRef(v.run_id, path).episode_id
            assignment = {'version': 'execution_results_assignment_v1',
                'handoff_ref': v.context.scope['subject_refs'][0],
                'selector': {'path': str(v.directory / 'controlled-result-workspace' /
                    'controlled-empty-results.txt'), 'offset': 0, 'limit': 4}}
            request = v.runtime._plain(v.context.request)
            request['message']['episode_assignment'] = assignment
            context = replace(v.context, role=role, path=path, episode_id=episode_id,
                assignment=assignment, request=request)
            v.journal.save('runtime_episodes', {'episode_id': episode_id,
                'path': v.runtime._json(path), 'request': v.runtime._json(request),
                'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})
            binding = v.registry.for_path(path)
            target = {'resource_kind': 'local', 'assignment': {
                'workspace': str(v.directory / 'controlled-result-workspace'), 'requested_job': {}}}
            monkeypatch.setattr(binding, '_target', lambda *_: deepcopy(target))
            monkeypatch.setattr(binding, '_received', lambda *_args, **_kwargs:
                ({'known_record_refs': [], 'initial_known_record_refs': []}, {}, {}))
        assert binding.binding_path == self.binding_path
        v.contexts[context.episode_id] = context
        f = self.task(v)
        selected_type = getattr(binding, 'decision_source_type', v.runtime.DecisionSource)
        phase = 'baseline' if selected_type is v.runtime.DecisionSource else 'connected'
        assert os.environ['GENE_DIRECT_TASK_PHASE'] == phase
        if phase == 'connected':
            assert selected_type.__module__ == binding.__module__.removesuffix('.episode') + '.task'
            assert selected_type.__name__ == ('LaunchTask' if role == 'launch' else 'ResultsTask')
        task = object.__new__(selected_type)
        task.__dict__.update(f.task.__dict__)
        task.__dict__.update(self.source(v, context).__dict__)
        f.task = task
        w = task.workflow
        w.decision_protocol = None
        w.native_event_information = None
        w.services = self.module('episode_services').WorkflowServices(w)
        def credit(source):
            assert source.episode_id == context.episode_id
            f.projections.append(source.episode_id)
            return binding.credit_view(context, None)
        w.source_credit_view = credit
        assert w.specialist(task) is binding
        return SimpleNamespace(v=v, f=f, task=task, workflow=w, binding=binding,
            context=context, role=role, phase=phase)
