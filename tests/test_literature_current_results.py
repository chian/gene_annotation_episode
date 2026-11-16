"""Factoring saved results preserves scientific differences and custom returns."""
from copy import deepcopy
import json

from gene_annotation_episode.episodic_workflow.root.library.literature_current_results import render_current_scoring_results


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


