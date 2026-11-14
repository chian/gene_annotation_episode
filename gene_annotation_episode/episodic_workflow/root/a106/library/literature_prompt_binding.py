"""Private A106 presentation choices for source and child results."""

from collections.abc import Mapping

from gene_annotation_episode.episodic_workflow.root.a106.library.literature_a106_render import is_result, render_received, split_reports
from gene_annotation_episode.episodic_workflow.root.a106.library.literature_covariance_presentation import covariance_meanings, covariance_support_refs


def render_source_result(parts, value, content, title, *, values, records, section, table, pick):
    if (not isinstance(content, Mapping) or not isinstance(content.get('cells'), (list, tuple))
            or not content['cells'] or not all(is_result(row) for row in content['cells'])):
        return False
    section(parts, title, values(pick(value, ('status', 'selected_tool', 'feedback'))))
    render_received(parts, [{'return_field': 'own saved result', 'rows': content['cells']}],
        section=section, table=table, values=values, records=records)
    return True


def separate_child_results(reports):
    return split_reports(reports)


def render_child_results(parts, results, *, section, table, values, records):
    render_received(parts, results, section=section, table=table, values=values, records=records)


def separate_covariance_rows(name, value):
    if (isinstance(value, (list, tuple)) and value
            and all(isinstance(row, Mapping)
                and row.get('evaluated_scope') == 'interpreted_reference_perturbation'
                for row in value)
            and any('covariance_interpretations' in row for row in value)):
        return [{key: child for key, child in row.items()
            if key != 'covariance_interpretations'} for row in value], list(value)
    return value, []


def render_covariance(parts, rows, records, *, section, table):
    covariance_meanings(parts, rows, records, section=section, table=table)


def support_refs(value, records):
    return covariance_support_refs(value, records)


def use_resolved_display(evidence_axis, state):
    return (evidence_axis == 'A106'
        or state.get('literature_experimental_work', {}).get('evidence_axis') == 'A106')
