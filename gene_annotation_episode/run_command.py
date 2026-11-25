"""The command-line entry of an episode run: ``run``, ``resume`` and ``report``, and the registration a run's caller
makes before it (``freeze-libraries``). ``cli.py`` calls these. A run starts with no proposed annotation: there is no
command that makes one.

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
    """The folder of the episode bound at ``binding_path``: the root episode's own folder, or the folders the path names
    below it, one folder per part of the path. Every folder under the root is an episode."""
    if binding_path == 'root':
        return ROOT
    return ROOT.joinpath(*binding_path.split('/'))


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
    # The estimate ledger is the runner's own (a ``ForecastYieldController`` is given it by the runner): it is offered to
    # every run, and an episode sees it only if it declares it.
    declared = sorted({name for binding in bindings for name in binding.services} | {'estimate_table'})
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


def freeze_libraries(store, *, source, continuation, tools, head=None):
    """The general run rule: a run reads frozen copies of its libraries, so a later edit of a published library cannot
    change a run that has started. For every head the run's ``continuation`` names (an episode directly under the root;
    or only ``head``, a binding path, when one is given), freeze that head's libraries from the published ``source`` into
    the directories the head's own settings name (the same file ``run`` takes, so the run reads exactly what was
    frozen), and give the selection a parent commissions that head with.

    The command names no axis (the owner, 2026-11-24: "The library freeze command should not specify axes"): a head is
    named by its binding path, as everywhere in a run. Each head's library module
    (``episode_support/configuration/<head>/process_options.py``) supplies ``freeze_selection`` with its own pieces, and
    the head itself says which option of its library it is (``AXIS`` of its ``messages/read_from_parent.py``, the option
    id its commissions must select), which is handed to that function unread.
    A head whose library module has no such function is reported as not frozen; it does not stop the others (this is a
    help to keep runs tidy, not a gate). Freezing an already frozen directory returns the snapshot that is there."""
    configuration = ROOT.parent / 'episode_support' / 'configuration'
    package = PACKAGE.rsplit('.', 1)[0] + '.episode_support.configuration'
    heads = sorted(path for path in continuation if '/' not in path and path != 'root')
    if head is not None:
        if head not in heads:
            raise ValueError('freeze_libraries_head_not_in_the_continuation:' + head)
        heads = [head]
    result = {}
    for name in heads:
        freeze = None
        if (configuration / name / 'process_options.py').is_file():
            freeze = getattr(importlib.import_module(f'{package}.{name}.process_options'), 'freeze_selection', None)
        if freeze is None:
            result[name] = {'frozen': False, 'reason': 'the_library_module_of_this_head_supplies_no_freeze_selection'}
            continue
        option = importlib.import_module('.'.join((PACKAGE, name, 'messages', 'read_from_parent'))).AXIS
        result[name] = {'frozen': True, **freeze(store, source=Path(source), settings=continuation[name], axis=option,
                                                 tools=list(tools))}
    return result


def read_json(path):
    return json.loads(Path(path).read_text())


__all__ = ['freeze_libraries', 'read_json', 'report', 'resume_run', 'run', 'subtree']
