# Initial-context test boundary review

013 core has 454 passes and one failure at the unchanged None-context call. 013 host is still running. No candidate source or test changes are made by this review.

Hashes establish byte equality and timing; they cannot alone establish intended API semantics. The observed production path supplies BindingContext. I infer that this ExecutionEpisodes test should use that same context, but do not claim an independently documented formal removal of None support. The separate PracticalResourceEpisodes implementation ignores context and its separate None-based test remains outside this proposal.

## Byte evidence

```json
{
  "gene_annotation_episode/execution_episodes.py": {
    "baseline": "960b05612d3e6c6c2a2207329ceae49a82fdc9b4ce6ab022b2c0d13986310aed",
    "production": "960b05612d3e6c6c2a2207329ceae49a82fdc9b4ce6ab022b2c0d13986310aed",
    "candidate": "07616795d85da790fcde11a5d762d9e58a0a47db5e1c0bdb6ad784fffbfbd53c",
    "013_before": "07616795d85da790fcde11a5d762d9e58a0a47db5e1c0bdb6ad784fffbfbd53c"
  },
  "gene_annotation_episode/episode_bindings.py": {
    "baseline": "dd4994560e96aa84aa45c8fee160670f22930af7d7dbc82ecd30965fcf5ea50d",
    "production": "dd4994560e96aa84aa45c8fee160670f22930af7d7dbc82ecd30965fcf5ea50d",
    "candidate": "dd4994560e96aa84aa45c8fee160670f22930af7d7dbc82ecd30965fcf5ea50d",
    "013_before": "dd4994560e96aa84aa45c8fee160670f22930af7d7dbc82ecd30965fcf5ea50d"
  },
  "gene_annotation_episode/runtime.py": {
    "baseline": "f15783d6068cfda5adbb3a52e91efdf7dd94b85dd7e59e335303218ae3d8cc04",
    "production": "f15783d6068cfda5adbb3a52e91efdf7dd94b85dd7e59e335303218ae3d8cc04",
    "candidate": "f15783d6068cfda5adbb3a52e91efdf7dd94b85dd7e59e335303218ae3d8cc04",
    "013_before": "f15783d6068cfda5adbb3a52e91efdf7dd94b85dd7e59e335303218ae3d8cc04"
  },
  "gene_annotation_episode/practical_resource_episodes.py": {
    "baseline": "484b563a17377c62166878a15c24aa78d84a032e1b7a9e58120366356927da89",
    "production": "484b563a17377c62166878a15c24aa78d84a032e1b7a9e58120366356927da89",
    "candidate": "484b563a17377c62166878a15c24aa78d84a032e1b7a9e58120366356927da89",
    "013_before": "484b563a17377c62166878a15c24aa78d84a032e1b7a9e58120366356927da89"
  },
  "tests/test_execution_episodes_family.py": {
    "baseline": "708b3caaa0f7dcf5139ef975621bbdce8ea593f372604a5e21c94a1a937b3f1f",
    "production": "708b3caaa0f7dcf5139ef975621bbdce8ea593f372604a5e21c94a1a937b3f1f",
    "candidate": "708b3caaa0f7dcf5139ef975621bbdce8ea593f372604a5e21c94a1a937b3f1f",
    "013_before": "708b3caaa0f7dcf5139ef975621bbdce8ea593f372604a5e21c94a1a937b3f1f"
  },
  "tests/test_practical_reconstruction.py": {
    "baseline": "96aaad76342e1906974b507dba885a74d731e678c1d244b28c595c079c3d1aab",
    "production": "96aaad76342e1906974b507dba885a74d731e678c1d244b28c595c079c3d1aab",
    "candidate": "96aaad76342e1906974b507dba885a74d731e678c1d244b28c595c079c3d1aab",
    "013_before": "96aaad76342e1906974b507dba885a74d731e678c1d244b28c595c079c3d1aab"
  }
}
```

## tests/test_execution_episodes_family.py :: test_one_owner_and_data_descriptor_reconstruct_all_operands

```python
def test_one_owner_and_data_descriptor_reconstruct_all_operands(host):
    h = host
    registry = EpisodeBindingRegistry([h.family])
    assert registry.roles == ('launch', 'launch_api', 'launch_local', 'launch_hpc', 'results')
    assert registry.entry_roles == ('launch', 'results')
    record = h.family.as_record()
    assert record['binding_id'] == 'execution_episodes'
    restored = ExecutionEpisodes(None, store=h.store, directory=h.tmp_path/'restored',
        run_id=h.journal.run_id, tool_registry=h.family.tool_registry, **record['configuration'])
    assert restored.as_record() == record
    assert restored.api_execution is None
    assert h.family.initial_decision_context(None)['execution_resource_capabilities'][0] == {
        'resource_id': 'here', 'resource_kind': 'local', 'workspace': str(h.workspace),
        'availability': 'unknown', 'tool_names': h.family.capabilities()[0]['tool_names'],
        'policy': h.family.resources['here']['policy'], 'inventory_snapshot': None}
    with pytest.raises(ValueError, match='duplicate_episode_role'):
        registry.register(restored)
```

## tests/test_execution_episodes_family.py :: context

```python
def context(h, role, assignment, episode_id, *, path=None):
    path = path or ((role, episode_id),)
    request = {'message': {'scope': h.scope, 'episode_assignment': deepcopy(assignment)}}
    value = BindingContext(h.journal.run_id, episode_id, role, path, h.scope, assignment, request)
    with h.store.transaction():
        h.journal.save('runtime_episodes', {'episode_id': episode_id, 'path': canonical(path),
            'request': canonical(request), 'initial_credit': 0, 'state': 'running'})
    return value
```

## gene_annotation_episode/execution_episodes.py :: initial_decision_context

```python
def initial_decision_context(self, context):
        value = {'execution_resource_capabilities': [self._resource_information(key) for key in self.resources],
            'execution_initial_information': deepcopy(self.initial_information),
            'received_bvbrc_values': [] if self.api_execution is None else
                self.api_execution.received_bvbrc_context(context)}
        if self._forwards_minhash_reports(context.role):
            value['received_minhash_values'] = self.api_execution.minhash.received_context(context)
        return value
```

## gene_annotation_episode/execution_episodes.py :: _forwards_minhash_reports

```python
def _forwards_minhash_reports(self, role):
        return (role in {'annotation', 'scientific_process'} and self.api_execution is not None
            and any(service.service == 'bvbrc_minhash' for service in self.api_execution.services.values()))
```

## gene_annotation_episode/execution_episodes.py :: execute

```python
async def execute(self, context, tool_name, arguments, operation_key):
        if context.role in ROLE_KINDS:
            self._check_parent_inputs(context)
            return await self._delegate(context).execute(context, tool_name, arguments, operation_key)
        try:
            catalog = {entry['name']: entry for entry in self.catalog(context)}
            if tool_name not in catalog:
                raise ValueError('execution_operation_not_available')
            arguments = checked(arguments, catalog[tool_name]['input_schema'], 'invalid_execution_operation_arguments')
            if context.role == 'launch':
                return _outcome(self.initial_decision_context(context))
            target = self._target(context)
            if target['resource_kind'] == 'api':
                return await self.api_execution.execute(context, tool_name, arguments, operation_key)
            if is_native_hmmer_target(target):
                return await self.native_hmmer_results.execute(context, target, tool_name, arguments, operation_key)
            return await self._execute_native_results(context, target, tool_name, arguments, operation_key)
        except (ValueError, TypeError) as error:
            return _outcome(code=str(error))
```

## gene_annotation_episode/episode_bindings.py :: initial_decision_context

```python
def initial_decision_context(self, context):
        """Already recorded caller information before an episode's first choice."""
        supplied = {}
        for binding in self._bindings:
            callback = getattr(binding, 'initial_decision_context', None)
            if callback is None:
                continue
            value = callback(context)
            if not isinstance(value, Mapping) or set(value).intersection(supplied):
                raise ValueError('initial_binding_context_field_conflict')
            supplied.update(_plain(value))
        return supplied
```

## gene_annotation_episode/runtime.py :: binding_context

```python
def binding_context(self, source):
        return BindingContext(self.run_id, source.episode_id, source.path[-1][0],
            source.path, source.scope,
            source.request.message.as_record().get('episode_assignment', {}),
            source.request.as_record(), received_record_refs=(
                tuple(self.receipts.known(source.episode_id)) if self.receipts is not None else ()))
```

## gene_annotation_episode/runtime.py :: call

```python
async def call(self, context, schema):
        index, self.calls = self.calls, self.calls + 1
        journal = self.workflow.journal
        row = journal.row("runtime_model_calls", self.episode_id, index)
        if row:
            saved = json.loads(row["request"])
            if row["purpose"] != "decision":
                raise WorkflowError("saved decision contract differs from reconstruction")
            # Historical and interrupted decisions retain the actual contract
            # supplied at dispatch. Additions to today's tool catalog belong to
            # new decisions, not retrospective reconstruction of earlier ones.
            schema = saved["schema"]
            context = saved["context"]
            if (self.workflow.decision_protocol == DECISION_EXCHANGE_PROTOCOL
                    and saved.get('decision_protocol') != DECISION_EXCHANGE_PROTOCOL):
                raise WorkflowError('pending_decision_requires_original_protocol')
            if row["response"] is not None:
                if self.workflow.decision_protocol == DECISION_EXCHANGE_PROTOCOL:
                    context = self.interpretation_context(context,
                        self.workflow.decision_exchanges.rows(self.episode_id, index))
                return json.loads(row["response"]), index, context, schema
        else:
            # Selected manuals are exact immutable assignment operands. Supply
            # their bodies only to new calls; saved calls above keep the context
            # originally dispatched, including an interrupted request.
            context = {**context,
                'launch_instruction_library': self.workflow.launch_instructions.context()}
            selected_instructions = self.workflow.launch_instructions.materialize(
                self.request.message.as_record().get('episode_assignment', {}).get('launch_instructions'))
            if selected_instructions is not None:
                context['selected_launch_instructions'] = selected_instructions
            if self.workflow.available_child_roles(self):
                context['child_options'] = child_option_information(self.workflow, self)['text']
            supplied_initial = self.workflow.episode_bindings.initial_decision_context(
                self.workflow.binding_context(self))
            if set(supplied_initial).intersection(context):
                raise ValueError('initial_binding_context_field_conflict')
            context = {**context, **supplied_initial}
            if 'pending_work' not in context:
                # Direct caller dispatches need the same authoritative
                # outstanding-work input as next(). Saved decisions above
                # retain the exact original context instead.
                context = {**context, 'pending_work': self.workflow.pending_work(self)}
            binding = self.workflow.execution_expectations
            if binding is not None and binding.applies(self.path[-1][0]):
                planning_scopes = ()
                if (self.path[-1][0] in binding.planning_roles
                        and self.workflow.job_episodes is not None):
                    jobs = self.workflow.job_episodes
                    if 'search_modes' in jobs.jobs.config:
                        options = jobs.prospective_execution_options(self.workflow.store, self.scope)
                        planning_scopes = list({value['execution_class'].ref: value['execution_class']
                                                for value in options}.values())
                        context = {**context, 'job_execution_options': [
                            {key: value[key] for key in ('query_ref', 'cpu', 'search_mode')}
                            | {'execution_class_ref': value['execution_class'].ref}
                            for value in options]}
                    else:
                        planning_scopes = jobs.prospective_execution_classes(self.workflow.store, self.scope)
                context = {**context, "execution_expectations": binding.capture(self.path[-1][0],
                    assignment=self.request.message.as_record().get("job_assignment"),
                    planning_scopes=planning_scopes)}
            if self.workflow.resource_estimator is not None:
                if self.workflow.is_job_source(self):
                    estimates = self.workflow.resource_estimator.estimate(
                        context.get("execution_expectations"),
                        job_ref=self.workflow.job_episodes.assignment(self)["job_ref"],
                        sample=self.workflow.job_episodes.latest_sample(self, include_inherited=True))
                elif "execution_expectations" in context:
                    # Supply expected execution costs before the owning episode
                    # chooses work. These classes describe proposed execution.
                    estimates = self.workflow.resource_estimator.estimate_context(
                        context["execution_expectations"])
                else:
                    estimates = None
                if estimates is not None:
                    context = {**context, "resource_tool_estimates": estimates}
            native_expectations = self.workflow.native_estimation_context(self, context)
            if native_expectations is not None:
                context = {**context, 'native_execution_expectations': native_expectations}
                if self.workflow.resource_estimator is not None:
                    native_estimates = self.workflow.resource_estimator.estimate_context(native_expectations)
                    context['resource_tool_estimates'] = [*context.get('resource_tool_estimates', []), *native_estimates]
            if self.workflow.native_event_information is not None:
                context['native_event_targets'] = self.workflow.native_event_information.read(
                    self.workflow.binding_context(self))
            if self.workflow.permits_common_action(self, 'wait'):
                context['waiting_support'] = self.workflow.waiting_support(self, context)
            saved = {"context": context, "schema": schema}
        if self.workflow.decision_protocol == DECISION_EXCHANGE_PROTOCOL:
            if row is None:
                saved = {**saved, 'decision_protocol': DECISION_EXCHANGE_PROTOCOL}
                if (self.workflow.receipts is not None and not self.workflow.is_job_source(self)
                        and not self.workflow.receipt_projection(self)):
                    self.workflow.receipts.receive(self.episode_id, context['visible_record_refs'],
                        kind='decision_input', source_index=index)
                journal.save('runtime_model_calls', {'episode_id': self.episode_id,
                    'call_index': index, 'purpose': 'decision', 'request': _json(saved), 'response': None})
            return await self.exchange_decision(context, schema, index, saved)
        has_session = getattr(self.workflow.provider, "has_session", lambda *_: False)
        if (not has_session(self.episode_id, "REASONING")
                and "restored_episode_history" not in context):
            # Restore the authoritative scientific/runtime state through the
            # existing replay path, not by rehydrating all archived contexts.
            # The fresh native conversation receives only a bounded metadata
            # index; exact older selections/outcomes are an ordinary own read.
            context = {**context, "restored_episode_history":
                self.workflow.history_preview(self, before=index)}
        context = instructional_model_context(context)
        # Save the exact supplied context, including its bounded operational
        # index, before dispatch. Completed historical calls are returned above
        # unchanged. Metadata contains no old contexts, so it cannot nest them.
        saved = {"context": context, "schema": schema}
        if (self.workflow.receipts is not None and not self.workflow.is_job_source(self)
                and not self.workflow.receipt_projection(self)):
            # A caller may use a different scalar for this parent while using
            # receipt-based credit in its children. Preserve what this actual
            # automatic input delivered so those children inherit it correctly.
            self.workflow.receipts.receive(self.episode_id, context['visible_record_refs'],
                kind='decision_input', source_index=index)
        journal.save("runtime_model_calls", {"episode_id": self.episode_id,
            "call_index": index, "purpose": "decision", "request": _json(saved), "response": None})
        with journal.measure("runtime_model_calls", self.episode_id, index):
            instructions = self.instructions(context)
            response = await self.workflow.provider.complete(self.episode_id, "REASONING", instructions,
                                                              context, _action_generation_schema(schema))
        journal.save("runtime_model_calls", {"episode_id": self.episode_id,
            "call_index": index, "purpose": "decision", "request": _json(saved), "response": _json(response)})
        return response, index, saved["context"], schema
```

## gene_annotation_episode/practical_resource_episodes.py :: initial_decision_context

```python
def initial_decision_context(self, context):
        return {'practical_resource_information': deepcopy(self.initial_information),
                'practical_resource_capabilities': [self._resource_information(kind)
                    for kind in self.resources]}
```

## tests/test_practical_reconstruction.py :: test_resource_information_precedes_selection_and_survives_reconstruction

```python
"""Practical caller reconstruction freezes configuration without doing work."""
import asyncio
from copy import deepcopy
import json

import pytest

from gene_annotation_episode import independent_execution as reconstruction
from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
from gene_annotation_episode.practical_service_setup import PracticalServiceFactory
from gene_annotation_episode.practical_resource_episodes import PracticalResourceEpisodes
from gene_annotation_episode.providers import ModelConnection
from gene_annotation_episode.runtime import assemble_workflow, run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_configuration import build_tools


class BeforeModel(Exception):
    pass


def test_factory_keeps_caller_configuration_immutable(tmp_path):
    resources = {'local': {'kind': 'local', 'workspace': str(tmp_path), 'policy': {
        'memory_bytes': 123, 'scratch_bytes': 456, 'wall_seconds': None}}}
    factory = PracticalServiceFactory(resources, {})
    original = factory.as_record()
    resources['local']['workspace'] = '/changed'
    assert factory.as_record() == original
    with pytest.raises(TypeError):
        factory.resources['local']['workspace'] = '/changed'
    binding = PracticalResourceEpisodes(None, directory=tmp_path,
        resources=factory.resources, initial_information=factory.initial_information)
    information = binding.initial_decision_context(None)['practical_resource_capabilities']
    assert information == [{'resource_kind': 'local', 'workspace': str(tmp_path),
        'policy': original['resources']['local']['policy'], 'inventory_snapshot': None}]


def test_configured_practical_services_reconstruct_without_discovery_or_commands(tmp_path, monkeypatch):
    directory = tmp_path/'run'
    resources = {'local': {'kind': 'local', 'workspace': str(tmp_path/'project'),
        'policy': {'memory_bytes': 128*1024**2, 'scratch_bytes': 16*1024**2, 'wall_seconds': None}}}
    factory = PracticalServiceFactory(resources, {})

    def forbidden(*args, **kwargs):
        pytest.fail('Reconstruction must not discover resources or execute an operation')

    monkeypatch.setattr(LocalPracticalOperations, 'initial_outcome', forbidden)
    monkeypatch.setattr(LocalPracticalOperations, 'execute', forbidden)

    async def inspect_before_model(connection):
        with Store(workspace) as reopened:
            binding = json.loads((directory/'episode-execution-binding.json').read_text())
            settings = json.loads(reopened.db.execute('SELECT settings FROM runtime_runs').fetchone()[0])
            options = reconstruction._standard_bindings(reopened, directory, settings)
            reconstruction._check_bindings(options, settings)
            assert options['episode_service_factory'].as_record() == factory.as_record()
            assert binding == reconstruction.make_runtime_binding(reopened, directory)
            restored = assemble_workflow(reopened, build_tools(reopened), object(), directory,
                json.loads((directory/'run.json').read_text())['run_id'], settings,
                **{key: value for key, value in options.items() if key != 'binding_definitions'})
            assert restored.episode_bindings.as_record() == settings['episode_bindings']
            assert set(restored.episode_bindings.roles) == {'launch_local'}
            assert reopened.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0] == 0
            assert not (directory/'practical-execution').exists()
            assert not (tmp_path/'project').exists()
            altered = deepcopy(settings)
            altered['episode_application_services']['factory'] = 'unknown.Factory'
            with pytest.raises(Exception) as error:
                reconstruction._standard_bindings(reopened, directory, altered)
            assert error.value.failure['code'] == 'unavailable_binding'
        raise BeforeModel

    monkeypatch.setattr(ModelConnection, '__aenter__', inspect_before_model)
    workspace = tmp_path/'state'
    with Store(workspace) as store:
        store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')
        with pytest.raises(BeforeModel):
            asyncio.run(run_workflow(store, build_tools(store), run_dir=directory,
                episode_service_factory=factory, episode_service_binding=factory.as_record()))

```

## Exact method comparison

Production and candidate extracted method bytes are identical: SHA256 `afdadac512f36851465deb40c5a480feb6fdc24f43b3918667f564c59e93bd72`. Production whole-file hash also matches the original baseline in the byte evidence above.

## Proposed prospective test-only correction

After 013 host exits naturally, replace the sole `initial_decision_context(None)` call in this ExecutionEpisodes test with a call using:

```python
launch = context(h, "launch",
    launch_assignment({"here": native_assignment(h.workspace)}), "descriptor-launch")
```

Then call `initial_decision_context(launch)` and preserve every existing expected field and assertion. This uses the existing fixture constructor, immutable BindingContext, explicit selected resource/job assignment, and actual runtime episode record. It submits nothing. The complete execution_episodes_family group would be rerun with fresh before/after hashes, preserving 013. No runtime or production source correction is proposed.
