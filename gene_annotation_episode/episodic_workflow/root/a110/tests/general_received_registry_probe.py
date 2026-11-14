"""Required A110 full/partial receiving boundary diagnostic.

Baseline preserves actual failures rather than replacing validators. Connected
checks require the explicitly configured recipient path to agree with the
retained original callback, including invalid outcomes. RNA fixture ports are
the separately reviewed reservation/observation/pure-worker ports only.
"""
from __future__ import annotations
import argparse
import ast
from copy import deepcopy
from dataclasses import replace
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
import traceback

AXIS = 'a110'
PREFIX = 'gene_annotation_episode.episodic_workflow.root.' + AXIS + '.'
CALLBACKS = ('received_report_sources', 'received_report_facts', 'received_report_closure_facts',
    'resolve_received_reference', 'validate_received_report', 'received_form_references')


def module(name):
    return importlib.import_module(PREFIX + name.replace('/', '.'))


def originals():
    path = Path(__file__).parent / 'fixtures/general_received_readers/original_callbacks.py'
    tree = ast.parse(path.read_text())
    assert [node.name for node in tree.body if isinstance(node, ast.FunctionDef)] == list(CALLBACKS)
    namespace = {'deepcopy': deepcopy, 'plain': module('communication').plain}
    if AXIS == 'a107':
        namespace['BLAST_GRADED_RETURN_SOURCE'] = module('a107_blast_execution').BLAST_GRADED_RETURN_SOURCE
    exec(compile(tree, str(path), 'exec'), namespace)
    return {name: namespace[name] for name in CALLBACKS}


def observe(callback):
    try:
        return {'status': 'returned', 'value': module('communication').plain(callback())}
    except Exception as error:
        return {'status': 'raised', 'type': type(error).__module__ + '.' + type(error).__qualname__,
            'message': str(error), 'traceback': traceback.format_exc()}


def comparable(row):
    return {key: value for key, value in row.items() if key != 'traceback'}


def attach(registry, factory, owner, *, connected):
    if not connected: return None
    configuration = module('library/received_execution_information/received_configuration').ReceivedExecutionConfiguration.original_global_factory(factory)
    catalog = configuration.construct(store=owner.store, run_id=owner.run_id, directory=owner.directory,
        tool_registry=owner.tool_registry, services=owner.services)
    callback = module('annotation_received_execution_information').received_execution_information
    registry.configure_received_execution_information(catalog, callback)
    return catalog


def context_boundaries(directory, *, partial, connected):
    fixture = module('tests/test_information_connected')
    case = fixture.InformationCase(directory, partial=partial, connect=False)
    try:
        assert len(case.hpc_initialization) == 4
        assert all(row['outcome']['status'] == 'completed' and row['native_or_provider_operations'] == 0
            for row in case.hpc_initialization)
        catalog = attach(case.registry, case.factory, case.owner, connected=connected)
        original = originals()
        observations = []
        for context in case.contexts:
            schema = {'type': 'object', 'properties': {}, 'additionalProperties': False}
            operations = {
                'received_report_sources': ((context.role,), lambda: case.registry.received_report_sources(context.role, path=context.path)),
                'received_report_facts': ((context,), lambda: case.registry.received_report_facts(context)),
                'received_report_closure_facts': ((context,), lambda: case.registry._received_report_mapping('received_report_closure_facts', context)),
                'resolve_received_reference': ((context, 'source_nonexistent_receiving_probe', 'source'),
                    lambda: case.registry.resolve_received_reference(context, 'source_nonexistent_receiving_probe', 'source')),
                'validate_received_report': ((context, {}, schema), lambda: case.registry.validate_received_report(context, {}, schema)),
                'received_form_references': ((context, {}, schema, 'empty-schema-diagnostic:' + context.episode_id),
                    lambda: case.registry.received_form_references(context, {}, schema, 'empty-schema-diagnostic:' + context.episode_id)),
            }
            for name, (arguments, current) in operations.items():
                expected = observe(lambda name=name, arguments=arguments: original[name](case.owner, *arguments))
                actual = observe(current)
                row = {'context': context.as_record(), 'boundary': name,
                    'expected_current_original': expected, 'registry': actual}
                if catalog is not None:
                    reader = catalog.received('@original-global-recipient', context)
                    direct = observe(lambda name=name, arguments=arguments: getattr(reader, name)(*arguments))
                    row['dedicated_reader'] = direct
                    assert comparable(direct) == comparable(expected), row
                    assert comparable(actual) == comparable(expected), row
                observations.append(row)
        return {'binding_count': len(case.bindings), 'context_count': len(case.contexts),
            'partial': partial, 'connected': connected, 'observations': observations,
            'fixture_initialization': getattr(case, 'hpc_initialization', None),
            'factory_definition': case.factory.as_record(),
            'authority_record': None if catalog is None else catalog.as_record()}
    finally:
        case.close()


def registry_for_received(case, *, partial):
    """Real 43/31 A107 bindings share the genuine received fixture Store/run.

    HPC readers use the actual required recorded Aurora configuration. Their
    ledgers are not accessed by these RNA receiving paths; no fake directory or
    initialized-state substitute is introduced.
    """
    from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import resources, commission
    information = module('tests/test_information_connected')
    owner = case.owner
    library = SimpleNamespace(as_record=lambda: {}, headers=lambda: [])
    science = module('scientific_process/episode').ScientificProcessEpisode(owner.services,
        library=library, tool_library=library,
        child_roles=('scientific_process', 'hpc', 'launch', 'results', 'monitor', 'literature'))
    bindings = [science]
    for parent in ('hpc_work_planning', 'scientific_process/hpc_work_planning'):
        for child in ('', '/hpc_allocation_execution', '/hpc_resource_prediction'):
            bindings.append(module(parent + child + '/episode').HPCEpisode(owner.services,
                store=owner.store, run_id=owner.run_id, directory=owner.directory,
                resources=resources(), commissions={'commission': commission()}))
    for parent in information.PARENTS[2:] if partial else information.PARENTS:
        prefix = parent + '/' if parent else ''
        leaves = ('execution_job_submission', 'execution_job_submission/api_job_execution',
            'execution_job_submission/local_job_execution', 'execution_job_submission/hpc_job_execution',
            'execution_result_acquisition')
        for leaf in leaves:
            bindings.append(module(prefix + leaf + '/episode').ExecutionEpisode(owner.services,
                store=owner.store, run_id=owner.run_id, directory=owner.directory,
                tool_registry=owner.tool_registry,
                **{key: deepcopy(getattr(owner, key)) for key in ('resources', 'initial_information',
                    'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles')}))
        bindings.append(module(prefix + 'execution_progress_assessment/episode').MonitorEpisode(owner.services))
    assert len(bindings) == (31 if partial else 43)
    return module('episode_bindings').EpisodeBindingRegistry(bindings), bindings


def nonempty_rna(directory, *, partial, connected):
    assert AXIS == 'a107'
    fixture = module('tests/test_information_rna_custody')
    iterator = fixture.build_received(directory, connected=False)
    case = next(iterator)
    try:
        preflight = json.loads((directory / 'actual-current-preflight/preflight-rejection.json').read_text())
        assert preflight['actual_current_preflight'] and preflight['controlled_producer_port_installed'] is False
        assert preflight['failure']['cause'] == 'native_request_exceeds_environment_bounds'
        provenance_path, = case.fixture.native_root.rglob('controlled-reservation-provenance.json')
        provenance = json.loads(provenance_path.read_text())
        assert provenance['genuine_native_producer'] is False and provenance['current_resource_authorization'] is False
        # This is the actual original factory object retained by the suspended
        # required fixture, not a configuration inferred from callback values
        # or copied owner fields. Product code never introspects this frame.
        factory = iterator.gi_frame.f_locals['factory']
        assert type(factory) is module('execution_service_setup').ExecutionServiceFactory
        registry, bindings = registry_for_received(case, partial=partial)
        catalog = attach(registry, factory, case.owner, connected=connected)
        original = originals()
        observations = []
        for context in (case.science, case.fixture.root):
            expected = observe(lambda: original['received_report_facts'](case.owner, context))
            actual = observe(lambda: registry.received_report_facts(context))
            assert expected['status'] == 'returned'
            native = module('rna_structure_result_views')
            comparison = module('rna_structure_comparison_views')
            assert expected['value'][native.FAMILY_SOURCES['summary']]
            assert expected['value'][comparison.PROJECTION_SOURCE]
            sources = observe(lambda: registry.received_report_sources(context.role, path=context.path))
            expected_sources = observe(lambda: original['received_report_sources'](case.owner, context.role))
            references = []
            for reference in expected['value'][native.REFERENCE_SOURCE]:
                references.append({'reference': reference,
                    'expected': observe(lambda reference=reference: original['resolve_received_reference'](case.owner, context, reference, 'execution_result')),
                    'registry': observe(lambda reference=reference: registry.resolve_received_reference(context, reference, 'execution_result'))})
            if connected:
                assert comparable(actual) == comparable(expected)
                assert comparable(sources) == comparable(expected_sources)
                for row in references:
                    assert comparable(row['registry']) == comparable(row['expected'])
            observations.append({'context': context.as_record(), 'expected': expected, 'registry': actual,
                'source_declarations': sources, 'reference_resolution': references})
        child, parent = case.child, case.science
        row = case.fixture.store.db.execute('SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?',
            (case.fixture.run_id, child.episode_id)).fetchone()
        saved_form = json.loads(row['form'])
        schema = module('communication').plain(child.request)['report_contract']['measurements']['schema']
        index = int(child.path[-1][1].removeprefix('child_'))
        key = f'{case.fixture.run_id}:{parent.episode_id}:{index}:typed_form'
        before = list(case.fixture.store.db.iterdump())
        expected_replay = observe(lambda: original['received_form_references'](case.owner, parent, saved_form, schema, key))
        first = observe(lambda: registry.received_form_references(parent, saved_form, schema, key))
        after_first = list(case.fixture.store.db.iterdump())
        second = observe(lambda: registry.received_form_references(parent, saved_form, schema, key))
        after_second = list(case.fixture.store.db.iterdump())
        if connected:
            assert comparable(first) == comparable(expected_replay) == comparable(second)
            assert before == after_first == after_second
        changed = deepcopy(saved_form)
        field = next(iter(changed))
        assert changed[field]
        changed[field] = []
        case.fixture.store.db.execute('UPDATE runtime_forms SET form=? WHERE run_id=? AND episode_id=?',
            (json.dumps(changed), case.fixture.run_id, child.episode_id))
        try:
            expected_denial = observe(lambda: original['received_report_facts'](case.owner, parent))
            actual_denial = observe(lambda: registry.received_report_facts(parent))
        finally:
            case.fixture.store.db.execute('UPDATE runtime_forms SET form=? WHERE run_id=? AND episode_id=?',
                (row['form'], case.fixture.run_id, child.episode_id))
        assert expected_denial['status'] == 'raised' and 'frozen_form_conflict' in expected_denial['message']
        if connected: assert comparable(actual_denial) == comparable(expected_denial)
        return {'partial': partial, 'binding_count': len(bindings), 'observations': observations,
            'factory_definition': factory.as_record(),
            'admission_replay': {'original_operation_key': key, 'expected': expected_replay,
                'first': first, 'second': second, 'rows_unchanged': before == after_first == after_second},
            'frozen_form_denial': {'expected': expected_denial, 'registry': actual_denial},
            'controlled_ports': ['Explicit synthetic reservation for historical 20-GiB saved producer data',
                'Synthetic native bundle and target observation', 'Exact pure grading function through controlled worker process port'],
            'actual_boundaries': ['Store', 'Journal', 'BindingContext', '43/31 registry bindings',
                'Original NativeJobHandle and RNA plan reads', 'Typed frozen reports and admission records',
                'Received facts and reference authentication', 'Same-key admission replay'],
            'genuine_native_or_scientific_execution_claim': False,
            'current_preflight_rejection': preflight,
            'controlled_reservation_provenance': provenance}
    finally:
        iterator.close()


def run(directory, phase):
    directory.mkdir(parents=True, exist_ok=False)
    report = {'axis': AXIS, 'phase': phase, 'contexts': [], 'nonempty': [],
        'remaining_original_scientific_coverage': ['Other omitted historical native reader families',
            *(['A110 retained FBA nonempty report/reference/admission chain'] if AXIS == 'a110' else [])]}
    path = directory / 'received_registry_probe.json'
    def save(): path.write_text(json.dumps(report, indent=2) + '\n')
    try:
        for partial in (False, True):
            target = directory / ('partial' if partial else 'full')
            target.mkdir()
            report['contexts'].append(context_boundaries(target, partial=partial, connected=phase == 'connected'))
            save()
        if AXIS == 'a107':
            for partial in (False, True):
                target = directory / ('rna-partial' if partial else 'rna-full')
                target.mkdir()
                report['nonempty'].append(nonempty_rna(target, partial=partial, connected=phase == 'connected'))
                save()
    except Exception:
        report['failure'] = traceback.format_exc()
        save()
        raise
    report['finished'] = True
    save()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--phase', choices=('baseline', 'connected'), required=True)
    args = parser.parse_args()
    run(args.output, args.phase)
