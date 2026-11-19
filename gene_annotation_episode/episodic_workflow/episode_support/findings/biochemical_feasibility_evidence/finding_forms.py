"""Record forms of the A110 controlled finding, built from the feature tables (each feature's validator and meaning):
the investigation finding over the held assessments (``investigation_finding_features.FEATURES``) and one entry per
saved reaction sheet (``literature_reaction_cells.FEATURES``). Every text field is a fixed vocabulary; nothing in a
form admits model prose. An episode builds its own ``RETURN_FORM`` with these and selects its own fields."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.findings.biochemical_feasibility_evidence.investigation_finding_features import (
    FEATURES as FINDING_FEATURES)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.biochemical_feasibility_evidence.literature_reaction_cells import (
    FEATURES as SHEET_FEATURES)

FIELD_TYPES = {'number': 'number', 'count': 'integer', 'boolean': 'boolean', 'refs': 'record_refs'}


def _field(rule, meaning):
    required = 'optional' not in rule
    if rule[0] == 'choice':
        return ChoiceField('text', meaning, rule[1], required)
    if rule[0] == 'counts':
        return Field('record', meaning, required,
                     form=RecordForm({key: Field('integer', meaning + ': ' + key) for key in rule[1]}))
    return Field(FIELD_TYPES[rule[0]], meaning, required)


def reaction_sheet_form():
    return RecordForm({name: _field(rule, meaning) for name, (rule, meaning) in SHEET_FEATURES.items()})


def investigation_finding_form(meaning_of_sheets):
    """The finding: the investigation features and ``reaction_sheets`` (one entry per sheet, never combined)."""
    return RecordForm({**{name: _field(rule, meaning) for name, (rule, meaning) in FINDING_FEATURES.items()},
                       'reaction_sheets': Field('list', meaning_of_sheets, items=reaction_sheet_form())})
