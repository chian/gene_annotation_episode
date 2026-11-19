"""Library functions of ``tools/`` and ``readers/`` run on the scoped store of a real run: a staged retained input,
the retained bytes of a protein-structure file, a source window read by descriptor, the component bytes of a
member, a failed-unit outcome, and a declared work table of the structural tools. Real Store, journal and runner;
the probe episode of ``episode_runtime/tests`` with the tools of ``library_probe/task.py`` added."""
import asyncio

from episode_runtime import BindingRegistry, link
from episode_runtime.tests.fact_collection.fact_extraction.episode import FactExtraction
from episode_runtime.tests.probe_world import SETTINGS, collaborators, entry, outcomes, tool, world  # noqa: F401

from .library_probe.episode import LibraryProbe

TEXT = 'ACDEFGHIKLMNPQRSTVWY'


def run_tool(world, run_id, name, **arguments):
    held = [arguments['ref']] if 'ref' in arguments else []
    registry = BindingRegistry([LibraryProbe(), FactExtraction()])
    linked = link(registry, 'library_probe', entry(world, [tool(name, **arguments)], assignment={'held_refs': held}), run_id=run_id,
                  journal=world['journal'], collaborators=collaborators(world, continuation={'library_probe': SETTINGS, 'fact_collection/fact_extraction': SETTINGS}))
    asyncio.run(linked.run())
    return outcomes(world, run_id, (('library_probe', run_id),))[0]['outcome']


def text_artifact(world):
    return world['store'].artifact(TEXT, 'text/plain')


def test_a_retained_input_is_staged_as_a_file_and_its_bytes_are_verified(world, tmp_path):
    done = run_tool(world, 'stage', 'stage', ref=text_artifact(world), workspace=str(tmp_path / 'workspace'))
    assert done['text'] == TEXT and done['bytes'] == TEXT and done['same_path'] is True
    assert done['refused'] == 'input_digest_mismatch'


def test_a_source_window_is_read_by_descriptor(world):
    done = run_tool(world, 'window', 'window', ref=text_artifact(world))
    assert done['text'] == TEXT[2:7] and done['start'] == 2 and done['end'] == 7 and done['total_bytes'] == len(TEXT)


def test_component_bytes_are_read_through_the_held_artifact(world):
    assert run_tool(world, 'components', 'components', ref=text_artifact(world))['bytes'] == TEXT[1:5]


def test_a_failed_unit_outcome_keeps_its_traceback_as_an_artifact(world):
    done = run_tool(world, 'failure', 'failure')
    assert done['status'] == 'failed' and done['code'] == 'provider_unreachable'
    assert done['diagnostic']['exception_type'] == 'ContractError'
    assert 'provider_unreachable' in done['diagnostic']['traceback']


def test_the_structure_binding_table_holds_a_row_per_source(world):
    assert run_tool(world, 'rows', 'binding_rows', ref=text_artifact(world)) == {'count': 1, 'body': {'target_ref': None}}
