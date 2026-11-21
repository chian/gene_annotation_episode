"""The sheet an extraction saves and what returns to the parent, through the real runner's public API on a real Store: the
unit ``extract`` saves the perturbation sheet through the population route (the route reads the numbers from the quoted
bytes, the model types none), the controlled finding is read by code from the A106 sheets this episode saved (none: a leaf
saves no grading sheet), and the return is admitted by ``RETURN_FORM``. Nothing is faked; no model is asked."""
import asyncio
import importlib
import json

from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_perturbation_storage import (
    PROVIDER as PERTURBATION_PROVIDER)

from .a106_world import SETTINGS, TEXT, answer, held_world, linked_run

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceCoverageImprovement
PATH = EPISODE.binding_path


def test_the_extraction_saves_the_perturbation_sheet_from_the_quoted_bytes_and_the_return_names_it(tmp_path):
    store, entry, names = held_world(tmp_path, windows=1)
    linked, _, _ = linked_run(tmp_path, [EPISODE()], PATH, entry, store, 'a106-report-sheet', {PATH: SETTINGS})
    asyncio.run(linked.next_decision())
    summary = EPISODE.internal_summary(linked.view)
    done = asyncio.run(linked.run_unit(EPISODE.action(answer(), summary, linked.view.records, None)))
    outcome = done['outcome']
    assert outcome['status'] == 'completed', outcome
    sheet_ref = outcome['result']['sheet_ref']
    reader = linked.view.records
    assert reader.receipt(sheet_ref)['how'] == 'produced' and reader.get(sheet_ref)['provider'] == PERTURBATION_PROVIDER
    cells = outcome['result']['cells']
    assert cells['W_mean_variance']['value'] == 1 and cells['perturbation_difference']['value'] == 9

    summary = EPISODE.internal_summary(linked.view)
    assert summary['a106_findings'] == {'intervention_assessments': [], 'a106_subscores': []}
    completion = {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': EPISODE.credit(summary, reader)}
    selection = ('literature_source_lead_dispositions', 'record_refs')
    result = EPISODE.final_to_parent(summary, completion, selection)
    admitted = EPISODE.return_form.select(selection).admit(result, 'return')
    assert admitted == result and result['credit'] == 1.0
    assert result['literature_source_lead_dispositions'] == {'relevant_lead_count': 1,
                                                             'lead_source_refs': [names['source']]}
    assert result['record_refs'] == [sheet_ref]
    assert set(EPISODE.return_form.select(selection).record_refs(admitted)) == {names['source'], sheet_ref}
    assert [spec for spec in EPISODE.return_form.fields.values() if spec.type == 'text'] == []
    assert TEXT.decode() not in json.dumps(result)
    json.dumps(result, allow_nan=False)
    store.close()
