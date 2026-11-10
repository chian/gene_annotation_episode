"""Factoring saved results preserves scientific differences and custom returns."""
from copy import deepcopy
import json

from gene_annotation_episode.literature_current_results import (
    current_interpretation_view, render_current_scoring_results,
)


class Display:
    @staticmethod
    def inline(value):
        return json.dumps(value, ensure_ascii=False)


def table(headers, rows):
    return '\n'.join(' | '.join(map(str, row)) for row in [headers, *rows])


def saved_sheet(reference, *, condition, criterion):
    cells = [dict(sheet_ref=reference, component=name, value=value, unit='per_min',
        status='populated', assay_type='activity_rate', quantity_kind='turnover',
        formula=name, meaning='A selected source quantity.', conditions=[condition],
        interpretations={'measurement_identity': criterion})
        for name, value in [('measured_effect', 6.18), ('effect_precision', 25)]]
    return dict(axis='A105', sheet_ref=reference, status='current', cells=cells,
                subscoring_sheets=[])


def test_different_conditions_and_criteria_remain_tied_to_exact_saved_sheet():
    sheets = [saved_sheet('source_a', condition='aerobic',
        criterion={'status': 'supported', 'support_refs': ['reference_a']}),
        saved_sheet('source_b', condition='anaerobic',
        criterion={'status': 'unknown', 'support_refs': []})]
    before = deepcopy(sheets)
    rendered = render_current_scoring_results(sheets, table=table, display=Display())
    assert sheets == before
    assert 'aerobic' in rendered and 'anaerobic' in rendered
    assert 'source_a' in rendered and 'source_b' in rendered
    assert 'reference_a' in rendered
    assert 'supported' in rendered and 'unknown' in rendered
    assert '6.18' in rendered and '25' in rendered
    assert rendered.count('measurement identity |') == 2
    # A common criterion is factored within each source, never merged across
    # sources with different actual measurements, conditions or qualifications.
    assert rendered.count('Saved criterion result') == 2


def test_custom_field_names_use_declared_meaning_and_keep_uncovered_cells():
    sheets = [saved_sheet('source_a', condition='aerobic', criterion={})]
    report = {'inventory_named_by_parent': ['reference_old'],
        'numbers_named_by_parent': sheets[0]['cells'],
        'custom_unresolved_question': ['hypothesis_x'],
        'historical_uncovered_numbers': [{**sheets[0]['cells'][0], 'sheet_ref': 'source_old'}]}
    schema = {'properties': {
        'inventory_named_by_parent': {'x-source': 'interpretation_basis_refs'},
        'numbers_named_by_parent': {'x-source': 'literature_assay_grading_cells'},
        'historical_uncovered_numbers': {'x-source': 'literature_assay_grading_cells'}}}
    before = deepcopy(report)
    result = current_interpretation_view(report, schema, sheets)
    assert report == before
    assert result == {'custom_unresolved_question': ['hypothesis_x'],
        'historical_uncovered_numbers': report['historical_uncovered_numbers']}
