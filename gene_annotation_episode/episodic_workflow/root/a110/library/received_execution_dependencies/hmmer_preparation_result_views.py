from __future__ import annotations
from copy import deepcopy
from functools import wraps
import math
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_hmmer_preparation_contracts import PROGRAM_MODES, operand_contract, output_contract
_COLLECTIONS = ('input_records', 'output_records', 'native_rows', 'calculations')
_DIRECTIONS = ('input', 'working_copy', 'output')
_COMPONENT_STATES = {'present', 'missing', 'incomplete', 'incompatible', 'nonfinite', 'failed'}
_STATES = _COMPONENT_STATES | {'invalid', 'native_missing_sentinel', 'undetermined', 'decoded', 'partial', 'unsupported', 'unknown', 'complete', 'truncated', 'not_measured'}
_OUTCOMES = {'pass', 'fail', 'unknown', 'not_applicable'}
_FAMILIES = {**dict.fromkeys(('hmmconvert', 'hmmfetch', 'hmmpress'), 'artifact'), **dict.fromkeys(('hmmbuild', 'alimask'), 'alignment_preparation'), 'hmmemit': 'emission', 'hmmsim': 'simulation', 'hmmstat': 'statistics', 'makehmmerdb': 'fm', 'hmmerfm-exactmatch': 'fm'}

def _error(code):
    raise ContractError('native_hmmer_preparation_projection_' + code)

def _contract_errors(code):
    """Malformed supplied structure is a contract failure, never an incidental exception."""

    def decorate(function):

        @wraps(function)
        def wrapped(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except (AttributeError, KeyError, TypeError, IndexError, RecursionError, OverflowError) as exc:
                raise ContractError('native_hmmer_preparation_projection_' + code) from exc
        return wrapped
    return decorate

def _text(value, *, nullable=False):
    if value is None and nullable:
        return
    if type(value) is not str or not value or '\x00' in value:
        _error('nonempty_text_required')

def _fields(value, fields, code='fields_invalid'):
    if type(value) is not dict or set(value) != set(fields):
        _error(code)

def _finite_json(value):
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for child in value:
            _finite_json(child)
        return
    if type(value) is dict and all((type(key) is str for key in value)):
        for child in value.values():
            _finite_json(child)
        return
    _error('finite_json_required')

def _integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        _error('integer_required')

def _spec(unit, meaning, *, state=None, cell=True):
    return {'unit': unit, 'meaning': meaning, 'state': state, 'cell': cell}

def _cells(entries, prefix=''):
    return {prefix + path: _spec(unit, meaning) for path, (unit, meaning) in entries.items()}

def _native(entries, prefix='', state=None):
    return {prefix + path: _spec(unit, meaning, cell=False, state=state + path if state else None) for path, (unit, meaning) in entries.items()}
_MODEL = _native({'length': ('match_state_count', 'Native LENG: declared model match states.'), 'sequence_count': ('sequence_count', 'Native NSEQ: training sequence count.'), 'effective_sequence_count': ('effective_sequence_count', 'Native EFFN: effective training sequence count.'), 'maximum_length': ('residue_count', 'Native MAXL: maximum expected hit length.'), 'checksum': ('checksum', 'Native CKSUM digital sequence checksum; an identifier, not confidence.'), 'calibration.EVD.mu': ('bit', 'Original HMMER2 EVD score location mu; no HMMER3 calibration mode is inferred.'), 'calibration.EVD.lambda': ('inverse_bit', 'Original positive HMMER2 EVD inverse-scale parameter lambda; no HMMER3 calibration mode is inferred.')})
for _tag in ('GA', 'TC', 'NC'):
    for _part in ('sequence', 'domain'):
        _MODEL[f'cutoffs.{_tag}.{_part}'] = _spec('bit', f'Native {_tag} {_part} score cutoff; no calibration is inferred.', cell=False)
_MODEL_COMPONENTS = _cells({'sequence_count': ('sequence_count', 'Saved native NSEQ training count.'), 'effective_sequence_count': ('effective_sequence_count', 'Saved native EFFN effective count.'), 'effective_sequence_ratio': ('effective_sequences_per_input_sequence', 'Saved EFFN/NSEQ with its explicit positive NSEQ denominator.'), 'declared_length': ('match_state_count', 'Saved native declared LENG.'), 'match_state_count': ('decoded_match_row_count', 'Count of decoded match-position rows, separate from declared length.'), 'mean_match_entropy': ('bit_per_match_position', 'Saved mean -sum(p log2 p) over every declared match position; usable native probability views, including explicitly qualified HMMER2 nominal values, are not normalized.'), 'mean_match_relative_entropy': ('bit_per_match_position', 'Saved mean sum(p log2(p/q)) over every declared match position and explicit background q; source and topology qualifications remain in the shared components.')})
for _container in ('composition', 'initial.insert', 'initial.transitions.M', 'initial.transitions.I', 'initial.transitions.D'):
    for _name in ('mass', 'mass_residual'):
        _MODEL_COMPONENTS[_container + '.' + _name] = _spec('probability_mass', 'Saved ' + ('probability sum' if _name == 'mass' else 'probability sum minus one') + ' for ' + _container + '; transition M/I/D outgoing populations stay separate.')
_A_CALC = {'population': _cells({'decoded_model_count': ('decoded_model_count', 'Decoded models in the declared input or output population; unsupported decoding stays unknown.'), 'complete_model_count': ('complete_decoded_model_count', 'Terminated decoded models without fatal extraction issues.'), 'primary_name_count': ('primary_name_occurrence_count', 'Occurrences of usable native NAME headers.'), 'accession_count': ('accession_occurrence_count', 'Occurrences of usable native ACC headers.'), 'distinct_primary_name_count': ('distinct_name_count', "Distinct usable NAME values in this direction's model population."), 'distinct_accession_count': ('distinct_accession_count', "Distinct usable ACC values in this direction's model population."), 'model_artifact_bytes': ('byte', 'Sum of actual retained model artifact bytes in this direction.')}), 'model_comparison': _cells({'source_length': ('match_state_count', "Source model's native LENG."), 'output_length': ('match_state_count', "Output model's native LENG."), 'length_difference': ('match_state_count', 'Saved output LENG minus source LENG.'), 'source_cell_count': ('decoded_probability_cell_count', 'Decoded source cells in common core distribution slots; separate HMMER2 configured fields remain retained.'), 'output_cell_count': ('decoded_probability_cell_count', 'Decoded output cells in common core distribution slots; separate HMMER2 configured fields remain retained.'), 'compared_cell_count': ('compared_probability_cell_count', 'Cells with comparable probabilities in the saved pair.'), 'max_absolute_probability_difference': ('absolute_probability_difference', 'Largest absolute output-minus-source difference among compared cells.'), 'mean_absolute_probability_difference': ('absolute_probability_difference_per_compared_cell', 'Sum of absolute differences divided by compared_cell_count; incomplete state is preserved.'), **{name + '_optional_field_count': ('optional_field_path_count', 'Count of saved optional field paths classified ' + name + '.') for name in ('retained', 'lost', 'changed', 'gained')}}), 'key_population': _cells({name: ('decoded_model_count' if name == 'returned_model_occurrence_count' else name, meaning) for name, meaning in {'requested_key_count': 'All requested key occurrences, including repetitions.', 'distinct_key_count': 'Distinct requested key strings.', 'resolved_key_count': 'Key associations whose saved state is resolved.', 'missing_key_count': 'Key associations whose saved state is missing.', 'ambiguous_key_count': 'Key associations whose saved state is ambiguous.', 'unknown_key_count': 'Key associations whose saved state is unknown.', 'fulfilled_key_count': 'Requested keys with validated returned model associations.', 'duplicate_key_occurrence_count': 'Requested occurrences minus distinct key strings.', 'selected_source_occurrence_count': 'Distinct source model occurrences selected by the saved key associations.', 'returned_model_occurrence_count': 'Decoded returned model occurrences; alias duplicates remain separate.', 'expected_returned_model_occurrence_count': 'Expected output occurrences from the actual indexed/unindexed retrieval semantics.', 'duplicate_representation_count': 'Matched returned source occurrences minus distinct source occurrences.'}.items()}), 'artifact': {**_cells({'size_bytes': ('byte', 'Actual retained bytes for this artifact occurrence.'), 'decoded_record_count': ('decoded_model_count', 'Shared decoded model count for supported source layouts; unsupported, malformed and partial population states stay explicit.')}), 'offset_width': _spec('byte', 'Native SSI offset width from its framing header.', cell=False)}, 'index_summary': _cells({**{'native_' + name: (name, 'Native reported index ' + name + '.') for name in ('model_count', 'primary_name_count', 'accession_count')}, **{'decoded_input_' + name: (unit, 'Decoded input ' + name + ' used in the native-summary comparison.') for name, unit in (('model_count', 'decoded_model_count'), ('primary_name_count', 'primary_name_occurrence_count'), ('accession_count', 'accession_occurrence_count'))}, **{name + '_difference': (name, 'Native reported minus decoded input ' + name + '.') for name in ('model_count', 'primary_name_count', 'accession_count')}}), 'bundle': _cells({'member_count': ('present_bundle_member_count', 'Captured pressed bundle member occurrences.'), 'bundle_byte_sum': ('byte', 'Sum of captured .h3m/.h3i/.h3f/.h3p bytes; partial sums keep incomplete state.')})}
_A_NATIVE = {'artifact_metadata': _native({'measured_size_bytes': ('byte', 'Byte count measured by the saved reader.'), 'offset_width': ('byte', 'Native SSI offset width when its header was decoded.'), 'decoded_record_count': ('decoded_model_count', 'Saved framing-only decoded count; this reader does not infer binary contents.')}), 'requested_key': {}, 'reported_path': {}, 'diagnostic': {}, 'index_summary': _native({name: ('count', 'Native index summary ' + name + '.') for name in ('model_count', 'primary_name_count', 'accession_count')})}
_A_CHECKS = set('parameters_valid supplied_bytes_match_occurrence capture_complete model_population_complete conversion_population_equal model_relationship model_probability_equivalence expected_revision required_member_present member_nonempty binary_framing binary_internal_content supplied_artifact_binding authenticated_artifact_custody bundle_supplied_attempt_consistency bundle_revision_consistent native_model_count native_primary_name_count native_accession_count source_primary_names_unique source_accessions_unique requested_keys_unique all_requested_keys_resolved all_requested_keys_returned fetch_output_population native_diagnostics conversion_stdout_equal'.split())
_B_UNITS = {'input_sequence_count': 'sequence_count', 'input_column_count': 'alignment_column_count', 'rf_consensus_count': 'RF_consensus_column_count', 'resaved_sequence_count': 'sequence_count', 'resaved_column_count': 'resaved_alignment_column_count', 'model_length': 'match_state_count', 'model_alignment_fraction': 'match_states_per_input_alignment_column', 'effective_sequence_count': 'effective_sequence_count', 'effective_input_sequence_ratio': 'effective_sequences_per_input_sequence', 'native_relative_entropy': 'bit_per_match_position', 'mean_match_entropy': 'bit_per_match_position', 'mean_match_relative_entropy': 'bit_per_match_position', 'requested_interval_count': 'request_interval_count', 'requested_union_count': 'distinct_alignment_column_count', 'actual_masked_count': 'alignment_column_count', 'newly_masked_count': 'alignment_column_count', 'removed_masked_count': 'alignment_column_count', 'retained_masked_count': 'alignment_column_count', 'masked_fraction': 'masked_columns_per_input_alignment_column', 'input_masked_count': 'alignment_column_count', 'input_alignment_count': 'decoded_alignment_record_count', 'processed_alignment_count': 'output_validated_alignment_record_count', 'unprocessed_alignment_count': 'decoded_unprocessed_alignment_record_count', 'mapped_model_position_count': 'model_position_count', 'native_mapping_row_count': 'decoded_mapping_row_count'}
_B_MEANINGS = {'input_sequence_count': 'Sequence rows in the source alignment.', 'input_column_count': 'Source alignment width before Plan7 resaving.', 'rf_consensus_count': 'Non-gap RF columns in the source alignment.', 'resaved_sequence_count': 'Sequence rows in the separately saved output alignment.', 'resaved_column_count': 'Width in the separate resaved alignment coordinate system.', 'model_length': 'Native output model LENG.', 'model_alignment_fraction': 'Saved model match states divided by source alignment columns.', 'effective_sequence_count': 'Native output model EFFN.', 'effective_input_sequence_ratio': 'Saved output EFFN divided by source sequence count.', 'native_relative_entropy': 'Native printed build re/pos, separate from the independent KL calculation.', 'mean_match_entropy': 'Saved mean match entropy across all declared model positions.', 'mean_match_relative_entropy': 'Saved mean match KL against the explicitly supplied background.', 'requested_interval_count': 'Number of selected range occurrences, including overlaps.', 'requested_union_count': 'Distinct source alignment columns in the union of requested inclusive spans; mapping mode leaves this unmeasured.', 'actual_masked_count': 'Columns carrying m in the output MM annotation.', 'newly_masked_count': 'Output masked columns absent from source MM.', 'removed_masked_count': 'Source masked columns absent from output MM.', 'retained_masked_count': 'Intersection of source and output masked columns.', 'masked_fraction': 'Saved output masked-column count divided by source alignment width.', 'input_masked_count': 'Source MM masked columns; native absent MM means an empty mask.', 'input_alignment_count': 'Decoded source alignment records; unsupported population remains unknown.', 'processed_alignment_count': 'Source alignment record with validated native output; attempted selection alone is not completion.', 'unprocessed_alignment_count': 'Decoded source alignment records remaining after validated processing of the first record.', 'mapped_model_position_count': 'Positions in the saved deterministic model-to-source-alignment map.', 'native_mapping_row_count': 'Decoded native mapping rows; an existing empty output has zero rows with its saved qualification.'}
_B_BUILD_NAMES = set('input_sequence_count input_column_count rf_consensus_count resaved_sequence_count resaved_column_count model_length model_alignment_fraction effective_sequence_count effective_input_sequence_ratio native_relative_entropy mean_match_entropy mean_match_relative_entropy'.split())
_B_MASK_NAMES = set(_B_UNITS) - _B_BUILD_NAMES | {'input_sequence_count', 'input_column_count', 'rf_consensus_count'}
_B_CALC = {kind: _cells({name: (_B_UNITS[name], _B_MEANINGS[name]) for name in names}, 'components.') for kind, names in (('build', _B_BUILD_NAMES), ('mask', _B_MASK_NAMES), ('mapping', _B_MASK_NAMES - set('actual_masked_count newly_masked_count removed_masked_count retained_masked_count masked_fraction input_masked_count'.split())))}
_B_CALC['mapping']['components.requested_union_count']['unit'] = 'alignment_column_count'
_B_CALC['build'].update({'model_components.' + name: value for name, value in _MODEL_COMPONENTS.items()})
_B_CHECKS = set('artifact_binding source_geometry output_geometry association summary_counts summary_eff_nseq summary_relative_entropy source_checksum model_map rf_model_length sequence_membership sequence_content alignment_width mask_annotation requested_ranges range_capacity native_mapping model_components parameter_valid input_population_processed output_symbol_changes fragment_marking alphabet'.split())
_E_CALC = {'generated_record': _cells({'length': ('residue_count', 'Generated ASCII letter residues, excluding gaps, stop and missing symbols.'), 'canonical_residue_count': ('residue_count', "Generated residues in the saved model's canonical alphabet."), 'ambiguous_residue_count': ('residue_count', 'Generated BJZX amino or RYMKSWBDHVN nucleotide residues.'), 'noncanonical_unambiguous_residue_count': ('residue_count', 'Generated amino O/U residues, separately retained.'), 'ambiguous_fraction': ('fraction_of_ungapped_residues', 'Saved ambiguity count divided by positive generated residue length.'), 'gap_count': ('gap_count', "Generated alignment '-', '.' and '_' symbols."), 'stop_count': ('stop_symbol_count', "Generated '*' symbols."), 'missing_symbol_count': ('missing_data_symbol_count', "Generated '~' symbols."), 'invalid_symbol_count': ('symbol_count', 'Generated symbols outside the saved alphabet and recognized special symbols.')}), 'model': _cells({'input_model_length': ('model_match_state_count', "Input model's native declared length."), 'selected_N': ('requested_sample_count', 'Explicit selected -N, separately missing in consensus mode.'), 'configured_expected_length': ('configured_expected_residue_count', 'Explicit -L profile expected length; not a measured generated length.'), 'captured_sample_count': ('captured_generated_record_count', 'Generated records associated with this exact model occurrence.'), 'expected_output_count': ('expected_generated_record_count', 'Saved count expected from consensus mode or explicit -N.'), 'count_difference': ('captured_minus_expected_record_count', 'Captured records minus expected generated records.'), 'total_length': ('residue_count', 'Sum of lengths of associated captured generated records.'), 'minimum_length': ('residue_count', 'Minimum associated generated record length.'), 'maximum_length': ('residue_count', 'Maximum associated generated record length.'), 'mean_length': ('residues_per_captured_record', 'Sum of generated lengths divided by captured record count.')}), 'alignment': _cells({'alignment_width': ('alignment_column_count', 'Width of the captured generated alignment.'), 'rf_match_column_count': ('rf_match_column_count', 'Non-gap generated RF columns.'), 'captured_row_count': ('captured_generated_record_count', 'Rows in the captured generated alignment.')}), 'consensus': _cells({'mismatch_count': ('nominal_consensus_mismatch_count', 'Native consensus disagreements with the saved nominal maximum-probability choices, including length difference.'), 'certain_mismatch_count': ('certain_consensus_mismatch_count', 'Native symbols outside all choices allowed by explicit rounding tolerance, including length difference.'), 'ambiguous_position_count': ('decoded_ambiguous_position_count', 'Decoded positions with multiple possible choices under the supplied tolerance.')})}
_E_CHECKS = {'sample_population_count', 'alignment_geometry', 'rf_matches_model_length', 'consensus_agreement', 'consensus_length'}
_S_SUMMARY_UNITS = {name: 'inverse_bit' if name in {'lambda', 'plambda'} else 'dimensionless' if name == 'tailp' else 'sequence' if name.startswith('E10') else 'trace_state' if name in {'almean', 'alsd'} else 'bit' for name in 'tailp mu lambda E10 mufix E10fix mufix2 E10fix2 pmu plambda E10p almean alsd'.split()}
_S_SUMMARY_MEANINGS = {'tailp': 'Native selected fitting tail probability mass.', 'mu': 'Native fitted Gumbel location or Forward exponential tail threshold.', 'lambda': 'Native fitted inverse-bit scale.', 'E10': 'Native expected count at the tenth highest generated score under the independent fit.', 'mufix': 'Native location with fixed lambda.', 'E10fix': 'Native expected count at the tenth score using fixed lambda.', 'mufix2': 'Native location using native calibrated lambda.', 'E10fix2': 'Native expected count using native calibrated lambda.', 'pmu': "Native printed calibration location; Hybrid's undetermined state is preserved.", 'plambda': 'Native printed calibrated inverse-bit scale.', 'E10p': 'Native expected count at the tenth score using printed calibration.', 'almean': 'Native mean M+D+I trace-state count.', 'alsd': 'Native sample standard deviation of M+D+I trace-state counts.'}
_S_CALC = {'native_summary': _cells({name: (unit, _S_SUMMARY_MEANINGS[name]) for name, unit in _S_SUMMARY_UNITS.items()}, 'components.'), 'native_rounding_residuals': _cells({name: (unit, 'Saved independent minus native printed ' + name + '; original sign and comparison qualification are retained.') for name, unit in _S_SUMMARY_UNITS.items() if name not in {'tailp', 'pmu', 'plambda'}}, 'components.'), 'score_statistics': _cells({'observed_count': ('sequence', 'Decoded generated score occurrences, separate from selected -N.'), 'declared_population': ('sequence', 'Explicit selected -N denominator.'), 'mean': ('bit', 'Saved complete-population score sum divided by observed_count.'), 'min': ('bit', 'Minimum complete-population generated score.'), 'max': ('bit', 'Maximum complete-population generated score.'), 'sample_variance': ('bit_squared', 'Saved squared score residual sum divided by observed_count minus one.'), 'x10': ('bit', 'Tenth highest score occurrence, retaining ties; requires ten occurrences.')}, 'components.'), 'fit': _cells({'mu': ('bit', 'Saved fit-variant location; Gumbel ML or selected Forward tail threshold.'), 'lambda': ('inverse_bit', 'Saved fit-variant inverse-bit scale; original variant and calibration remain in retained data.'), 'survival_at_x10': ('dimensionless', 'Saved fitted survival at the tenth highest score.'), 'E10': ('sequence', 'Saved population times effective tail mass times survival at the tenth score.'), 'tail_mass': ('dimensionless', 'Explicit selected tail mass for this saved fit row.'), 'tail_count': ('sequence', 'Selected tail occurrence count; Forward uses floor(N*tail_mass).'), 'tail_threshold': ('bit', 'Smallest score in the selected tail population.')}, 'components.'), 'alignment_statistics': _cells({'observed_count': ('sequence', 'Observed native traceback rows in this occurrence/model group.'), 'alignment_mean': ('trace_state', 'Saved mean native M+D+I trace-state count.'), 'alignment_sample_sd': ('trace_state', 'Saved sample standard deviation of native M+D+I counts.')}, 'components.')}
for _kind in ('filter_recalculation', 'native_experimental_filter_replay', 'native_filter'):
    _S_CALC[_kind] = _cells({'count': ('sequence', 'Saved generated-score passing occurrence count for this declared filter variant.'), 'fraction': ('dimensionless', 'Saved passing count divided by explicit -N.')}, 'components.')
_S_CALC['native_filter']['components.rounding_residual'] = _spec('dimensionless', 'Saved count/N minus native printed passing fraction.')
_S_CHECKS = {'native_rounding.' + name for name in _S_SUMMARY_UNITS if name not in {'tailp', 'pmu', 'plambda'}} | {'hybrid_native_experimental_filter_count', 'native_filter_count', 'alignment_score_correspondence', 'native_filter_fraction'}
_H_CALC = _cells({**{name: (spec['unit'], spec['meaning']) for name, spec in _MODEL_COMPONENTS.items() if name in {'sequence_count', 'effective_sequence_count', 'effective_sequence_ratio', 'mean_match_entropy', 'mean_match_relative_entropy'}}, 'background_entropy': ('bit', 'Saved -sum(q log2 q) for the explicitly supplied background.'), 'mean_match_information': ('bit_per_match_position', 'Saved background entropy minus mean model match entropy.'), 'occupancy_sum': ('expected_match_state_count', 'Saved sum of match-state occupancy from model transitions.'), 'entry_occupancy_sum': ('expected_match_state_count', 'Saved occupancy sum over positions 2 through M.'), 'weighted_emission_relative_entropy': ('bit_per_occupied_match_state', 'Saved occupancy-weighted match KL divided by positive occupancy sum.'), 'mean_entry_transition_term': ('bit_per_occupied_entry_state', 'Saved weighted entry-transition log terms divided by entry occupancy, using explicit length probability.'), 'position_relative_entropy': ('bit_per_match_position', 'Saved weighted emission relative entropy plus mean entry-transition term.'), 'composition_weight_sum': ('expected_emission_mass', 'Saved sum of occupancy-weighted model emission masses.'), 'composition_relative_entropy': ('bit', 'Saved normalized weighted composition KL against the explicit background.')}, 'components.')
_F_DATABASE = {'source_occurrence_count': ('sequence_occurrences', 'Decoded source FASTA sequence occurrences.'), 'source_artifact_count': ('artifacts', 'Supplied original source artifact occurrences.'), 'source_symbol_total': ('source_symbols', 'Sum of decoded source sequence symbol counts.'), 'stored_segment_count': ('segments', 'Decoded FM segment metadata rows; unknown when body decoding is unavailable.'), 'distinct_target_count': ('source_target_ids', 'Distinct native source target IDs in decoded segments.'), 'declared_total_char_count': ('source_symbols_excluding_block_overlap', 'Native total_char_count header excluding repeated block overlap.'), 'actual_database_bytes': ('bytes', 'Actual captured database bytes, including headers and arrays.'), 'indexed_symbols': ('index_symbols_including_block_overlap', 'Saved sum of forward block N-1, including overlap.'), 'indexed_unique_symbols': ('index_symbols_excluding_block_overlap', 'Saved sum of forward block N-1-overlap.'), 'sentinel_count': ('logical_text_block_sentinels', 'Decoded forward blocks, each with one logical sentinel.'), 'stored_bwt_sentinel_count': ('stored_section_sentinels', 'Decoded forward/reverse BWT sections, each with one sentinel.'), 'ambiguity_range_count': ('stored_ranges', 'Decoded ambiguity metadata ranges.'), 'covered_source_symbols': ('source_symbols', 'Saved union length of validated source-coordinate segment intervals.'), 'ambiguity_union_symbols': ('source_symbols', 'Saved source-coordinate ambiguity union length.'), 'ambiguity_fraction': ('fraction', 'Saved ambiguity union symbols divided by positive source_symbol_total.')}
_F_CALC = {'database_summary': _cells(_F_DATABASE, 'components.'), 'block_validation': _cells({'bwt_symbol_mismatch_count': ('symbols', 'Saved LF-cycle preceding-symbol mismatches against retained text.'), 'lf_visited_rows': ('rows', 'Number of distinct BWT rows visited in the saved full LF consistency check.')}, 'details.'), 'segment_validation': _cells({'compared_symbols': ('symbols', 'Source segment symbols compared outside recorded ambiguous positions.'), 'mismatching_symbols': ('symbols', 'Compared source/index symbol disagreements.')}, 'components.'), 'location_validation': _cells({'native_anchor': ('one_based_source_coordinate', 'Native f/r anchor in supplied source coordinates.'), 'query_length': ('symbols', 'Saved literal query symbol length.'), 'interval_start': ('one_based_source_coordinate', 'Saved inclusive source interval start.'), 'interval_end': ('one_based_source_coordinate', 'Saved inclusive source interval end; reverse direction is reversal without complement.')}, 'components.'), 'query_validation': _cells({name + '_location_count': ('location_occurrences', 'Saved ' + name + ' locations for this exact query occurrence.') for name in ('valid', 'invalid', 'unresolved')}, 'components.')}
_F_EXACT = {'query_occurrence_count': ('query_occurrences', 'Supplied literal query line occurrences, preserving duplicates.'), 'native_Q': ('query_occurrences_with_native_locations', 'Native query occurrences with emitted locations; count-only uses raw intervals.'), 'native_H': ('native_emitted_location_occurrences', 'Native emitted location occurrences; count-only uses raw FM intervals.'), 'native_R': ('query_occurrences_with_no_raw_interval', 'Native query occurrences without a raw interval.'), 'native_unclassified_queries': ('query_occurrences', 'Saved query count minus native_Q minus native_R, retaining negative/failed values.'), 'emitted_location_count': ('emitted_location_occurrences', 'Decoded native location rows; absent in count-only mode.'), **{name + '_location_count': ('emitted_location_occurrences', 'Saved ' + name + ' classifications among emitted location occurrences.') for name in ('valid', 'invalid', 'unresolved')}, 'duplicate_location_count': ('repeated_resolved_tuple_occurrences', 'Repeated resolved (query, source, direction, anchor) tuple occurrences.'), **{name + '_location_fraction': ('fraction', 'Saved ' + name + ' location count divided by positive emitted_location_count.') for name in ('valid', 'invalid', 'unresolved')}, 'expected_literal_location_count': (['literal_source_location_occurrences', 'location_occurrences'], 'Saved exhaustive literal-source location count when explicitly calculated; missing otherwise.'), 'missing_literal_location_count': ('location_occurrences', 'Saved expected-minus-emitted tuple multiset count when explicitly compared.'), 'extra_literal_location_count': ('location_occurrences', 'Saved emitted-minus-expected tuple multiset count when explicitly compared.')}
_F_CALC['exactmatch_summary'] = _cells(_F_EXACT, 'components.')
_F_DATABASE_CHECKS = {'source_custody', 'decoded_layout', 'dna_reader_compatibility', 'metadata_partition', 'total_char_count'}
_F_EXACT_CHECKS = {'native_query_population', 'native_location_count', 'native_location_query_count', 'count_only_has_no_locations', 'exhaustive_literal_agreement'}
_F_CHECKS = _F_DATABASE_CHECKS | _F_EXACT_CHECKS | set('decoded_array_symbols bwt_text_consistency suffix_samples counter_rows sentinel_encoding block_offsets paired_block_metadata ambiguity_bounds block_segment_coverage segment_coordinates segment_name source_symbols_outside_ambiguities source_ambiguity_membership block_overlap source_coverage hit_bounds hit_symbols hit_ambiguity hit_index_membership hit_source_name hit_duplicate_tuple'.split())

def _definitions(program, mode):
    if type(program) is not str or program not in PROGRAM_MODES or type(mode) is not str or (mode not in PROGRAM_MODES[program]):
        _error('program_mode_invalid')
    family = _FAMILIES[program]
    if family == 'artifact':
        kinds = {name: deepcopy(value) for name, value in _A_CALC.items() if name in {'population', 'artifact'} or (name == 'bundle' and program == 'hmmpress') or (name == 'index_summary' and mode == 'index') or (name == 'model_comparison' and mode != 'index') or (name == 'key_population' and program == 'hmmfetch' and (mode != 'index'))}
        return ({'input_records': {'model': _MODEL}, 'output_records': {'model': _MODEL}, 'native_rows': _A_NATIVE, 'calculations': kinds}, _A_CHECKS)
    if family == 'alignment_preparation':
        kind = 'build' if program == 'hmmbuild' else 'mask' if mode.startswith('mask_') else 'mapping'
        coordinate = 'one_based_model_position' if mode in {'mask_model', 'model_to_alignment'} else 'one_based_alignment_column'
        target = 'one_based_alignment_column' if mode == 'model_to_alignment' else 'one_based_model_position'
        native = {'population': {'decoded_count': _spec('decoded_alignment_record_count', 'Saved decoded alignment-record population; unsupported remains unknown.', cell=False, state='state')}}
        if program == 'hmmbuild':
            native['build_summary'] = _native({'nseq': ('sequence_count', 'Native reported source sequence count.'), 'alen': ('alignment_column_count', 'Native source alignment columns.'), 'mlen': ('match_state_count', 'Native output model match positions.'), 'W': ('residue_count', 'Native maximum expected hit length.'), 'eff_nseq': ('effective_sequence_count', 'Native effective training sequence count.'), 're_per_position': ('bit_per_match_position', 'Native printed model relative entropy per position.')})
        else:
            native['requested_interval'] = _native({name: (coordinate, 'Selected inclusive ' + name + ' in the declared source coordinate system.') for name in ('start', 'end')})
            if kind == 'mapping':
                native['mapping'] = _native({name: (target if name.startswith('target_') else coordinate, 'Native or requested inclusive ' + name + '; coordinate system is fixed by this operation mode.') for name in ('requested_start', 'requested_end', 'returned_source_start', 'returned_source_end', 'target_start', 'target_end')})
        align = _native({'column_count': ('alignment_column_count', 'Saved native alignment width.'), 'block_count': ('alignment_block_count', 'Saved interleaved alignment block count.')})
        return ({'input_records': {'alignment': align}, 'output_records': {'alignment': align, 'model': {}}, 'native_rows': native, 'calculations': {kind: _B_CALC[kind]}}, _B_CHECKS)
    if family == 'emission':
        kinds = {'generated_record': _E_CALC['generated_record'], 'model': _E_CALC['model']}
        if mode.startswith('consensus_'):
            kinds['consensus'] = _E_CALC['consensus']
        if mode == 'sample_core_aligned':
            kinds['alignment'] = _E_CALC['alignment']
        out = {'alignment': _native({'native.column_count': ('alignment_column_count', 'Saved generated Stockholm width.'), 'native.block_count': ('alignment_block_count', 'Saved generated Stockholm block count.')}), 'alignment_row': {}} if mode == 'sample_core_aligned' else {'fasta': {}}
        return ({'output_records': out, 'native_rows': {name: {} for name in ('line', 'fasta_header', 'fasta_sequence', 'header', 'terminator', 'sequence', 'GC', 'GR', 'GS', 'GF', 'comment', 'blank', 'invalid')}, 'calculations': kinds}, _E_CHECKS)
    if family == 'statistics':
        native = _native({'nseq': ('sequence_count', 'Native reported training sequence count.'), 'eff_nseq': ('effective_sequence_count', 'Native reported effective sequence count.'), 'M': ('match_state_count', 'Native reported model length.'), 'relent': ('bit_per_match_position', 'Native mean model relative entropy.'), 'info': ('bit_per_match_position', 'Native mean model information.'), 'p_relE': ('bit_per_match_position', 'Native position relative entropy.'), 'compKL': ('bit', 'Native model composition KL.')}, 'values.', 'states.')
        return ({'native_rows': {'model_statistic': native}, 'calculations': {'model_statistic': _H_CALC}}, {'native_rounding_agreement'})
    if family == 'simulation':
        summary = {name: (unit, _S_SUMMARY_MEANINGS[name]) for name, unit in _S_SUMMARY_UNITS.items() if mode != 'forward' or name not in {'mufix2', 'E10fix2'}}
        native = {'summary': _native(summary, 'payload.values.', 'payload.states.'), 'scores': _native({'declared_population': ('sequence', 'Explicit -N for this generated vector.'), 'observed_count': ('sequence', 'Actually decoded vector count; unavailable without the original ABI.')}, 'payload.'), 'alignments': _native({'trace_state_count': ('trace_state', 'Native M+D+I trace-state count.'), 'score': ('bit', 'Native printed generated alignment score.')}, 'payload.', 'payload.states.'), 'filter': {**_native({'count': ('sequence', 'Native passing score occurrences.'), 'fraction': ('dimensionless', 'Native printed passing fraction.')}, 'payload.', 'payload.states.'), 'payload.denominator': _spec('sequence', 'Explicit -N filter denominator.', cell=False)}, 'xy_series': {}}
        calc = deepcopy(_S_CALC)
        if mode == 'forward':
            for kind in ('native_summary', 'native_rounding_residuals'):
                for name in ('mufix2', 'E10fix2'):
                    calc[kind].pop('components.' + name, None)
        if mode != 'viterbi':
            calc.pop('alignment_statistics')
        if mode != 'hybrid':
            calc.pop('native_experimental_filter_replay')
        return ({'input_records': {'model': _MODEL}, 'native_rows': native, 'calculations': calc}, _S_CHECKS)
    calc = deepcopy(_F_CALC)
    native = {'diagnostic': {}, 'index_parameters': {'payload.value': _spec(['index_symbol_count', 'suffix_array_sampling_interval'], 'Native bin_length or suffix array sample rate only; categorical parameter rows have no numeric value.', state='payload.state', cell=False)}}
    if program == 'makehmmerdb':
        for name in ('exactmatch_summary', 'location_validation', 'query_validation'):
            calc.pop(name)
    else:
        if mode == 'count_only':
            calc['exactmatch_summary']['components.native_Q']['unit'] = 'query_occurrences_with_raw_interval'
            calc['exactmatch_summary']['components.native_H']['unit'] = 'raw_fm_interval_occurrences'
        native.update(exactmatch_hit=_native({'anchor': ('one_based_source_coordinate', 'Native f/r source anchor; reversal has no complement.')}, 'payload.'), exactmatch_counts=_native({name: (calc['exactmatch_summary']['components.native_' + name]['unit'], 'Original native ' + name + ' count for the selected locations/count-only population.') for name in ('Q', 'H', 'R')}, 'payload.'))
    return ({'input_records': {'fasta': {}, **({'query': {}} if program != 'makehmmerdb' else {})}, 'native_rows': native, 'calculations': calc}, _F_CHECKS)

def preparation_projection_catalog(program, mode):
    """Closed scalar field/meaning catalogue; no values are discovered at runtime."""
    definitions, checks = _definitions(program, mode)
    result = {}
    for collection, kinds in definitions.items():
        quantities = {}
        for kind, fields in kinds.items():
            for path, spec in fields.items():
                descriptor = quantities.setdefault(path, {'unit': [], 'meaning': [], 'source': []})
                descriptor['unit'].extend(spec['unit'] if type(spec['unit']) is list else [spec['unit']])
                descriptor['meaning'].append(kind + ': ' + spec['meaning'])
                descriptor['source'].append(('calculations.rows' if collection == 'calculations' else 'sheet.' + collection) + '/' + kind + '/' + path)
        for descriptor in quantities.values():
            units = sorted(set(descriptor['unit']))
            descriptor['unit'] = units[0] if len(units) == 1 else units
            descriptor['meaning'] = ' '.join(descriptor['meaning'])
            descriptor['source'] = '; '.join(descriptor['source'])
        result[collection] = {'quantities': dict(sorted(quantities.items())), 'checks': sorted(checks)}
    return result
_ALL_PATHS = sorted({path for program, modes in PROGRAM_MODES.items() for mode in modes for entry in preparation_projection_catalog(program, mode).values() for path in entry['quantities']})
_ALL_CHECKS = sorted(_A_CHECKS | _B_CHECKS | _E_CHECKS | _S_CHECKS | _F_CHECKS | {'native_rounding_agreement'})
_ALL_KINDS = sorted({kind for program, modes in PROGRAM_MODES.items() for mode in modes for kinds in _definitions(program, mode)[0].values() for kind in kinds})
_ALL_UNITS = sorted({unit for program, modes in PROGRAM_MODES.items() for mode in modes for kinds in _definitions(program, mode)[0].values() for fields in kinds.values() for spec in fields.values() for unit in (spec['unit'] if type(spec['unit']) is list else [spec['unit']])})
_ALL_ROLES, _ALL_FORMATS = (set(), set())
for _program, _modes in PROGRAM_MODES.items():
    for _mode in _modes:
        for _contract in (operand_contract, output_contract):
            for _mapping in _contract(_program, _mode):
                _ALL_ROLES.update(_mapping)
                for _formats in _mapping.values():
                    _ALL_FORMATS.update(_formats)

def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

def _reference(namespace, *, identifier=False, nullable=False):
    return {'type': ['string', 'null'] if nullable else 'string', 'format': 'identifier' if identifier else 'reference', 'x-reference-namespace': namespace}
_SOURCE = _reference('execution_result')
_ARTIFACT = _reference('artifact')
_KEY = _reference('native_hmmer_preparation_row', identifier=True)
_SELECTION = _object({'direction': {'type': 'string', 'enum': list(_DIRECTIONS)}, 'role': {'type': 'string', 'enum': sorted(_ALL_ROLES)}, 'ordinal': {'type': 'integer', 'minimum': 0}})
_WINDOW = {'oneOf': [_object({'offset': {'type': 'integer', 'minimum': 0}, 'limit': {'type': 'integer', 'minimum': 1}}), _object({'record_keys': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': _KEY}})]}
_PROJECTION = _object({'collection': {'type': 'string', 'enum': list(_COLLECTIONS)}, 'rows': _WINDOW, 'quantities': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'enum': _ALL_PATHS}}, 'checks': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'enum': _ALL_CHECKS}}})
NATIVE_HMMER_PREPARATION_RESULT_SELECTOR_SCHEMA = _object({'version': {'const': 'native_hmmer_preparation_result_selector_v1'}, 'acquisition': {'const': 'complete_bound_bundle'}, 'projection': {'oneOf': [_PROJECTION, {'type': 'null'}]}, 'artifacts': {'type': 'array', 'uniqueItems': True, 'items': _SELECTION}})
NATIVE_HMMER_PREPARATION_RESULT_SELECTOR_SCHEMA['anyOf'] = [{'properties': {'artifacts': {'minItems': 1}}}, {'properties': {'projection': {'type': 'object', 'anyOf': [{'properties': {'quantities': {'minItems': 1}}}, {'properties': {'checks': {'minItems': 1}}}]}}}]
_CHECK_OCCURRENCE = _object({**_SELECTION['properties'], 'artifact_ref': _ARTIFACT})
ROW_SCHEMA = _object({'record_key': _KEY, 'kind': {'type': 'string', 'enum': _ALL_KINDS}, 'name': _reference('native_hmmer_preparation_name', identifier=True, nullable=True), 'accession': _reference('native_hmmer_preparation_accession', identifier=True, nullable=True), 'source_ref': _SOURCE, 'artifact_ref': _reference('artifact', nullable=True), 'quantities': {'type': 'array', 'items': _object({'path': {'type': 'string', 'enum': _ALL_PATHS}, 'value': {'type': ['number', 'null']}, 'state': {'type': 'string', 'enum': sorted(_STATES)}, 'unit': {'type': ['string', 'null'], 'enum': [*_ALL_UNITS, None]}})}, 'checks': {'type': 'array', 'items': _object({'name': {'type': 'string', 'enum': _ALL_CHECKS}, 'outcome': {'type': 'string', 'enum': sorted(_OUTCOMES)}, 'occurrences': {'type': 'array', 'items': _CHECK_OCCURRENCE, 'uniqueItems': True}})}})
ARTIFACT_SCHEMA = _object({'source_ref': _SOURCE, **_SELECTION['properties'], 'artifact_ref': _ARTIFACT, 'format': {'type': 'string', 'enum': sorted(_ALL_FORMATS)}, 'size_bytes': {'type': 'integer', 'minimum': 0}, 'sha256': _reference('native_hmmer_preparation_sha256', identifier=True), 'completeness': {'type': 'string', 'enum': ['complete', 'partial', 'unknown']}})
POPULATION_SCHEMA = _object({'source_ref': _SOURCE, 'collection': {'type': ['string', 'null'], 'enum': [*_COLLECTIONS, None]}, **{name: {'type': 'integer', 'minimum': 0} for name in ('total_records', 'returned_records', 'omitted_records', 'requested_artifact_count', 'returned_artifact_count')}, 'missing_record_keys': {'type': 'array', 'items': _KEY, 'uniqueItems': True}, 'missing_artifacts': {'type': 'array', 'items': _SELECTION, 'uniqueItems': True}})
FAILURE_STAGES = ('software', 'inputs', 'staging', 'preflight', 'execution', 'outputs', 'capture', 'prerequisite', 'custody', 'metadata', 'native', 'reading', 'worker', 'extraction', 'parsing', 'calculation', 'grading', 'projection', 'selection', 'format', 'association', 'validation', 'unclassified')
FAILURE_SCHEMA = _object({'handoff_ref': _reference('execution_handoff'), 'source_ref': _reference('execution_result', nullable=True), 'stage': {'type': 'string', 'enum': list(FAILURE_STAGES)}, 'code': _reference('native_hmmer_preparation_failure_code', identifier=True), 'record_key': _reference('native_hmmer_preparation_failure_record', identifier=True, nullable=True), 'affected': {**_SELECTION, 'type': ['object', 'null']}})
IDENTIFIER_NAMESPACES = tuple(('native_hmmer_preparation_' + name for name in ('row', 'name', 'accession', 'sha256', 'failure_code', 'failure_record')))

def preparation_fact_sources():
    descriptions = {'rows': (ROW_SCHEMA, 'Requested saved numerical measurements and checks with exact row and artifact associations; generated values remain generated.'), 'artifacts': (ARTIFACT_SCHEMA, 'Explicitly requested artifact occurrences and those required by selected rows/checks, preserving same-byte separate roles.'), 'population': (POPULATION_SCHEMA, 'Decoded saved row and selected artifact accounting; this is not biological completeness.'), 'result_refs': (_SOURCE, 'Original HMMER preparation result references.'), 'failures': (FAILURE_SCHEMA, 'Recorded typed acquisition, grading or projection failures with their original handoff and affected occurrence.')}
    return {'execution_hmmer_preparation_' + name: {'type': 'array', 'meaning': meaning, 'report_schema': {'type': 'array', 'items': deepcopy(schema), 'x-source': 'execution_hmmer_preparation_' + name}} for name, (schema, meaning) in descriptions.items()}

def _unique_text_list(value, code):
    if type(value) is not list:
        _error(code)
    for item in value:
        _text(item)
    if len(set(value)) != len(value):
        _error('duplicate_request')

def _selection(value, program, mode):
    _fields(value, {'direction', 'role', 'ordinal'}, 'artifact_selection_fields_invalid')
    _integer(value['ordinal'])
    if value['direction'] not in _DIRECTIONS:
        _error('artifact_direction_invalid')
    required, optional = (output_contract if value['direction'] == 'output' else operand_contract)(program, mode)
    roles = {**required, **optional}
    if value['role'] not in roles or (value['direction'] == 'working_copy' and (not (value['role'] == 'models' and (program == 'hmmpress' or (program == 'hmmfetch' and mode == 'index'))))):
        _error('artifact_role_not_in_operation')
    return (value['direction'], value['role'], value['ordinal'])

@_contract_errors('selector_structure_invalid')
def validate_preparation_result_selector(value, *, program, mode):
    """Validate exact typed selections without adding a default result window."""
    catalog = preparation_projection_catalog(program, mode)
    _finite_json(value)
    _fields(value, {'version', 'acquisition', 'projection', 'artifacts'}, 'selector_fields_invalid')
    if value['version'] != 'native_hmmer_preparation_result_selector_v1' or value['acquisition'] != 'complete_bound_bundle':
        _error('selector_version_or_acquisition_invalid')
    if type(value['artifacts']) is not list:
        _error('artifact_selections_list_required')
    selected = [_selection(item, program, mode) for item in value['artifacts']]
    if len(set(selected)) != len(selected):
        _error('duplicate_artifact_request')
    projection = value['projection']
    if projection is not None:
        _fields(projection, {'collection', 'rows', 'quantities', 'checks'}, 'projection_fields_invalid')
        if type(projection['collection']) is not str or projection['collection'] not in catalog:
            _error('collection_not_in_operation')
        entry = catalog[projection['collection']]
        for name in ('quantities', 'checks'):
            _unique_text_list(projection[name], 'requested_fields_list_required')
            if set(projection[name]) - set(entry[name]):
                _error('field_not_in_operation_collection')
        window = projection['rows']
        if type(window) is dict and set(window) == {'offset', 'limit'}:
            _integer(window['offset'])
            _integer(window['limit'], 1)
        else:
            _fields(window, {'record_keys'}, 'row_selection_invalid')
            _unique_text_list(window['record_keys'], 'record_keys_list_required')
            if not window['record_keys']:
                _error('record_keys_nonempty_required')
    if not value['artifacts'] and (projection is None or (not projection['quantities'] and (not projection['checks']))):
        _error('empty_selection')
    return deepcopy(value)

def _kind(row, family, collection):
    if family == 'statistics':
        return 'model_statistic'
    if family in {'artifact', 'simulation'} and collection in {'input_records', 'output_records'}:
        return 'model'
    kind = row.get('kind')
    _text(kind)
    return kind
