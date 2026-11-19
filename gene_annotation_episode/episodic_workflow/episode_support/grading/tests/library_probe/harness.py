"""Run library functions through the real runner: a real Store, journal and model provider, the probe episode, and
the unit outcomes read back from the run journal."""
import asyncio

from episode_runtime import BindingRegistry, link
from episode_runtime.tests.probe_world import open_world
from gene_annotation_episode.episodic_workflow.episode_support.grading.tests.library_probe.episode import LibraryProbe

CONTINUATION = {'library_probe': {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}}}


def calls(*steps):
    """The plan of a run: each step names a test-side wrapper (``'module:name'``) and its keyword arguments."""
    return [{'function': function, 'keywords': keywords} for function, keywords in steps]


def run_plan(world, run_id, plan, held=()):
    """Run the plan with the records ``held`` passed in custody; the outcome of each plan step, in order."""
    entry = {'assignment': {'held_refs': list(held)}, 'message': {'plan': plan}, 'selection': []}
    collaborators = {'store': world['store'], 'model_provider': world['provider'], 'continuation': CONTINUATION,
                     'services': {}}
    linked = link(BindingRegistry([LibraryProbe()]), 'library_probe', entry, run_id=run_id,
                  journal=world['journal'], collaborators=collaborators)
    asyncio.run(linked.run())
    units = [unit[2] for unit in world['journal'].units(run_id, (('library_probe', run_id),))]
    return [unit['outcome'] for unit in units][:len(plan)]


def open_store(tmp_path):
    return open_world(tmp_path)
