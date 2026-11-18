"""Controlled context/descriptor operands; real own modules and Store, no native work."""
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
import json

PACKAGE = __package__.rsplit('.tests', 1)[0]
AXIS = PACKAGE.rsplit('.', 1)[1]
AXIS_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = AXIS_ROOT.parents[3]
CASES = json.loads((Path(__file__).parent / 'fixtures' / 'receiving_context_cases.json').read_text())
EXTERNAL = tuple(CASES['external'])


def own(name):
    return import_module(PACKAGE + '.' + name)


def canonical_type():
    return import_module('gene_annotation_episode.episodic_workflow.root.receiving_context').BindingContext


def operands(scope=None):
    role = 'sequence_homology_evidence'
    path = ((role, 'context-control'),)
    run_id = 'controlled-receiving-context'
    scope = {} if scope is None else scope
    assignment = {'context_control': ['original', {'qualified': False}]}
    return dict(run_id=run_id,
        episode_id=own('method_loop.identities').EpisodeRef(run_id, path).episode_id,
        role=role, path=path, scope=scope, assignment=assignment,
        request={'message': {'scope': scope, 'episode_assignment': assignment}},
        received_record_refs=('controlled-reference',))


def saved_context(store, context_type):
    store.create_problem(raw_sequence='MAAA', molecule='protein')
    values = operands(store.validate_scope())
    journal = own('episode_journal').Journal(store, values['run_id'])
    journal.save('runtime_episodes', dict(episode_id=values['episode_id'],
        path=json.dumps(values['path']), request=json.dumps(values['request']),
        initial_credit=0.0, state='active'))
    return context_type(**values), journal


def runtime_shell(context, journal, *, received=None):
    # The actual original Episode.identity is called by Workflow.resolver.
    # These are explicit read/guard ports, not a fake BindingContext or registry.
    tools = SimpleNamespace(retained_molecular_reference_access=lambda *a, **k: None)
    services = SimpleNamespace(protein_structure_reference_access=lambda *a, **k: None)
    bindings = own('episode_bindings').EpisodeBindingRegistry(())
    host = SimpleNamespace(run_id=context.run_id,
        context=SimpleNamespace(require_run_id=lambda: context.run_id),
        grains={context.role: SimpleNamespace(name=context.role)}, journal=journal,
        tools=tools, services=services, episode_bindings=bindings,
        scientific_provenance=None, native_event_information=None,
        progress_provider=None, initial_known_record_refs=(), store=journal.store)
    return host
