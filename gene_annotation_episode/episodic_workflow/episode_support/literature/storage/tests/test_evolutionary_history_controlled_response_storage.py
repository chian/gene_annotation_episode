"""The controlled-response repository on the custody-scoped store: population from a constructed fixture source
roster (text, covariance document and graph image held as source records), the saved sheet read back and its
component rows projected, through the real runner."""
import json
from pathlib import Path

from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.evolutionary_history_evidence.literature_controlled_response_storage import LiteratureControlledResponseRepository

from .evolutionary_history_world import run, source, world  # noqa: F401

FIXTURE = Path(__file__).parent / 'fixtures' / 'controlled_response_v3'
SHEET = {'from_step': 0, 'path': ['result', 'sheet_ref']}
REPOSITORY = __name__ + ':SyntheticControlledResponse'


class SyntheticControlledResponse(LiteratureControlledResponseRepository):
    """The repository under the synthetic-fixture evidence profile, which the constructed fixture belongs to."""

    def __init__(self, store):
        super().__init__(store, evidence_origin='synthetic_fixture')


def held_fixture(world):
    """The fixture's sources as records the Episode can be given, and its selection naming them."""
    case = json.loads((FIXTURE / 'CONSTRUCTED_SOURCE_SELECTION_0.json').read_text())
    selection = json.dumps(case['selection'])
    held = []
    contents = {row['source_ref']: (row['content_utf8'].encode() if row['content_utf8'] is not None
                                    else (FIXTURE / row['encoded_image_file']).read_bytes())
                for row in json.loads((FIXTURE / 'CONSTRUCTED_SOURCE_ROSTER_001.json').read_text())}
    contents[case['selection']['covariance']['source_ref']] = case['source_covariance_text'].encode()
    for old, content in contents.items():
        text = content.decode() if not content.startswith(b'\x89PNG') else None
        reference, artifact = source(world, content if text is None else text,
                                     'image/png' if text is None else 'text/plain')
        selection = selection.replace(old, reference)
        held += [reference, artifact]
    return json.loads(selection), held


def step(tool, method, *arguments, scope=None, **keywords):
    """The plan step that runs ``method`` of the synthetic-profile repository above."""
    arguments = {'repository': REPOSITORY, 'method': method, 'call': list(arguments), 'keywords': keywords}
    if tool == 'read':
        return {'tool': 'read', 'arguments': arguments}
    return {'tool': 'call', 'arguments': {**arguments, 'scope': scope, 'assignment': {}}}


def test_a_controlled_response_sheet_is_saved_read_back_and_projected(world):
    selection, held = held_fixture(world)
    populated, listed, saved, keys, cells = run(world, 'controlled_response', [
        step('call', 'populate', selection, scope=world['scope']),
        step('read', 'held_sheet_refs'),
        step('read', 'read', SHEET),
        step('read', 'requested_component_keys', SHEET, {}),
        step('read', 'project_cells', [SHEET], components=[{'from_step': 0, 'path': ['result', 'component_keys', 0]}])],
        held=held)
    sheet = populated['result']['sheet_ref']
    assert populated['status'] == 'completed' and listed == [sheet]
    assert saved['input_source_ref'] == selection['source_ref']
    assert saved['evidence_origin'] == 'synthetic_fixture'
    assert [row['sheet_ref'] for row in cells] == [sheet]
    assert cells[0]['component_key'] == populated['result']['component_keys'][0]
    assert populated['result']['component_keys'] == saved['component_roster']
