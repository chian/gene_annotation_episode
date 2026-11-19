"""The investigation finding of a saved A102 source-geometry sheet (``literature_structure_cells``): controlled
features that code reads from the sheet's cell rows and its saved extraction, each with its validator.

What a feature is (``INVESTIGATION_FINDING_FEATURES_a102.md`` section 2.13): the evidence type (a fixed value of
the A102 vocabulary), the sheet's reference, the bounds, status and unavailable reason of each of the six cells,
the sizes of the two fixed panels and how many of their members were measured, the validation binding, the kind
of operand source and whether an experiment assessment was saved with the sheet. No model-written text: the
assessment's question, conclusion and limitations stay in the sheet, inside the Episode that saved it.

Also here: the rule of the merged A102 head (``a102_structural_report.py`` and ``a102_experimental_evidence.py``
at ``97308b94c``): the comparative native grading results and the experimental structure sheets are separate
sheets and are never combined into one A102 score (``aggregation: none``); each experimental sheet keeps its
component meanings.
"""
import json
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.calculations.structural_homology_evidence.literature_structure_calculations import (
    COMPONENTS, REASONS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.structural_homology_evidence.literature_structure_storage import (
    CELLS, LiteratureStructureRepository, SOURCE_KINDS, VALIDATION_BINDINGS)

EVIDENCE_TYPE = 'experimental_structure_geometry'
STATUSES = ('populated', 'unavailable')
REASON_CHOICES = (*REASONS, 'none')
AGGREGATION = 'none'

# name -> validator: ('number', low, high), ('count',), ('choice', options), ('boolean',), ('refs',)
FEATURES = {
    'evidence_type': ('choice', (EVIDENCE_TYPE,)),
    'sheet_refs': ('refs',),
    **{name + '_lower': ('number', -1, 1) for name in COMPONENTS},
    **{name + '_upper': ('number', -1, 1) for name in COMPONENTS},
    **{name + '_status': ('choice', STATUSES) for name in COMPONENTS},
    **{name + '_unavailable_reason': ('choice', REASON_CHOICES) for name in COMPONENTS},
    'geometry_member_count': ('count',),
    'geometry_measured_count': ('count',),
    'local_member_count': ('count',),
    'local_measured_count': ('count',),
    'validation_binding': ('choice', VALIDATION_BINDINGS),
    'operand_source_kind': ('choice', SOURCE_KINDS),
    'experiment_assessed': ('boolean',),
}
MEANINGS = {
    'evidence_type': 'The A102 evidence type: experimental_structure_geometry (a source-model geometry sheet)',
    'sheet_refs': 'The saved sheet (one reference)',
    **{name + '_lower': 'Lower conditional bound of the ' + name + ' cell, -1 to 1, dimensionless'
       for name in COMPONENTS},
    **{name + '_upper': 'Upper conditional bound of the ' + name + ' cell, -1 to 1, dimensionless'
       for name in COMPONENTS},
    **{name + '_status': 'Whether the ' + name + ' cell is populated (lower equals upper) or unavailable'
       for name in COMPONENTS},
    **{name + '_unavailable_reason': 'The fixed reason the ' + name + ' cell is unavailable, or none'
       for name in COMPONENTS},
    'geometry_member_count': 'Members of the fixed geometry panel (atom-group pairs)',
    'geometry_measured_count': 'Geometry panel members whose distance was measured in the selected model',
    'local_member_count': 'Residues of the fixed local-validation panel',
    'local_measured_count': 'Local panel residues with a reported RSCC joined to the selected model',
    'validation_binding': 'How the validation report is joined to the coordinates (entry and revision)',
    'operand_source_kind': 'The kind of source the operands were read from',
    'experiment_assessed': 'Whether an experiment assessment was saved with the sheet',
}


def validate_features(features):
    """Each feature against its validator; a bound pair must be ordered. A violation raises ``ValueError``."""
    if set(features) != set(FEATURES):
        raise ValueError('structure_finding_features_mismatch')
    for name, rule in FEATURES.items():
        value = features[name]
        if rule[0] == 'number':
            valid = (type(value) in (int, float) and math.isfinite(value) and rule[1] <= value <= rule[2])
        elif rule[0] == 'count':
            valid = type(value) is int and value >= 0
        elif rule[0] == 'choice':
            valid = value in rule[1]
        elif rule[0] == 'boolean':
            valid = type(value) is bool
        else:
            valid = type(value) is list and len(value) == 1 and type(value[0]) is str
        if not valid:
            raise ValueError('structure_finding_feature_invalid:' + name)
    for name in COMPONENTS:
        if features[name + '_lower'] > features[name + '_upper']:
            raise ValueError('structure_finding_bounds_unordered:' + name)
    if features['geometry_measured_count'] > features['geometry_member_count']:
        raise ValueError('structure_finding_feature_invalid:geometry_measured_count')
    if features['local_measured_count'] > features['local_member_count']:
        raise ValueError('structure_finding_feature_invalid:local_measured_count')
    return features


def sheet_features(reader, sheet_ref):
    """The features of one sheet this Episode saved, read from its cell rows and its saved extraction."""
    cells = {row['component']: row['cell'] for row in reader.table(CELLS).select({'sheet_ref': sheet_ref})}
    source = reader.get(sheet_ref)
    saved = json.loads(reader.get_artifact(source['artifact_ref']))
    geometry, local = saved['sheet']['native_geometry'], saved['extraction']['native_local']
    features = {'evidence_type': EVIDENCE_TYPE, 'sheet_refs': [sheet_ref]}
    for name in COMPONENTS:
        cell = cells[name]
        features[name + '_lower'] = cell['lower']
        features[name + '_upper'] = cell['upper']
        features[name + '_status'] = cell['status']
        features[name + '_unavailable_reason'] = ('none' if cell['unavailable_reason'] is None
                                                  else cell['unavailable_reason'])
    features.update({
        'geometry_member_count': len(geometry),
        'geometry_measured_count': sum(row['distance_A'] is not None for row in geometry),
        'local_member_count': len(local),
        'local_measured_count': sum(item['rscc'] is not None for item in local),
        'validation_binding': saved['extraction']['calculation_inputs']['validation_binding'],
        'operand_source_kind': saved['extraction']['source_kind'],
        'experiment_assessed': 'experiment_assessment' in saved,
    })
    return validate_features(features)


def current_sheet_features(reader):
    """The features of each current sheet this Episode saved, in the order the sheets were first saved."""
    return [sheet_features(reader, ref) for ref in LiteratureStructureRepository(reader).current_sheet_refs()]


def merged_sheet_features(own, returned):
    """This Episode's own sheets and the sheets its children returned, one entry per sheet (first seen kept):
    sheets are listed side by side, never combined."""
    result = {}
    for features in (*own, *returned):
        result.setdefault(features['sheet_refs'][0], features)
    return list(result.values())


def experimental_structure_arm(returned):
    """The head's experimental A102 arm: the source-geometry sheets its literature children returned, one entry
    per sheet with its own component features, kept beside the comparative native arm (the head's credit view
    over the native grading sheets) and never aggregated with it or across sheets."""
    return {'sheets': merged_sheet_features((), returned), 'aggregation': AGGREGATION,
            'separate_from': 'comparative_native_grading_sheets'}
