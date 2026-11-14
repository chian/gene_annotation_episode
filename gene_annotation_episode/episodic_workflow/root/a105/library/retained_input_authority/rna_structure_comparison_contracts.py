"""Closed retained-input RNA comparison contracts; no scientific execution.

The schemas describe stored values, not a formula language. Input relationships
are checked against supplied records. Component validation checks representation
and relationships only; publication separately checks deterministic arithmetic.
"""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.rna_structure_contracts import RNA_SYMBOLS, RNA_ISSUE_CODES
PROFILE = 'vienna_2_7_retained_linear_model_v1'
UNCERTAINTY_REASON = 'selected_inputs_do_not_produce_comparison_uncertainty'
COMPARISON_REASONS = frozenset('\nnot_requested not_supplied not_tested received_failure zero_denominator\ninvalid_selection duplicate_operand_requires_alias\nduplicate_sequence_variant_requires_representative invalid_alias\nsaved_operand_not_received original_receipt_mismatch retained_sheet_missing\nretained_sheet_digest_mismatch original_structure_unavailable original_topology_invalid\noriginal_sequence_unavailable sequence_identity_unverified unsupported_index_map\ncorrespondence_not_supplied invalid_correspondence substitution_manifest_mismatch\npartial_correspondence unmapped_selected_site unresolved_partner unresolved_pair_endpoints\nsupplied_alignment_gap selected_site_absent invalid_site_selection\nrequested_energy_unavailable energy_kind_mismatch energy_structure_mismatch\nnative_model_missing model_setting_missing model_setting_different\nparameter_identity_missing parameter_identity_different unsupported_model_profile\nsoftware_generation_unverified equal_array_generation_rule_used different_sequence_lengths\nbaseline_unavailable baseline_comparability_unknown selected_population_only\nduplicate_alias_excluded comparison_uncertainty_not_produced nonfinite_derived_value\nselected_window_omits_members unknown_source_origin projection_not_requested\nprojection_mismatch selected_inputs_do_not_produce_comparison_uncertainty\n'.split())
CELL_STATES = frozenset(('present', 'not_requested', 'not_produced', 'missing_input', 'invalid_input', 'incompatible', 'failed', 'truncated', 'unknown'))
CELL_ORIGINS = frozenset(('retained_native_prediction', 'retained_native_evaluation', 'derived_correspondence', 'derived_topology_comparison', 'derived_energy_difference', 'derived_scan_count', 'derived_scan_rank'))
SITE_TRANSITIONS = ('unchanged_unpaired', 'unchanged_partner', 'lost_pairing', 'gained_pairing', 'reassigned_partner', 'deleted_site', 'inserted_site', 'unmapped_site', 'unresolved_partner', 'unavailable_topology')
PAIR_RELATIONS = ('preserved', 'lost', 'gained', 'unresolved_baseline', 'unresolved_variant')
PAIRING_STATES = ('changed', 'unchanged_in_complete_correspondence', 'unresolved', 'not_requested')
ENERGY_STATES = ('not_requested', 'comparable', 'native_energy_unavailable', 'model_incompatible', 'model_unknown', 'not_supplied', 'not_tested', 'received_failure')
RANK_CLASSES = ('unique_lowest', 'tied_lowest', 'not_lowest', 'unavailable', 'not_requested')
PREDICATES = ('lower_than_baseline', 'equal_to_baseline', 'higher_than_baseline', 'within_baseline_tolerance', 'model_incompatible', 'model_unknown', 'energy_unavailable', 'received_failure', 'not_supplied', 'not_tested')
PAIR_METRICS = tuple('baseline_pair_count variant_pair_count baseline_mapped_pair_count\nvariant_mapped_pair_count baseline_unresolved_pair_count variant_unresolved_pair_count\npreserved_pair_count lost_pair_count gained_pair_count known_pair_change_count\npair_symmetric_difference_count preserved_baseline_pair_fraction mapped_baseline_pair_fraction\nmapped_variant_pair_fraction alignment_inserted_nt alignment_deleted_nt'.split())
SITE_METRICS = tuple('requested_site_count shared_site_count decidable_site_count\nchanged_site_count unchanged_site_count lost_pairing_site_count gained_pairing_site_count\nreassigned_partner_site_count deleted_site_count inserted_site_count unmapped_site_count\nunavailable_topology_site_count unresolved_partner_site_count decidable_site_fraction\nchanged_site_fraction unchanged_site_fraction'.split())
ENERGY_METRICS = ('baseline_native_energy', 'variant_native_energy', 'baseline_selected_energy', 'variant_selected_energy', 'energy_delta', 'energy_absolute_delta', 'baseline_tolerance')
SCAN_ENERGY_METRICS = tuple('declared_entry_count canonical_member_count alias_entry_count\ndeclared_variant_count native_energy_available_variant_count received_failure_variant_count\nnot_supplied_variant_count not_tested_variant_count sheet_energy_unavailable_variant_count\nmodel_incompatible_variant_count model_unknown_variant_count comparable_variant_count\nrank_population_count lower_variant_count equal_variant_count higher_variant_count\nbaseline_rank_start baseline_rank_end baseline_tie_count\ncomparable_variant_fraction within_tolerance_variant_count baseline_selected_energy\nminimum_selected_energy baseline_energy_above_minimum lowest_energy_tie_count'.split())
SCAN_MEMBER_RANK_METRICS = ('member_rank_start', 'member_rank_end')
SCAN_SITE_METRICS = tuple('decidable_variant_count changed_variant_count unchanged_variant_count\nlost_pairing_variant_count gained_pairing_variant_count reassigned_partner_variant_count\ndeleted_variant_count unmapped_variant_count unavailable_topology_variant_count\nunresolved_partner_variant_count changed_variant_fraction unchanged_variant_fraction'.split())
COMPARISON_METRICS = frozenset((*PAIR_METRICS, *SITE_METRICS, *ENERGY_METRICS, *SCAN_ENERGY_METRICS, *SCAN_MEMBER_RANK_METRICS, *SCAN_SITE_METRICS, 'change_indicator'))
COMPARISON_UNITS = frozenset(('nt', 'sites', 'pairs', 'fraction', 'indicator', 'kcal/mol', 'kcal/mol/nt', 'entries', 'candidates', 'aliases', 'variants', 'rank'))
MODEL_SETTING_NAMES = ('temperature_c', 'dangles', 'noLP', 'noGU', 'noGUclosure', 'special_hp', 'logML', 'min_loop_size', 'max_bp_span', 'circ', 'gquad')
OTHER_SCALAR_SETTING_NAMES = tuple('backbone_length backtrack backtrack_type betaScale circ_alpha0\ncirc_penalty compute_bpp cv_fact energy_set helical_rise nc_fact nonstandards oldAliEn\npf_smooth ribo salt saltDPXInit saltDPXInitFact saltMLLower saltMLUpper sfact uniq_ML window_size'.split())
ARRAY_SETTING_NAMES = ('alias', 'pair', 'rtype')
COMPATIBILITY_FIELDS = ('energy_kind', 'unit', 'baseline.structure_association', 'variant.structure_association', 'model.engine', 'model.engine_version', 'hard_constraints', 'soft_constraints', 'parameter_artifact.sha256', 'parameter_artifact.size_bytes', 'parameter_load_return', 'parameter_save_return', 'other_observed_settings.name_set', *('effective_settings.' + name for name in MODEL_SETTING_NAMES), *('other_observed_settings.' + name for name in (*OTHER_SCALAR_SETTING_NAMES, *ARRAY_SETTING_NAMES)), *('software.' + name for name in ('worker_source_sha256', 'rna_module_sha256', 'rna_extension_sha256', 'viennarna_distribution_version')))

def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

def nullable(schema):
    return {'anyOf': [deepcopy(schema), {'type': 'null'}]}

def array(schema, *, minimum=0, unique=False):
    return {'type': 'array', 'items': schema, 'minItems': minimum, **({'uniqueItems': True} if unique else {})}

def enum(values):
    return {'enum': list(values)}
ID = {'type': 'string', 'minLength': 1, 'pattern': '^[^\\u0000\\r\\n]+$'}
COUNT = {'type': 'integer', 'minimum': 0}
NUMBER = {'type': 'number'}
BOOLEAN = {'type': 'boolean'}
NULL = {'type': 'null'}
TEXT = {'type': 'string'}
RNA_CHAR = {'type': 'string', 'pattern': '^[' + RNA_SYMBOLS + RNA_SYMBOLS.lower() + ']$'}
PATH = {'type': 'string', 'pattern': '^/(?:[^~\\u0000\\r\\n]|~[01])*$'}
PAIR = {'type': 'array', 'minItems': 2, 'maxItems': 2, 'items': COUNT}
COMPARISON_ISSUE_SCHEMA = obj({'stage': enum(('selection', 'authority', 'input', 'correspondence', 'compatibility', 'calculate', 'projection')), 'code': enum(sorted(COMPARISON_REASONS)), 'member_id': nullable(ID), 'comparison_id': nullable(ID), 'selection_id': nullable(ID), 'field': nullable(PATH), 'index': nullable(COUNT)})
ENERGY_REQUEST_SCHEMA = obj({'quantity': enum(('native_mfe', 'native_evaluation')), 'normalization': enum(('none', 'per_nt')), 'compatibility_profile': {'const': PROFILE}, 'baseline_absolute_tolerance': nullable({'type': 'number', 'minimum': 0})})
_OLD_ID = {'type': 'string', 'minLength': 1, 'pattern': '^[^\\u0000]+$'}
MEMBER_SELECTION_SCHEMA = {'oneOf': [obj({'kind': {'const': 'explicit'}, 'member_ids': array(ID, unique=True)}), obj({'kind': {'const': 'exceptions'}, 'predicates': array(enum(PREDICATES), minimum=1, unique=True)})]}

def _projection(family, **fields):
    return obj({'projection_id': ID, 'family': {'const': family}, **fields})
RNA_COMPARISON_PROJECTION_REQUEST_SCHEMA = {'oneOf': [_projection('energy_comparison', comparison_ids=array(ID, unique=True), metrics=array(enum(ENERGY_METRICS), unique=True), include_order=BOOLEAN, include_tolerance_band=BOOLEAN), _projection('structures', member_ids=array(ID, unique=True), fields=array(enum(('original_sequence', 'analysis_sequence', 'dot_bracket', 'pairs')), minimum=1, unique=True)), _projection('position_changes', comparison_id=ID, selection_id=ID, transitions=array(enum(SITE_TRANSITIONS), minimum=1, unique=True)), _projection('pair_changes', comparison_ids=array(ID, unique=True), relations=array(enum(PAIR_RELATIONS), minimum=1, unique=True)), _projection('comparison_counts', comparison_ids=array(ID, unique=True), selection_ids=array(ID, unique=True), metrics=array(enum((*PAIR_METRICS, *SITE_METRICS)), unique=True), include_pairing_change_state=BOOLEAN), _projection('scan_energy', scan_id=ID, metrics=array(enum(SCAN_ENERGY_METRICS), unique=True), include_rank_class=BOOLEAN), _projection('scan_sites', scan_id=ID, selection_ids=array(ID, unique=True), metrics=array(enum(SCAN_SITE_METRICS), unique=True)), _projection('scan_members', scan_id=ID, members=MEMBER_SELECTION_SCHEMA, fields=array(enum(('energy', 'delta', 'rank_start', 'rank_end', 'eligibility')), minimum=1, unique=True), order={'const': 'declared'}, limit=nullable(COUNT))]}
METRIC_SPECS = {}
for _metric in PAIR_METRICS:
    _unit = "fraction" if _metric.endswith("fraction") else "nt" if _metric.startswith("alignment_") else "pairs"
    METRIC_SPECS["rna_pair_compare_v1." + _metric] = {
        "metric": _metric, "units": (_unit,),
        "origins": ("derived_correspondence",) if _metric.startswith("alignment_") else ("derived_topology_comparison",)}
for _metric in (*SITE_METRICS, "change_indicator"):
    METRIC_SPECS["rna_site_compare_v1." + _metric] = {"metric": _metric,
        "units": ("indicator" if _metric == "change_indicator" else "fraction" if _metric.endswith("fraction") else "sites",),
        "origins": ("derived_topology_comparison",)}
for _metric in ENERGY_METRICS:
    METRIC_SPECS["rna_energy_compare_v1." + _metric] = {"metric": _metric,
        "units": ("kcal/mol",) if "native_energy" in _metric else ("kcal/mol", "kcal/mol/nt"),
        "origins": ("derived_energy_difference",) if _metric in ("energy_delta", "energy_absolute_delta", "baseline_tolerance")
            else ("retained_native_prediction", "retained_native_evaluation")}
for _metric in (*SCAN_ENERGY_METRICS, *SCAN_MEMBER_RANK_METRICS):
    _energy_metric = _metric in ("baseline_selected_energy", "minimum_selected_energy", "baseline_energy_above_minimum")
    _unit = ("entries" if _metric == "declared_entry_count" else "aliases" if _metric == "alias_entry_count"
        else "rank" if "rank_start" in _metric or "rank_end" in _metric else "fraction" if _metric.endswith("fraction")
        else "candidates" if _metric in ("canonical_member_count", "rank_population_count", "baseline_tie_count", "lowest_energy_tie_count")
        else "variants")
    _origins = (("derived_energy_difference",) if _metric == "baseline_energy_above_minimum" else
        ("retained_native_prediction", "retained_native_evaluation") if _energy_metric else
        ("derived_scan_rank",) if _unit == "rank" else ("derived_scan_count",))
    METRIC_SPECS["rna_scan_energy_v1." + _metric] = {"metric": _metric,
        "units": ("kcal/mol", "kcal/mol/nt") if _energy_metric else (_unit,), "origins": _origins}
for _metric in SCAN_SITE_METRICS:
    METRIC_SPECS["rna_scan_site_v1." + _metric] = {"metric": _metric,
        "units": ("fraction" if _metric.endswith("fraction") else "variants",), "origins": ("derived_scan_count",)}
COMPARISON_FORMULAS = frozenset(METRIC_SPECS)
NUMERIC_CELL_SCHEMA = obj({'metric': enum(sorted(COMPARISON_METRICS)), 'value': nullable(NUMBER), 'unit': enum(sorted(COMPARISON_UNITS)), 'state': enum(sorted(CELL_STATES)), 'reason': nullable(enum(sorted(COMPARISON_REASONS))), 'numerator': nullable(NUMBER), 'denominator': nullable(NUMBER), 'origin': enum(sorted(CELL_ORIGINS)), 'formula_id': enum(sorted(COMPARISON_FORMULAS)), 'input_paths': array(PATH, unique=True), 'population_id': nullable(ID), 'selection_id': nullable(ID), 'uncertainty': obj({'state': {'const': 'not_produced'}, 'value': NULL, 'reason': {'const': UNCERTAINTY_REASON}})})
PARTNER_SCHEMA = obj({'state': enum(('unpaired', 'mapped', 'gap', 'unmapped', 'unavailable')), 'local_index': nullable(COUNT), 'column': nullable(COUNT), 'counterpart_index': nullable(COUNT)})
SITE_CHANGE_SCHEMA = obj({'column': nullable(COUNT), 'baseline_index': nullable(COUNT), 'variant_index': nullable(COUNT), 'baseline_symbol': nullable(RNA_CHAR), 'variant_symbol': nullable(RNA_CHAR), 'baseline_partner': PARTNER_SCHEMA, 'variant_partner': PARTNER_SCHEMA, 'transition': enum(SITE_TRANSITIONS), 'change_indicator': NUMERIC_CELL_SCHEMA, 'issues': array(COMPARISON_ISSUE_SCHEMA)})
PAIR_CHANGE_SCHEMA = obj({'relation': enum(PAIR_RELATIONS), 'columns': nullable(PAIR), 'baseline_pair': nullable(PAIR), 'variant_pair': nullable(PAIR), 'baseline_pair_key': nullable(ID), 'variant_pair_key': nullable(ID), 'gap_endpoint': BOOLEAN, 'issues': array(COMPARISON_ISSUE_SCHEMA)})
NATIVE_ENERGY_SCHEMA = obj({'value': nullable(NUMBER), 'numeric_text': nullable(TEXT), 'unit': {'const': 'kcal/mol'}, 'state': enum(sorted(CELL_STATES - {'unknown'})), 'reason': nullable(enum(sorted(RNA_ISSUE_CODES))), 'structure_key': nullable(_OLD_ID), 'engine': enum((None, 'ViennaRNA')), 'engine_version': nullable(_OLD_ID), 'model_key': nullable(_OLD_ID)})
COMPATIBILITY_SCHEMA = obj({'profile': {'const': PROFILE}, 'state': enum(('compatible', 'incompatible', 'unknown')), 'checks': array(obj({'field': enum(COMPATIBILITY_FIELDS), 'outcome': enum(('equal', 'different', 'missing', 'unsupported', 'equal_by_versioned_generation_rule'))})), 'issues': array(COMPARISON_ISSUE_SCHEMA)})
ENERGY_COMPARISON_SCHEMA = obj({'request': ENERGY_REQUEST_SCHEMA, 'baseline_native': nullable(NATIVE_ENERGY_SCHEMA), 'variant_native': nullable(NATIVE_ENERGY_SCHEMA), 'compatibility': COMPATIBILITY_SCHEMA, 'components': array(NUMERIC_CELL_SCHEMA), 'order': enum(('variant_lower', 'equal', 'variant_higher', 'unavailable')), 'baseline_tolerance_band': enum(('below', 'within', 'above', 'not_requested', 'unavailable'))})
