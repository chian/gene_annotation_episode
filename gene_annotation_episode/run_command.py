"""The command-line entry of an episode run: ``run``, ``resume`` and ``report``, and the two registrations a run's
caller makes before it (``propose-annotation``, ``freeze-libraries``). ``cli.py`` calls these.

Nothing here is episode code or recording code. ``run`` links the entry binding and every binding below it with
the four system collaborators (the workspace's ``Store``, the real ``ModelProvider``, the caller's continuation
settings and the real job services) and runs it to the end; the runner records everything in the run journal.
``resume`` replays a recorded run. ``report`` reads a run back from its journal. A wrong commission fails with its own
error."""
from __future__ import annotations

import asyncio
import importlib
import json
from pathlib import Path

from episode_runtime import BindingRegistry, EpisodeBinding, RunJournal, link, resume

from .model_provider import ModelProvider, load_config

ROOT = Path(__file__).resolve().parent / 'episodic_workflow' / 'root'
PACKAGE = 'gene_annotation_episode.episodic_workflow.root'


def _folder(binding_path):
    """The folder of the episode bound at ``binding_path``: the root episode's own folder, or the folder named by the
    path below the one axis folder that holds its first part."""
    if binding_path == 'root':
        return ROOT
    head, *rest = binding_path.split('/')
    (axis,) = [folder for folder in sorted(ROOT.iterdir()) if (folder / head / 'episode.py').is_file()]
    return axis.joinpath(head, *rest)


def _binding(binding_path):
    """The one binding instance of the episode at ``binding_path``."""
    relative = _folder(binding_path).relative_to(ROOT).parts
    module = importlib.import_module('.'.join((PACKAGE, *relative, 'episode')))
    (binding,) = [value for value in vars(module).values() if isinstance(value, type)
                  and issubclass(value, EpisodeBinding) and value.__module__ == module.__name__]
    return binding()


def subtree(entry_path):
    """The entry binding and every binding its child slots name, recursively. Nothing else is imported."""
    bindings, pending = {}, [entry_path]
    while pending:
        path = pending.pop()
        if path not in bindings:
            bindings[path] = _binding(path)
            pending.extend(bindings[path].child_slots.values())
    return list(bindings.values())


def _collaborators(store, bindings, *, continuation, services, model_calls):
    """The four system collaborators. A service an episode declares that the job services do not offer fails here."""
    from .episodic_workflow.episode_support.jobs.job_services import job_services
    offered = job_services(services)
    declared = sorted({name for binding in bindings for name in binding.services})
    return {'store': store,
            'model_provider': ModelProvider(load_config(), Path(model_calls), Path(model_calls).parent),
            'continuation': continuation, 'services': {name: offered[name] for name in declared}}


def _closed(journal, run_id, closed, journal_path, model_calls):
    episodes = journal.episodes(run_id)
    entry = episodes[0]
    return {'run_id': run_id, 'entry': closed['entry'], 'result': closed['result'].as_record(),
            'completion': entry['completion'], 'episodes': len(episodes), 'journal': str(journal_path),
            'model_calls': str(model_calls),
            'model_calls_made': len(list(Path(model_calls).glob('call-*')))}


def run(store, *, entry, commission, continuation, services, run_id, journal, model_calls):
    """Link ``entry`` with the caller's commission and run it to the end."""
    bindings = subtree(entry)
    record = RunJournal(journal)
    linked = link(BindingRegistry(bindings), entry, commission, run_id=run_id, journal=record,
                  collaborators=_collaborators(store, bindings, continuation=continuation, services=services,
                                               model_calls=model_calls))
    return _closed(record, run_id, asyncio.run(linked.run()), journal, model_calls)


def resume_run(store, *, continuation, services, run_id, journal, model_calls):
    """Replay the recorded run ``run_id``: recorded units and model calls are not made again."""
    record = RunJournal(journal)
    bindings = subtree(record.entry(run_id)['entry_path'])
    linked = resume(BindingRegistry(bindings), run_id=run_id, journal=record,
                    collaborators=_collaborators(store, bindings, continuation=continuation, services=services,
                                                 model_calls=model_calls))
    return _closed(record, run_id, asyncio.run(linked.run()), journal, model_calls)


def report(*, run_id, journal):
    """What the journal recorded of the run: each episode with its completion, its units in order (the tool or
    child, its arguments, its outcome), the model's answers and the yield controller's steps."""
    record = RunJournal(journal)
    episodes = []
    for episode in record.episodes(run_id):
        path = tuple(tuple(step) for step in episode['path'])
        episodes.append({
            'binding_path': episode['binding_path'], 'state': episode['state'], 'completion': episode['completion'],
            'units': [{'label': label, 'unit': unit} for label, _, unit, _ in record.units(run_id, path)],
            'model_answers': [call['response'] for call in record.model_calls(run_id, path)],
            'controller_steps': record.controller_steps(run_id, path),
            'ceilings': record.ceilings(run_id, path),
            'receipts': [{'ref': item['ref'], 'how': item['how']} for item in record.receipts(run_id, path)]})
    return {'run_id': run_id, 'run_state': record.run_state(run_id), 'failure': record.run_failure(run_id),
            'episodes': episodes}


def propose_annotation(store, *, subject, predicate, value):
    """Register the caller's proposed annotation of ``subject``: one hypothesis record of caller origin."""
    record = store.put('hypothesis', {'subject_refs': [subject], 'predicate': predicate, 'value': value,
                                      'context_refs': []}, origin='caller')
    return {'proposed_annotation_ref': record['id'], 'record': record}


def freeze_libraries(store, *, directory, source, axis, tools, tool_registry):
    """Freeze the process library (from its published ``source``) and the tool library (the named tools of the tool
    registry) into ``directory`` for a run, and give the selection of ``axis`` a parent commissions its head with:
    the axis option, the first thought pattern of the library and the tool information of the named tools."""
    from .episodic_workflow.episode_support.configuration.sequence_homology_evidence.process_options import (
        SequenceHomologyEvidenceLibrary)
    from .episodic_workflow.episode_support.records.sequence_homology_evidence.construction_records import (
        SELECTION_VERSION)
    from .episodic_workflow.episode_support.tools.sequence_homology_evidence.tools import ToolRegistry
    from .episodic_workflow.episode_support.tools.tool_catalog import ScientificToolLibrary
    directory = Path(directory)
    library = SequenceHomologyEvidenceLibrary.freeze(directory / 'process-library', source=source)
    thought = next(header['option_ref'] for header in library.headers()
                   if header['option_ref']['slot'] == 'thought_pattern')
    available = ToolRegistry(store, **tool_registry).catalog()
    catalog = [{'name': name, 'resources': 'local', **available[name]} for name in tools]
    tool_library = ScientificToolLibrary.freeze(directory / 'tool-library', catalog=catalog)
    information = tool_library.resolve_tool_info([{'name': name, 'resources': 'local'} for name in tools])
    return {'process_library_directory': str(library.directory), 'tool_library_directory': str(tool_library.directory),
            'selection': {'version': SELECTION_VERSION, 'evidence_axis': library.reference(axis),
                          'thought_pattern': thought, 'child_tool_info': information}}


def read_json(path):
    return json.loads(Path(path).read_text())


__all__ = ['freeze_libraries', 'propose_annotation', 'read_json', 'report', 'resume_run', 'run', 'subtree']
