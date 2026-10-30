"""Build the reviewed 177/001+002 closed schema asset; development only."""
from copy import deepcopy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'candidate' / 'gene_annotation_episode'
native = json.loads((ROOT / 'bvbrc_proteome_directional_schemas.json').read_text())
def renamed(v):
    if isinstance(v, dict):
        return {k: ('#/$defs/Reader' + x[8:] if k == '$ref' else renamed(x)) for k, x in v.items()}
    if isinstance(v, list): return [renamed(x) for x in v]
    return v
D = {'Reader' + k: renamed(v) for k, v in native['$defs'].items()}
def ref(n): return {'$ref': '#/$defs/' + n}
def arr(n): return {'type': 'array', 'items': ref(n) if isinstance(n, str) else n}
def obj(**p): return {'type': 'object', 'properties': p, 'required': list(p), 'additionalProperties': False}
def enum(*v): return {'enum': list(v)}
def nullable(v): return {'anyOf': [ref(v) if isinstance(v, str) else v, {'type': 'null'}]}
N = {'type': 'integer', 'minimum': 0}
P = {'type': 'integer', 'minimum': 1}
S = {'type': 'string'}
BOOL = {'type': 'boolean'}
NULL = {'type': 'null'}
POINTER = {'type': 'string', 'pattern': r'^(?:/(?:[^~/]|~[01])*)*$'}
def fixed(s): return {'const': s}
for alias, original in {'NativeIntCell':'IntegerCell', 'NativeDecimalCell':'DecimalCell', 'NativeTextCell':'StringCell', 'ReaderTraceBlock':'TracebackBlock', 'ReaderResult':'DirectionalReportResult'}.items():
    D[alias] = ref('Reader' + original)
key_fields = ['report_ordinal','query_ordinal','subject_ordinal','hsp_ordinal','block_ordinal','column_ordinal']
for name, count in [('QueryKey',2),('SubjectKey',3),('HspKey',4),('BlockKey',5),('ColumnKey',6)]:
    D[name] = obj(**{k:deepcopy(N) for k in key_fields[:count]})
D['FieldRef'] = obj(report_ordinal=N,pointer=POINTER)
codes = '''invalid_input_contract invalid_parameters no_report_supplied native_reader_partial native_reader_failure source_body_incomplete source_object_completeness_unknown source_object_incomplete missing_native_count invalid_native_count zero_native_denominator count_exceeds_denominator incompatible_native_denominators identity_exceeds_paired_count positive_below_identity positive_exceeds_paired_count reported_count_traceback_conflict missing_traceback missing_traceback_symbols invalid_traceback_symbols traceback_width_conflict double_gap_column missing_coordinate invalid_coordinate reverse_protein_coordinates coordinate_span_conflict coordinate_outside_reported_length missing_reported_length invalid_reported_length block_continuity_conflict incomplete_displayed_geometry incomplete_displayed_strings native_denominator_extent_unknown native_denominator_extent_conflict alternative_query_mapping alternative_subject_mapping query_symbol_conflict subject_symbol_conflict query_gap_versus_pair_conflict subject_gap_versus_pair_conflict noncollinear_pair_order overlapping_hsp_occupied_positions zero_paired_population zero_resolved_population native_no_hit_with_displayed_population empty_without_native_no_hit descriptions_without_subject_blocks missing_native_score invalid_native_score printed_zero_expectation statistic_occurrences_disagree no_execution_or_occurrence_evidence semantic_context_missing semantic_context_conflict'''.split()
D['IssueCode'] = enum(*codes)
D['Issue'] = obj(code=ref('IssueCode'),fields=arr('FieldRef'),columns=arr('ColumnKey'),hsps=arr('HspKey'),argument_pointer=nullable(POINTER))
D['Support'] = obj(included_blocks=arr('BlockKey'),excluded_blocks=arr('BlockKey'),hsps_without_traceback=arr('HspKey'),complete_for_displayed_blocks=BOOL)
D['Interval'] = {'type':'array','prefixItems':[N,P],'items':False,'minItems':2,'maxItems':2}
D['ExactFraction'] = obj(numerator=N,denominator=P,decimal={'type':'string','pattern':r'^[01](?:\.[0-9]+)?$'})
units = 'alignment_column paired_column displayed_position coordinate_pair gap_run query_occurrence description_occurrence subject_occurrence hsp_occurrence block_occurrence pair_representation'.split()
for name, val, unit in [('CountCell',N,enum(*units)),('RatioCell',ref('ExactFraction'),fixed('fraction'))]:
    cell=obj(state=enum('value','missing','invalid','conflict','undefined'),value=nullable(val),unit=unit,inputs=arr('FieldRef'),reasons=arr('IssueCode'),uncertainty=NULL)
    cell['oneOf']=[{'properties':{'state':fixed('value'),'value':val}}, {'properties':{'state':enum('missing','invalid','conflict','undefined'),'value':NULL}}]
    D[name]=cell
D['HspObservation']=obj(key=ref('HspKey'),**{k:ref('NativeIntCell') for k in ('identity_count','identity_denominator','positive_count','positive_denominator','gap_count','gap_denominator','raw_score','expect_group_count')},**{k:ref('NativeDecimalCell') for k in ('identity_printed_percent','positive_printed_percent','gap_printed_percent','bit_score','expect')},method_text=ref('NativeTextCell'),traceback_blocks=arr('ReaderTraceBlock'))
D['SubjectObservation']=obj(key=ref('SubjectKey'),reported_length=ref('NativeIntCell'),defline_text=ref('NativeTextCell'),identifier_token=ref('NativeTextCell'),hsps=arr('HspObservation'))
D['QueryObservation']=obj(key=ref('QueryKey'),reported_length=ref('NativeIntCell'),header_text=ref('NativeTextCell'),identifier_token=ref('NativeTextCell'),no_hits_marker=ref('NativeTextCell'),boundary=enum('next_banner','next_query','eof_complete','eof_unconfirmed'),database_headers=arr('ReaderDatabaseHeader'),descriptions=arr('ReaderDescription'),statistics=arr('ReaderStatistic'),subjects=arr('SubjectObservation'))
D['ReportObservation']=obj(report_ordinal=N,report_key={'type':'string','minLength':1,'pattern':r'\S'},query_rows=arr('QueryObservation'))
D['DirectionalSheet']=obj(version=fixed('bvbrc_proteome_directional_sheet_v1'),reader_results=arr('ReaderResult'),reports=arr('ReportObservation'),diagnostics=arr('Issue'))
D['DirectionalCalculationParameters']=obj(version=fixed('bvbrc_proteome_directional_parameters_v1'),formula_version=fixed('displayed_blastp_correspondence_v1'),amino_acid_alphabet=enum('standard20','standard20_plus_uo'),ratio_decimal_places={'type':'integer','minimum':0,'maximum':30},rounding=fixed('half_even'))
D['AxisPosition']=obj(state=enum('position','gap','unavailable_coordinate'),value=nullable(N))
D['AxisPosition']['oneOf']=[{'properties':{'state':fixed('position'),'value':N}},{'properties':{'state':enum('gap','unavailable_coordinate'),'value':NULL}}]
D['Column']=obj(key=ref('ColumnKey'),query_symbol={'type':'string','pattern':r'^[A-Za-z*\-]$'},subject_symbol={'type':'string','pattern':r'^[A-Za-z*\-]$'},query_position=ref('AxisPosition'),subject_position=ref('AxisPosition'),kind=enum('query_gap','subject_gap','resolved_identical','resolved_substituted','unresolved_pair','stop_containing_pair'),displayed_symbol_equal=BOOL)
counts='alignment_columns paired_columns displayed_symbol_identical_pairs displayed_symbol_nonidentical_pairs resolved_amino_acid_pairs resolved_amino_acid_identical_pairs resolved_amino_acid_substituted_pairs unresolved_symbol_pairs stop_containing_pairs query_gap_columns subject_gap_columns query_gap_runs subject_gap_runs query_non_gap_symbols subject_non_gap_symbols'.split()
fractions='trace_symbol_identity_over_columns trace_symbol_identity_over_pairs trace_resolved_amino_acid_identity trace_resolved_pair_fraction trace_unresolved_pair_fraction trace_gap_fraction'.split()
D['TraceCounts']=obj(**{k:ref('CountCell') for k in counts})
D['TraceFractions']=obj(**{k:ref('RatioCell') for k in fractions})
D['PositionUnion']=obj(intervals=arr('Interval'),count=ref('CountCell'),reported_length=ref('NativeIntCell'),coverage=ref('RatioCell'),support=ref('Support'))
D['CoverageComponents']=obj(**{f'{axis}_{kind}_union':ref('PositionUnion') for kind in ('reported_interval','trace_occupied','trace_paired') for axis in ('query','subject')})
D['BlockComponents']=obj(key=ref('BlockKey'),counts=ref('TraceCounts'),fractions=ref('TraceFractions'),columns=arr('Column'),coverage=ref('CoverageComponents'),diagnostics=arr('Issue'))
D['ReportedFractions']=obj(**{k:ref('RatioCell') for k in ('reported_identity_fraction','reported_positive_fraction','reported_gap_fraction','reported_identity_among_paired_fraction')},reported_paired_column_count=ref('CountCell'),reported_nonidentical_paired_count=ref('CountCell'))
D['NativeScores']=obj(bit_score=ref('NativeDecimalCell'),raw_score=ref('NativeIntCell'),expect=ref('NativeDecimalCell'),expect_group_count=ref('NativeIntCell'),expectation_display=enum('positive_reported_decimal','printed_zero_precision_unknown','missing','invalid'))
D['HspComponents']=obj(key=ref('HspKey'),reported=ref('ReportedFractions'),native_scores=ref('NativeScores'),blocks=arr('BlockComponents'),trace_counts=ref('TraceCounts'),trace_fractions=ref('TraceFractions'),strings_support=ref('Support'),coverage=ref('CoverageComponents'),pair_geometry_support=ref('Support'),contiguous_blocks=enum('yes','no','unknown'),native_denominator_extent=enum('agrees','disagrees','unknown'),diagnostics=arr('Issue'))
D['PairEdge']=obj(query_position=N,subject_position=N,supports=arr('ColumnKey'),symbol_state=enum('consistent','conflicting'))
D['MappingConflict']=obj(code=enum('alternative_query_mapping','alternative_subject_mapping','query_symbol_conflict','subject_symbol_conflict','query_gap_versus_pair_conflict','subject_gap_versus_pair_conflict','noncollinear_pair_order','block_continuity_conflict'),columns=arr('ColumnKey'),query_intervals=arr('Interval'),subject_intervals=arr('Interval'))
D['CorrespondenceGraph']=obj(key=ref('SubjectKey'),edges=arr('PairEdge'),distinct_pair_count=ref('CountCell'),repeated_pair_occurrence_count=ref('CountCell'),pair_geometry_support=ref('Support'),conflicts=arr('MappingConflict'),mapping_state=enum('compatible_displayed_partial_map','observed_conflict','incomplete_geometry'))
D['CompatiblePairCounts']=obj(**{k:ref('CountCell') for k in ('identical_symbol_pairs','resolved_pairs','resolved_identical_pairs','resolved_substituted_pairs','unresolved_pairs','stop_containing_pairs')})
D['Extremum']=obj(state=enum('value','missing','invalid'),selected_field=nullable('FieldRef'),tied_hsps=arr('HspKey'),excluded_hsps=arr('HspKey'),reason_codes=arr('IssueCode'))
D['SubjectComponents']=obj(key=ref('SubjectKey'),displayed_hsp_count=ref('CountCell'),displayed_block_count=ref('CountCell'),hsps=arr('HspComponents'),coverage=ref('CoverageComponents'),correspondence=ref('CorrespondenceGraph'),compatible_pair_counts=ref('CompatiblePairCounts'),**{k:ref('RatioCell') for k in ('compatible_unique_pair_symbol_identity','compatible_unique_pair_resolved_identity','compatible_unique_pair_resolved_fraction','nonoverlapping_hsp_reported_identity_over_columns')},**{k:ref('CountCell') for k in ('nonoverlapping_hsp_reported_identity_count','nonoverlapping_hsp_reported_alignment_columns')},**{k:ref('Extremum') for k in ('maximum_reported_hsp_bit_score','maximum_reported_hsp_raw_score','minimum_reported_hsp_expectation')},diagnostics=arr('Issue'))
display='native_no_hit_claim alignments_displayed descriptions_only empty_without_native_no_hit_claim contradictory_native_no_hit_claim'.split()
D['QueryComponents']=obj(key=ref('QueryKey'),display_state=enum(*display),**{'displayed_'+k+'_count':ref('CountCell') for k in ('description','subject','hsp','block')},subjects=arr('SubjectComponents'),any_displayed_subject_query_paired_union=ref('PositionUnion'),diagnostics=arr('Issue'))
D['ReportComponents']=obj(report_ordinal=N,**{'displayed_'+k+'_count':ref('CountCell') for k in ('query','description','subject','hsp','block')},queries=arr('QueryComponents'),diagnostics=arr('Issue'))
used=['native_counts','traceback_symbols','traceback_coordinates','reported_lengths','amino_acid_alphabet']
unused=['database_expectations','native_alignment_scores','native_positives','native_midlines','description_scores','database_statistics','method_text']
D['DirectionalComponents']=obj(version=fixed('bvbrc_proteome_directional_components_v1'),formula_version=fixed('displayed_blastp_correspondence_v1'),sheet_sha256={'type':'string','pattern':'^[0-9a-f]{64}$'},parameters=ref('DirectionalCalculationParameters'),reports=arr('ReportComponents'),diagnostics=arr('Issue'),correspondence_used_inputs=fixed(used),correspondence_unused_retained_inputs=fixed(unused))
for name, payload in [('DirectionalSheet','sheet'),('DirectionalComponents','components')]:
    D[name+'Result']=obj(state=enum('available','partial','failure'),**{payload:nullable(name)},diagnostics=arr('Issue'))
    D[name+'Result']['oneOf']=[{'properties':{'state':fixed('failure'),payload:NULL,'diagnostics':{'minItems':1}}},{'properties':{'state':enum('available','partial'),payload:ref(name)}}]
D['DirectionalScoringSheet']=obj(version=fixed('bvbrc_proteome_directional_scoring_sheet_v1'),observed=ref('DirectionalSheet'),calculated=ref('DirectionalComponents'))
(ROOT / 'bvbrc_proteome_directional_numerical_schemas.json').write_text(json.dumps({'$schema':native['$schema'],'$defs':D},indent=2)+'\n')
