"""The A110 literature reaction grading of this episode through the real runner on a real Store: the first decision
(the episode's own ``decide``, the model not asked) offers the reaction graders with the owner's grader
instructions; the XLSX sheet reader and the populate tool run as real tool units on the held reaction world
(``episode_support/literature/storage/tests/reaction_world.py``) with a real supplementary workbook; the return is
admitted by the episode's own form. Nothing is faked."""
import asyncio
import importlib
import io
import zipfile

import pytest

from episode_runtime import BindingRegistry, ModelRequest, RunJournal, ToolCall, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.biochemical_feasibility_evidence.literature_reaction_types import (
    EXPERIMENT_TYPES)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.tests.reaction_world import (
    held_world, source)

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').TableEvidenceExtraction
PATH = EPISODE.binding_path
SETTINGS = {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}}


def workbook():
    """A real one-sheet XLSX package: the two preparations' ratios."""
    parts = {
        '[Content_Types].xml': '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
        '_rels/.rels': '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        'xl/workbook.xml': '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Ratios" sheetId="1" r:id="rId1"/></sheets></workbook>',
        'xl/_rels/workbook.xml.rels': '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
        'xl/worksheets/sheet1.xml': '<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>preparation</t></is></c><c r="B1" t="inlineStr"><is><t>ratio</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>prep1</t></is></c><c r="B2"><v>0.7</v></c></row><row r="3"><c r="A3" t="inlineStr"><is><t>prep2</t></is></c><c r="B3"><v>0.9</v></c></row></sheetData></worksheet>',
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as package:
        for name, text in parts.items():
            package.writestr(name, text)
    return buffer.getvalue()


def test_the_next_decision_the_sheet_reader_a_populate_unit_and_the_admitted_return(tmp_path):
    store, entry, arguments, paper = held_world(tmp_path, requested=['ratio_mean'])
    supplement = source(store, workbook(), parents=[paper['id']])
    assignment = entry['assignment']
    window = assignment['selection']
    assignment['selection'] = {'kind': 'window', **window}
    assignment['received_record_refs'] += [supplement['id'], supplement['artifact_ref']]
    collaborators = {'store': store, 'model_provider': ModelProvider(load_config(), tmp_path / 'model_calls',
                                                                    tmp_path),
                     'continuation': {PATH: SETTINGS}, 'services': {}}
    run = link(BindingRegistry([EPISODE()]), PATH, entry, run_id='a110-table-grading',
               journal=RunJournal(tmp_path / 'journal.sqlite3'), collaborators=collaborators)
    request = asyncio.run(run.next_decision())
    summary = EPISODE()._summary(run.view)
    assert summary['family'] == 'reaction' and EPISODE.credit(summary, run.view.records) == 0
    assert isinstance(request, ModelRequest)
    assert all(grader['question'] in request.instructions for grader in EXPERIMENT_TYPES.values())
    envelope = {'scope': assignment['scope'], 'page_source_ref': paper['id']}
    sheets = asyncio.run(run.run_unit(ToolCall('source_xlsx_sheets', {**envelope,
                                                                      'arguments': {'source_ref': supplement['id']}})))
    assert sheets['outcome']['status'] == 'completed', sheets['outcome']
    assert 'Ratios' in str(sheets['outcome']['result'])
    unit = asyncio.run(run.run_unit(ToolCall('literature_reaction_populate', {**envelope, 'arguments': arguments})))
    assert unit['outcome']['status'] == 'completed', unit['outcome']
    sheet_ref = unit['outcome']['result']['sheet_ref']
    summary = EPISODE()._summary(run.view)
    [features] = summary['reaction_sheets']
    assert features['sheet_refs'] == [sheet_ref] and features['ratio_mean'] == pytest.approx(.8)
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 2, 'credit': 0.0}, ())
    assert EPISODE.return_form.select(()).admit(result, 'return') == result
    store.close()
