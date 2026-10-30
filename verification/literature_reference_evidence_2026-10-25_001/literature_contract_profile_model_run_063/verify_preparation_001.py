"""No-model contract/import preflight for the exact released generation.

All scientific inputs stay opaque. Contract contexts are explicitly invented
metadata fixtures, with no Store, source publication, action or observation.
Each pin is inspected in a separate fresh process; original pins are read-only.
"""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
import hashlib
import importlib
import importlib.metadata
import importlib.util
import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
import tomllib
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
NEW = HERE / 'pin_001'
ACCEPTED = BASE / 'a105_contract_information_design_059/connected_stage_004/pin_010'
PROFILE = 'operation_contract_information_v1'


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def fingerprint(path):
    path = Path(path).resolve()
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)}


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def verify_pin(pin):
    if pin == NEW:
        manifest_path = pin / 'SOURCE_MANIFEST.json'
        rows = json.loads(manifest_path.read_bytes())['files']
        entries = {row['pin_relative_path']: {'bytes': row['size'], 'sha256': row['sha256']} for row in rows}
        assert len(rows) == len(entries) == 1432
    else:
        assert pin == ACCEPTED
        manifest_path = pin / 'PIN_MANIFEST.json'
        assert sha(manifest_path) == '0a4e66d11cbbf3149bdc0d5f3a9424b4efe20ee2231e0987ed833281cce62a6d'
        entries = json.loads(manifest_path.read_bytes())
        assert len(entries) == 1425
    for name, expected in entries.items():
        relative = Path(name)
        assert not relative.is_absolute() and '..' not in relative.parts
        path = (pin / name).resolve()
        assert path.is_relative_to(pin)
        assert {'bytes': path.stat().st_size, 'sha256': sha(path)} == expected, name
    actual = {str(p.relative_to(pin)) for p in pin.rglob('*') if p.is_file()}
    assert actual == {*entries, manifest_path.name}
    return entries


def install_pin(pin):
    repository = next(parent for parent in pin.parents if (parent / 'AGENTS.md').is_file())
    sys.path[:] = [str(pin), *[entry for entry in sys.path if entry and
        Path(entry).resolve() not in {repository, repository / 'tests', HERE, pin / 'runner'}]]
    sys.dont_write_bytecode = True
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'


def forbid_model():
    from gene_annotation_episode import providers
    calls, blocked = [], []
    def forbidden(*_args, **_kwargs):
        calls.append('forbidden_model_entrypoint')
        raise AssertionError('metadata_preflight_forbids_model_provider_entry')
    for cls in (providers.ModelConnection, providers._SessionConnection):
        for name in ('__init__', '__aenter__', 'complete', 'catalog'):
            setattr(cls, name, forbidden)
            blocked.append(cls.__name__ + '.' + name)
    for name in ('_rpc', '_send', '_read', '_session'):
        setattr(providers._SessionConnection, name, forbidden)
        blocked.append('_SessionConnection.' + name)
    return calls, blocked


def import_descriptor_modules(pin):
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes
    tree = ast.parse((pin / 'gene_annotation_episode/literature_episodes.py').read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'LiteratureEpisodes')
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == 'as_record')
    names = {'source_locations.py'}
    for node in ast.walk(method):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.endswith('.py'):
            names.add(node.value)
    for name in sorted(names):
        importlib.import_module('gene_annotation_episode.' + name[:-3])
    assert len(names) > 60
    return sorted(names)


def saved_exchange_probe(catalog, facts):
    """Use actual read validators over invented in-memory metadata records."""
    from gene_annotation_episode import runtime
    from gene_annotation_episode.composition_information import contract_metadata_catalog
    from gene_annotation_episode.decision_context import state_frame, model_snapshot
    from gene_annotation_episode.episode_contract_information import operation_contract_information
    object_schema = runtime._object
    branches = []
    for row in catalog:
        branch = object_schema({'kind': {'type': 'string', 'const': 'tool'},
            'tool': {'type': 'string', 'const': row['name']},
            'arguments': runtime._embedded_tool_schema(row['input_schema'])})
        branch['x-argument-transport'] = row['argument_transport']
        branches.append(branch)
    schema = object_schema({'selection': {'anyOf': branches}, 'report_update': object_schema({})})
    lookups = [object_schema({'view': {'type': 'string', 'const': 'child_options'},
        'role': {'type': ['string', 'null'], 'enum': [None, 'literature']}})]
    for row in contract_metadata_catalog():
        lookups.append(object_schema({'view': {'type': 'string', 'const': 'composition_information'},
            'operation': {'type': 'string', 'const': row['name']}, 'arguments': row['input_schema']}))
    selected = object_schema({'response_type': {'type': 'string', 'const': 'select_action'}, **schema['properties']})
    selected['required'] = ['response_type', *schema['required']]
    exchange = object_schema({'response': {'anyOf': [object_schema({
        'response_type': {'type': 'string', 'const': 'request_context'},
        'lookup': {'anyOf': lookups}}), selected]}})
    context = {'tools': catalog, 'contract_information_profile': PROFILE, 'action_yields': {}}
    record = {'version': PROFILE, 'permitted_child_roles': ['literature'],
        'fact_sources_by_role': {'literature': facts}, 'fact_sources_sha256': runtime._digest({'literature': facts}),
        'catalog_sha256': runtime._digest(catalog), 'action_schema_sha256': runtime._digest(schema),
        'exchange_schema': exchange, 'instructions': 'Explicitly invented metadata-only validation fixture; never dispatched.'}
    saved = {'context': context, 'schema': schema, 'contract_information': record}
    snapshot = model_snapshot(context, {})
    request = {'instructions': record['instructions'], 'output_schema': runtime._action_generation_schema(exchange),
        'restoration': {'snapshot': snapshot, 'pending_public_exchanges': []}, 'context': state_frame(snapshot)}
    query = {'response': {'response_type': 'request_context', 'lookup': {
        'view': 'composition_information', 'operation': 'episode.operation_contract',
        'arguments': {'operation': catalog[0]['name']}}}}
    reply = operation_contract_information(catalog=catalog, operation=catalog[0]['name'])
    rows = [{'exchange_index': 0, 'request': request, 'response_recorded': True,
             'response': query, 'lookup_result_recorded': True, 'lookup_result': reply}]
    workflow = runtime.Workflow.__new__(runtime.Workflow)
    workflow.decision_protocol = 'decision_exchange_v1'
    workflow.decision_exchanges = SimpleNamespace(rows=lambda *_: rows)
    source = runtime.DecisionSource.__new__(runtime.DecisionSource)
    source.workflow, source.episode_id = workflow, 'invented_metadata_fixture'
    source.validate_contract_exchange_history(saved, 0)
    original = deepcopy(rows)
    rows[0]['response']['response']['lookup']['arguments']['extra'] = 'malformed closed query'
    try:
        source.validate_contract_exchange_history(saved, 0)
    except runtime.WorkflowError as error:
        assert str(error) == 'original_contract_information_query_mismatch'
    else:
        raise AssertionError('forged_completed_contract_reply_after_invalid_query_accepted')
    rows[:] = deepcopy(original)
    rows[0]['lookup_result']['result']['meaning'] = 'substituted reply'
    try:
        source.validate_contract_exchange_history(saved, 0)
    except runtime.WorkflowError as error:
        assert str(error) == 'original_contract_information_reply_mismatch'
    else:
        raise AssertionError('substituted_reply_accepted')
    rows[:] = original
    source.validate_contract_exchange_history(saved, 0)
    return {'valid_saved_query_reply_accepted': True, 'invalid_query_completed_reply_rejected': True,
            'substituted_reply_rejected': True, 'restored_original_accepted': True,
            'fixture_scope': 'in-memory metadata only; no Store, journal, source, action, model or observation'}


def snapshot(pin):
    entries = verify_pin(pin)
    install_pin(pin)
    calls, blocked = forbid_model()
    if pin == NEW:
        runner_path = pin / 'runner/run_literature_source_job_062.py'
        spec = importlib.util.spec_from_file_location('metadata_only_pinned_runner', runner_path)
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        def forbidden(*_args, **_kwargs):
            raise AssertionError('scientific_input_or_workflow_entry_forbidden')
        for name in ('main', 'load_inputs', 'offline_check', 'live', 'register_inputs', 'custody_checks'):
            setattr(runner, name, forbidden)
        runner.configure_pin(pin)
        runner.verify_pin(pin)
    from gene_annotation_episode import runtime
    from gene_annotation_episode.communication import validate_closed_schema
    from gene_annotation_episode.composition_information import CONTRACT_ARGUMENT_TRANSPORT
    from gene_annotation_episode.domain import obj
    from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
    from gene_annotation_episode.episode_contract_information import (
        operation_contract_information, return_contract_information, expand_fact_form,
        validate_saved_fact_form, ContractInformationError)
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes, _population_catalog
    from gene_annotation_episode.schema_information_text import parse_schema_information, schema_fingerprint
    from method_loop.durable import DurableExecutionStore
    from method_loop.episode import Episode
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.independent_execution import open_commission
    from jsonschema import Draft202012Validator
    descriptor_modules = import_descriptor_modules(pin)
    # No scientific source identity is asserted. The service supplies no ordinary
    # tools; this fixture checks only all19 declared population contracts.
    service = SimpleNamespace(tool_catalog=lambda _scope: [])
    binding = LiteratureEpisodes(service, rate_population=True,
        reference_parent_sources=['source_' + 'a' * 24], contract_information_profile=PROFILE)
    context = BindingContext('metadata-fixture', 'metadata-fixture', 'literature',
        (('literature', 'metadata-fixture'),), {}, {}, {}, ())
    catalog = binding.catalog(context)
    assert len(catalog) == 19
    assert [{k: row[k] for k in ('name', 'description', 'input_schema')} for row in catalog] == _population_catalog()
    assert all(row['argument_transport'] == CONTRACT_ARGUMENT_TRANSPORT for row in catalog)
    facts = binding.fact_sources('literature')
    assert len(facts) == 18
    operations, returns = {}, {}
    for row in catalog:
        Draft202012Validator.check_schema(row['input_schema'])
        reply = operation_contract_information(catalog=catalog, operation=row['name'])
        assert reply['status'] == 'completed' and parse_schema_information(reply['result']['text']) == row['input_schema']
        assert reply['result']['meaning'] == row['description']
        operations[row['name']] = reply['result']
    for name, fact in facts.items():
        reply = return_contract_information(facts_by_role={'literature': facts},
            permitted_child_roles=['literature'], role='literature', source=name)
        exact = fact['report_schema']
        assert reply['status'] == 'completed' and parse_schema_information(reply['result']['text']) == exact
        interpretation = {'type': 'string', 'enum': ['unknown', 'qualified']}
        compact = obj({'chosen_numbers': {'$ref': 'episode-fact:' + name}, 'qualification': interpretation})
        literal = obj({'chosen_numbers': exact, 'qualification': interpretation})
        first = expand_fact_form(json.dumps(compact), child_role='literature',
            facts_by_role={'literature': facts}, permitted_child_roles=['literature'])
        second = expand_fact_form(json.dumps(literal), child_role='literature',
            facts_by_role={'literature': facts}, permitted_child_roles=['literature'])
        assert first['expanded_schema'] == second['expanded_schema'] == literal
        for submitted, result in ((compact, first), (literal, second)):
            validate_closed_schema(result['expanded_schema'])
            assert validate_saved_fact_form(child_role='literature', submitted_schema_json=json.dumps(submitted),
                expanded_schema=result['expanded_schema'], declaration=result['declaration']) == literal
        assert len(first['declaration']['fact_references']) == 1 and second['declaration']['fact_references'] == []
        returns[name] = {'reply': reply['result'], 'compact': compact, 'literal': literal,
                         'compact_result': first, 'literal_result': second}
    invalids = {
        'operation': operation_contract_information(catalog=catalog, operation='absent.operation'),
        'wrong_role': return_contract_information(facts_by_role={'literature': facts},
            permitted_child_roles=['literature'], role='annotation', source=next(iter(facts))),
        'source': return_contract_information(facts_by_role={'literature': facts},
            permitted_child_roles=['literature'], role='literature', source='absent_fact')}
    assert all(v['status'] == 'invalid' and not v['record_refs'] for v in invalids.values())
    registry = EpisodeBindingRegistry((binding,))
    assert registry.contract_information_configurations() == (PROFILE,)
    assert registry.contract_information_profile(context) == PROFILE
    descriptor = binding.as_record()
    restored = LiteratureEpisodes(service, **descriptor['configuration'])
    assert restored.as_record() == descriptor
    for protocol in (None, 'legacy'):
        try:
            runtime.Workflow.validate_contract_information_configuration(SimpleNamespace(decision_protocol=protocol), PROFILE)
        except ContractInformationError as error:
            assert error.code == 'contract_information_requires_pending_decision_protocol'
        else:
            raise AssertionError('incompatible_protocol_accepted')
    runtime.Workflow.validate_contract_information_configuration(SimpleNamespace(decision_protocol='decision_exchange_v1'), PROFILE)
    exchange_probe = saved_exchange_probe(catalog, facts)
    models, controller = runtime._effective_configuration()
    defaults = tomllib.loads((pin / 'gene_annotation_episode/defaults.toml').read_text())
    assert controller == {'cost': .001, 'window_size': 8, 'subsample_size': 4, 'uncertainty_alpha': .05}
    assert defaults['scientific_progress']['finding_unit'] == 1
    assert defaults['local_jobs'] == {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296}
    imported = []
    for name, module in sorted(sys.modules.items()):
        filename = getattr(module, '__file__', None)
        if filename and name.split('.')[0] in {'gene_annotation_episode', 'method_loop'}:
            path = Path(filename).resolve()
            assert path.is_relative_to(pin), (name, str(path))
            relative = str(path.relative_to(pin))
            assert relative in entries and sha(path) == entries[relative]['sha256']
            imported.append({'module': name, **fingerprint(path)})
    assert not calls
    verify_pin(pin)
    return {'scope': 'pure metadata/declared-contract contexts; zero source registration or model entry',
        'descriptor': descriptor, 'operations': operations, 'returns': returns, 'invalid_feedback': invalids,
        'saved_exchange_probe': exchange_probe, 'descriptor_modules_imported': descriptor_modules,
        'actual_project_imports': imported, 'disabled_model_entrypoints': blocked, 'attempted_model_entrypoints': calls,
        'models': {k: {n: models[k][n] for n in ('model', 'reasoning_effort')} for k in ('FAST', 'REASONING')},
        'controller': controller, 'scientific_progress': defaults['scientific_progress'],
        'restoration': runtime._effective_restoration_configuration(), 'local_jobs': defaults['local_jobs'],
        'project_classes': [inspect.getfile(v) for v in (Store, Episode, DurableExecutionStore, inspect.unwrap(open_commission))]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    assert args.snapshot is not None and args.output is not None
    pin, output = args.snapshot.resolve(), args.output.resolve()
    assert pin in {NEW, ACCEPTED} and output.is_relative_to(HERE) and not output.is_relative_to(NEW)
    result = snapshot(pin)
    save(output, result)
    print(json.dumps({'status': 'passed', 'pin': str(pin), 'operations': len(result['operations']),
        'returns': len(result['returns']), 'actual_project_imports': len(result['actual_project_imports']),
        'model_entries': len(result['attempted_model_entrypoints']), 'source_inputs_decoded': False}))


if __name__ == '__main__':
    main()
