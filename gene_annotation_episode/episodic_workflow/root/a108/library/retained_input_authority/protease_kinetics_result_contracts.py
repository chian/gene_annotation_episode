"""Controlled ordinary protease values over the shared stored-value engine.

These contracts neither run a fit nor read a File. Provenance strings inside
values confer no admission; only the final Return's actual Source is semantic.
"""
from __future__ import annotations
from copy import deepcopy
import re
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority import molecular_sequence_result_contracts as stored
TOOL = 'analyze_protease_kinetics'
PACKET_VERSION = 'ordinary_protease_kinetics_values_v1'
FACT_SOURCE = 'protease_kinetics_outcomes'
SELECTOR_VERSION = stored.PROTEASE_SELECTOR_VERSION
VALUES_VERSION = stored.PROTEASE_PUBLIC_VERSION
COMPONENTS_VERSION = 'protease_kinetics_components_v2'
FILE_ROLES = ('capture', 'sheet', 'components')
_SOURCE = re.compile('source_[0-9a-f]{24,64}')
_IDENTITIES = ({'kind': 'summary'}, {'kind': 'protease_fit'}, {'kind': 'protease_covariance', 'parameter_i': 0, 'parameter_j': 0}, {'kind': 'protease_curve', 'substrate_ordinal': 0}, {'kind': 'protease_quantity', 'quantity': stored.QUANTITIES[0]})

def _source(value):
    return type(value) is str and _SOURCE.fullmatch(value) is not None

def _selection(rows, *, mode=stored.MODES[0], saved_sheet_ref=None):
    return stored.validate_molecular_sequence_result_selector(dict(version=SELECTOR_VERSION, operation=TOOL, mode=mode, saved_sheet_ref=saved_sheet_ref, rows=rows, return_files=[]))

def validate_ordinary_protease_kinetics_packet(value):
    value = stored.copy_json(value)
    stored.closed(value, ('version', 'selection', 'values', 'file_states', 'failures'))
    stored.require(value['version'] == PACKET_VERSION)
    stored.closed(value['selection'], ('rows',))
    selector = _selection(value['selection']['rows'])
    stored.validate_molecular_sequence_fact_values(stored.PROJECTION_SOURCE, [value['values']])
    public = value['values']
    stored.require(public['schema'] == VALUES_VERSION and public['operation'] == TOOL and (public['components_schema'] in (None, COMPONENTS_VERSION)) and ([(row['row_id'], row['field']) for row in public['rows']] == [(row['row_id'], field) for row in selector['rows'] for field in row['fields']]))
    stored.closed(value['file_states'], FILE_ROLES)
    stored.require(all((state in stored.FILE_STATES and state != 'produced_unretained' for state in value['file_states'].values())) and all((value['file_states'][role] == public['source_states'][role] for role in ('sheet', 'components'))))
    stored.require(type(value['failures']) is list)
    for issue in value['failures']:
        stored.validate_failure(issue)
    stored.require(all((issue in value['failures'] for issue in public['failures'])))
    return value

def validate_ordinary_protease_kinetics_return(value):
    value = stored.copy_json(value)
    stored.require(type(value) is dict and _source(value.get('source_ref')))
    packet = {key: item for key, item in value.items() if key != 'source_ref'}
    validate_ordinary_protease_kinetics_packet(packet)
    return value

def _obj(properties):
    return dict(type='object', properties=properties, required=list(properties), additionalProperties=False)

def _row_selector_schema():
    variants = []
    for identity in _IDENTITIES:
        fields = {key: {'type': 'string', 'const': value} if key == 'kind' else {'type': 'string', 'enum': list(stored.QUANTITIES)} if key == 'quantity' else {'type': 'integer', 'minimum': 0, **({'maximum': 1} if key in ('parameter_i', 'parameter_j') else {})} for key, value in identity.items()}
        table = stored.field_table(TOOL, identity, profile=stored._PROTEASE_PROFILE)
        variants.append(_obj({'row_id': _obj(fields), 'fields': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': {'type': 'string', 'enum': list(table)}}}))
    return {'anyOf': variants}

def ordinary_protease_kinetics_fact_sources():
    """Only the top actual Source is a reference-bearing public operand."""
    original = stored.molecular_sequence_fact_sources(profile=stored._PROTEASE_PROFILE)
    projection = deepcopy(original[stored.PROJECTION_SOURCE]['report_schema']['items']['anyOf'][0])
    issue = deepcopy(original[stored.FAILURE_SOURCE]['report_schema']['items'])

    def opaque(node):
        if type(node) is dict:
            if node.get('format') == 'reference' or 'x-reference-namespace' in node:
                node.pop('format', None)
                node.pop('x-reference-namespace', None)
            for child in node.values():
                opaque(child)
        elif type(node) is list:
            for child in node:
                opaque(child)
    opaque(projection)
    opaque(issue)
    item = _obj({'version': {'type': 'string', 'const': PACKET_VERSION}, 'source_ref': {'type': 'string', 'pattern': '^source_[0-9a-f]{24,64}$', 'format': 'reference', 'x-reference-namespace': 'source'}, 'selection': _obj({'rows': {'type': 'array', 'items': _row_selector_schema()}}), 'values': projection, 'file_states': _obj({role: {'type': 'string', 'enum': [state for state in stored.FILE_STATES if state != 'produced_unretained']} for role in FILE_ROLES}), 'failures': {'type': 'array', 'items': issue}})
    meaning = 'Selected retained protease native-fit and separately qualified physical values, with original assay, population, calibration, covariance and uncertainty qualifications even for an empty selection. Supplied historical Sheets do not establish original Workflow custody; nested provenance grants no Files.'
    return {FACT_SOURCE: dict(type='array', report_schema={'type': 'array', 'items': item, 'x-source': FACT_SOURCE}, description=meaning, meaning=meaning)}
