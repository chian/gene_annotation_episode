"""Persist selected reference reaction constraints and exact admitted subsets.

This adapter owns source custody and immutable selected-operation records. It
does not choose investigations, interpret experiments, add observations or
recompute a saved numerical sheet during replay.
"""
from __future__ import annotations
from copy import deepcopy
import json
import hashlib
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError, canonical, identity, obj, validate_schema
from gene_annotation_episode.episodic_workflow.root.a110.library.literature_reaction_types import EXPERIMENT_TYPES
from gene_annotation_episode.episodic_workflow.root.a110.source_display_labels import source_literal_label
from gene_annotation_episode.episodic_workflow.root.a110.library import literature_experiment_assessments as assessments
from gene_annotation_episode.episodic_workflow.root.a110.literature_sheet_updates import publication
from gene_annotation_episode.episodic_workflow.root.a110.library.literature_reaction_calculations import COMPONENTS, CONDITIONAL_CODES, REASONS, populate_reaction_constraints
from gene_annotation_episode.episodic_workflow.root.a110.library.literature_reaction_inputs import LITERAL_FIELDS, reaction_population_schema, read_reaction_inputs
from gene_annotation_episode.episodic_workflow.root.a110.library.literature_reaction_meanings import INPUT_VERSION as MEANINGS_INPUT_VERSION, RECORD_VERSION as MEANINGS_RECORD_VERSION, NAMESPACE as MEANINGS_NAMESPACE, BASES, MODEL_FIELDS, RESOURCE_FIELDS, DEMAND_FIELDS, direct_references as meaning_direct_references, publish_meanings, semantic_metadata, binding_references
PROVIDER = 'literature.experimental.reaction'
FORMULA_CODES = {name: 'reaction_' + name + '_v1' for name in COMPONENTS}
BINDINGS = {'assayed_subject_ref': ('molecule', 'reference'), 'construct_ref': ('construct', 'reference'), 'experiment_ref': ('experiment', 'reference'), 'numerator_ref': ('numerator', 'term'), 'denominator_ref': ('denominator', 'term'), 'endpoint_ref': ('endpoint', 'term'), 'condition_ref': ('condition', 'context'), 'resource_context_ref': ('resource_context', 'context')}
SOURCE_KINDS = ('primary_source', 'retained_extraction', 'graph_extraction', 'synthetic_fixture')
LITERAL_REFERENCE_TYPES = {'molecule': 'literature_result', 'construct': 'construct', 'experiment': 'assay'}
_FIXED_METADATA = {'evaluation_scope': 'reported_reference_reaction_constraints', 'bound_kind': 'logical_model_domain_not_confidence_interval', 'measurement_corrections': 'not_applied', 'target_correspondence': 'not_evaluated', 'uncertainty_interpretation': 'descriptive_not_confidence_interval'}

def literal_reference_role(record):
    """Recover the producer's original role, including historical assay-typed subjects.

    The accession binds the selected literal field and its exact saved anchor.
    No label interpretation, source rereading or biological identity inference
    is involved. Caller-declared assays keep their existing authority.
    """
    if record.get('record_type') != 'reference' or record.get('origin') != 'tool':
        return None
    anchor = record.get('anchor')
    if not isinstance(anchor, dict):
        return None
    for role in LITERAL_REFERENCE_TYPES:
        if record.get('accession') == identity('reaction_literal', {'field': role, **anchor}):
            return role
    return None

def reaction_return_view_requirements():
    """Static contract metadata; no source lookup or scientific interpretation."""
    return {'required_sheet_versions': {'literature_reaction_cells': 'literature_reaction_record_v2', 'literature_reaction_semantic_cells': MEANINGS_RECORD_VERSION}, 'detail': "The numerical and semantic return views require different saved sheet versions. A legacy numerical sheet has no saved semantic bindings. Inspect the actual sheet's Source version and select its matching recorded-fact view. A valid numerical return may include an empty semantic companion; a lone empty wrong view is rejected. Redelivery changes the representation of existing saved facts and cannot create semantic bindings. Source-supported meanings require an a110_source_reaction_measurements_v2 dataset or an a110_source_reaction_selection_v1 calculation, rather than another population of the same a110_source_reaction_measurements_v1 dataset."}

def _metadata(extraction, sheet):
    ratio = extraction['calculation_inputs']['ratio']
    budget = extraction['calculation_inputs']['budget']
    details = sheet['ratio_details']
    reported_sd = details['reported_sample_sd']
    derived_sd = details['derived_sample_sd']['value']
    return {**_FIXED_METADATA, 'operand_source_kind': extraction['arguments']['source_kind'], 'ratio_origin': ratio['origin'] if ratio is not None else None, 'budget_origin': budget['origin'] if budget is not None else None, 'independent_n': details['independent_n'], 'reported_sample_sd': reported_sd, 'derived_sample_sd': derived_sd, 'ratio_uncertainty': 'reported_sample_sd' if reported_sd is not None else 'descriptive_sample_sd' if derived_sd is not None else 'unreported', 'ratio_mode': ratio['mode'] if ratio is not None else None, 'ratio_kind': ratio['ratio_kind'] if ratio is not None else None, 'ratio_unit': ratio['unit'] if ratio is not None else None, 'claim_prediction': ratio['claim'] if ratio is not None else None, 'alternative_predictions': [entry['prediction'] for entry in ratio['alternatives']] if ratio is not None else [], 'budget_basis': budget['basis'] if budget is not None else None, 'budget_unit': budget['unit'] if budget is not None else None, 'resources_complete': budget['resources_complete'] if budget is not None else None, 'demand': budget['demand'] if budget is not None else None}

def _direct_references(args):
    """Fixed semantic order survives canonical JSON object-key reordering."""
    return list(dict.fromkeys([args['source_ref'], *([args['data_source_ref']] if args['data_source_ref'] is not None else []), *(args['literals'][field]['source_ref'] for field in LITERAL_FIELDS if args['literals'][field] is not None), *(entry['source_ref'] for entry in args['interpretation_witnesses'])]))

def reaction_direct_references(extraction, direct):
    refs = meaning_direct_references(extraction, direct)
    if 'native_evidence' in extraction:
        from gene_annotation_episode.episodic_workflow.root.a110.library.literature_reaction_native_inputs import native_direct_references
        refs.extend(native_direct_references(extraction['native_evidence']))
    return list(dict.fromkeys(refs))
