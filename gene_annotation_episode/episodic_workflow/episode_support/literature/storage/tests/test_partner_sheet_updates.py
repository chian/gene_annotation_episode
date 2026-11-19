"""The A107 partner-sheet update library through the real runner: a sheet admitted from outside, a sheet published
that depends on it, and a new version of the admitted sheet that refreshes what depends on it. Real Store, journal
and runner, a real scoped store and reader; the repository is the working one of ``partner_sheet_probe``."""
import asyncio
import json

from episode_runtime import BindingRegistry, RunJournal, link
from episode_runtime.tests.probe_world import SETTINGS, open_world

from .partner_sheet_probe.episode import PartnerSheetProbe
from .partner_sheet_probe.repository import save_sheet

BINDING = 'partner_sheet_probe'


def held(store, *sheets):
    """Every record the library reads of the sheets, named for the pass: each sheet and the artifacts it names."""
    return list(dict.fromkeys(ref for sheet in sheets for ref in (sheet, store.get(sheet)['request_ref'], store.get(sheet)['artifact_ref'])))


def unit_outcomes(world, run_id):
    return [unit[2]['outcome'] for unit in world['journal'].units(run_id, ((BINDING, run_id),))]


def test_sheets_are_admitted_published_and_refreshed_through_declared_tables(tmp_path):
    world = open_world(tmp_path)
    store = world['store']
    first = save_sheet(store, 'external_episode', {'name': 'a', 'input': {'sheet_ref': 'none'}}, 'a1', 'caller')
    second = save_sheet(store, 'external_episode', {'name': 'a', 'input': {'sheet_ref': 'none'}}, 'a2', 'caller')
    plan = [{'tool': 'admit', 'arguments': {'ref': first}},
            {'tool': 'populate', 'arguments': {'arguments': {'name': 'b', 'input': {'sheet_ref': first}}}},
            {'tool': 'populate', 'arguments': {'arguments': {'name': 'c', 'input': {'sheet_ref': first},
                                                             'refuse': [second]}}},
            {'tool': 'admit', 'arguments': {'ref': second}}]
    entry = {'assignment': {'held_refs': held(store, first, second)}, 'message': {'plan': plan}, 'selection': []}
    linked = link(BindingRegistry([PartnerSheetProbe()]), BINDING, entry, run_id='sheets', journal=world['journal'],
                  collaborators={'store': store, 'model_provider': world['provider'], 'services': world['services'],
                                 'continuation': {BINDING: SETTINGS}})
    result = asyncio.run(linked.run())['result'].as_record()
    admit_first, publish_b, publish_c, admit_second = unit_outcomes(world, 'sheets')

    # The admitted sheet is a binding the Episode did not produce; the published one is its own.
    assert admit_first['bindings'] == [[first, admit_first['bindings'][0][1], 'admitted']]
    assert admit_first['current'] == [first]
    family_a, family_b = admit_first['bindings'][0][1], publish_b['bindings'][1][1]
    assert publish_b['bindings'][1][2] == 'owned' and family_a != family_b
    sheet_b = publish_b['outcome']['result']['sheet_ref']
    assert publish_b['current'] == [first, sheet_b]
    assert publish_c['outcome']['status'] == 'completed' and len(publish_c['current']) == 3

    # The new version of the admitted sheet re-publishes B on it; C cannot take it and is marked unavailable.
    versions = {family: [ref, status, detail] for family, ref, status, detail in admit_second['versions']}
    refreshed_b = versions[family_b][0]
    assert refreshed_b != sheet_b and versions[family_b][1] == 'current'
    assert versions[family_a][:2] == [second, 'current']
    assert json.loads(store.get_artifact(store.get(refreshed_b)['request_ref']))['arguments']['input'] == {
        'sheet_ref': second}
    unavailable = [value for value in versions.values() if value[1] == 'unavailable']
    assert [value[2]['reason'] for value in unavailable] == ['partner_input_component_not_received']
    assert admit_second['current'] == [second, refreshed_b]

    # What the reader of the summary and the return saw is the same current set, held by the Episode.
    assert result['current'] == [second, refreshed_b]
    assert result['credit'] == 4.0 and result['finding'] == {'steps_done': 4}
    store.close()
