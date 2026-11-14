"""Assemble a numerical MetaCATS sheet from supplied parsed records only."""
from copy import deepcopy
import re

from . import bvbrc_alignment_provider_contracts as common
from . import bvbrc_metacats_association_contracts as associations_contract
from . import bvbrc_metacats_provider_contracts as c
from .bvbrc_alignment_values import diagnostic


def extract_metacats_sheet(*, analysis: dict, inputs: tuple[dict, ...],
        documents: tuple[dict, ...], read_outcomes: tuple[dict, ...], run: dict,
        associations: dict, populations: dict, category_associations: dict,
        parameters: dict) -> dict:
    """Retain every native token and independent association qualification.

    The adapter owns byte custody and original parameter authentication. This
    extractor neither reads bytes nor calculates tests. Missing evidence keeps
    the complete usable sheet; contradictory envelopes return a typed failure.
    """
    try:
        c.shape(parameters, {'source_dialect'})
        c.require(parameters['source_dialect'] == 'retained_bvbrc_metacats', 'source_dialect_invalid')
        common.input_map(inputs)
        common.document_maps(documents)
        common.validate_association_set(associations, inputs=inputs, documents=documents)
        category_associations = associations_contract.validate_metacats_association_set(
            category_associations, analysis=analysis, documents=documents, associations=associations)
        value = {'schema_version': 'bvbrc_metacats_sheet_v1', 'tool': 'C-L205-MetaCATS',
            'analysis': deepcopy(analysis), 'inputs': deepcopy(list(inputs)),
            'documents': deepcopy(list(documents)), 'read_outcomes': deepcopy(list(read_outcomes)),
            'run': deepcopy(run), 'associations': deepcopy(associations),
            'populations': deepcopy(populations), **deepcopy(category_associations), 'native_observations': []}
        value['requirements'] = c.merge_reports(associations['requirements'], category_associations['requirements'])
        value['diagnostics'] = c.merge_reports(associations['diagnostics'], category_associations['diagnostics'],
            *(r['diagnostics'] for r in read_outcomes))
        if analysis['alignment_id'] is None:
            value['requirements'] = c.merge_reports(value['requirements'], [c.need(analysis['analysis_id'],
                'alignment', 'alignment_document_unavailable', kind='input_bytes')])
        value['native_observations'] = c.native_observations(value)
        value = c.validate_metacats_sheet(value)
        partial = bool(value['requirements'] or value['diagnostics'] or any(r['status'] != 'ok' for r in read_outcomes))
        return {'status': 'partial' if partial else 'ok', 'value': value, 'diagnostics': deepcopy(value['diagnostics'])}
    except (ValueError, KeyError, TypeError, IndexError, UnicodeError, RecursionError) as exc:
        code = str(exc) if isinstance(exc, ValueError) and re.fullmatch(r'[A-Za-z0-9_]+', str(exc)) else c.PREFIX + 'shape_invalid'
        return {'status': 'invalid', 'value': None, 'diagnostics': [diagnostic(code, severity='error')]}


__all__ = ['extract_metacats_sheet']
