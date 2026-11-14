"""Closed native projections of the gel reader's original numerical outputs."""
from copy import deepcopy as cp

from jsonschema import Draft202012Validator, ValidationError

from .communication import plain
from .domain import ContractError, canonical
from . import literature_gel_inputs as inputs
from . import literature_gel_calculations as calculations


PROVIDER = 'literature.a105.gel'
OPERATION = 'literature.gel.populate'
FACT_SOURCE = 'literature_gel_component_cells'
VERSION = 'literature_gel_record_v1'
FACT_VERSION = 'literature_gel_component_fact_v1'
RAW_COMPONENTS = ('pixel_count', 'sum_gray', 'sum_darkness', 'minimum_gray', 'maximum_gray', 'zero_gray_count')
CORRECTED_COMPONENT = 'background_corrected_band_darkness'
LANE_COMPONENTS = ('shifted_display_darkness', 'free_display_darkness', 'selected_total_display_darkness',
    'shifted_display_fraction', 'off_band_display_fraction', 'display_black_pixel_fraction',
    'display_total_ratio_to_protein_lane')
COMPARISON_COMPONENTS = ('protein_associated_display_shift', 'competitor_residual_display_fraction',
    'displaced_display_fraction', 'factorized_competitor_sensitive_shift', 'direct_competitor_sensitive_shift')
COMPONENTS = (*RAW_COMPONENTS, CORRECTED_COMPONENT, *LANE_COMPONENTS, *COMPARISON_COMPONENTS)
VIEWS = ('raw_region', 'corrected_band', 'lane', 'comparison', 'sensitivity')
REQUEST_COMPONENTS = 'requested_gel_components'
REQUEST_VIEWS = 'requested_gel_views'
REQUEST_KEYS = 'requested_gel_component_keys'
LANE_MEANINGS = ('subject', 'construct', 'endpoint', 'condition', 'control_role')


def obj(properties):
    return {'type':'object', 'properties':properties, 'required':list(properties), 'additionalProperties':False}


def nullable(schema):
    return {'anyOf':[schema, {'type':'null'}]}


def ref(name):
    return {'$ref':'#/$defs/'+name}


def arr(schema, **kw):
    return {'type':'array', 'items':schema, **kw}


def enum(*values):
    return {'enum':list(values)}


def record_reference(namespace='reference'):
    return {'type':'string', 'format':'reference', 'x-reference-namespace':namespace}


def gel_population_schema():
    return obj({'selection':{'anyOf':[inputs.gel_arguments_schema(),
        inputs.gel_arguments_schema(version=inputs.VERSION_V2)]},
        'comparison':calculations.gel_comparison_schema()})


def validate_population_arguments(arguments):
    value=plain(arguments)
    try:
        Draft202012Validator(gel_population_schema()).validate(value)
        canonical(value)
        selection=inputs.validate_gel_selection(value['selection'])
        comparison=calculations._comparison(value['comparison'], {'selection':selection})
    except (ValueError, TypeError, KeyError, ValidationError) as error:
        raise ContractError('gel_native_arguments_invalid') from error
    return {'selection':selection, 'comparison':comparison}


def gel_cells_schema():
    text={'type':'string','minLength':1}
    box=nullable({'type':'array','items':{'type':'integer'},'minItems':4,'maxItems':4})
    rational=obj({'numerator':{'type':'string','pattern':r'^-?(0|[1-9][0-9]*)$'},
        'denominator':{'type':'string','pattern':r'^[1-9][0-9]*$'}})
    qualifiers=('selected_background_overlaps_band','negative_background_corrected_band_retained',
        'display_fraction_outside_unit_interval_retained','display_diagnostic_not_calibrated_recovery',
        'display_black_pixels_do_not_establish_native_saturation','shared_measurements_not_independent_evidence',
        'displaced_display_fraction_outside_unit_interval_retained','baseline_cancels_from_direct_form',
        'cancellation_does_not_establish_baseline_measurement','same_physical_display_measurement_reused_nondiscriminating',
        'display_diagnostic_not_calibration_recovery')
    reasons=('region_not_selected','invalid_region','region_outside_image','unsupported_image_format',
        'unsupported_native_grayscale_mode','single_frame_required','unsupported_image_orientation','image_decode_failed',
        'band_role_not_selected','overlapping_band_regions','nonpositive_total_display_darkness',
        'bands_not_inside_whole_lane','nonpositive_whole_lane_display_darkness','comparison_lane_not_selected',
        'zero_protein_associated_display_shift','nonpositive_reference_total_display_darkness','no_available_values')
    formulas=tuple('selected_region_'+name for name in RAW_COMPONENTS)+(CORRECTED_COMPONENT,
        'sum_background_corrected_shifted_bands','sum_background_corrected_free_bands',
        'shifted_plus_free_display_darkness','shifted_divided_by_shifted_plus_free_display_darkness',
        'whole_lane_minus_selected_bands_divided_by_whole_lane','zero_gray_pixels_divided_by_selected_band_pixels',
        'protein_fraction_minus_baseline_fraction','competitor_fraction_minus_baseline_fraction',
        'protein_fraction_minus_competitor_fraction',
        'competitor_minus_baseline_divided_by_protein_minus_baseline',
        'one_minus_competitor_residual_display_fraction','protein_associated_shift_times_displaced_fraction',
        'selected_total_divided_by_protein_lane_selected_total','explicit_available_assignment_minimum_maximum')
    meaning=obj({'state':enum('known','unknown','conflicting'),
        'value_ref':nullable(record_reference()),'witness_refs':arr(record_reference())})
    meaning['allOf']=[{'if':{'properties':{'state':{'const':'known'}}},
        'then':{'properties':{'value_ref':record_reference(),'witness_refs':{'minItems':1}}},
        'else':{'properties':{'value_ref':{'type':'null'}}}}]
    diagnostics=[role+'_'+name+'_'+state for role in ('baseline','protein','competitor')
        for name in LANE_MEANINGS for state in ('unknown','conflicting')]
    diagnostics += [role+'_lane_not_selected' for role in ('baseline','protein','competitor')]
    diagnostics += ['protein_competitor_'+name+'_mismatch' for name in ('subject','construct','endpoint')]
    diagnostics += [role+'_role_does_not_establish_requested_experimental_meaning' for role in ('baseline','protein','competitor')]
    D={
        'Rational':rational,
        'Meaning':meaning,
        'Lane':obj({'lane_id':text,'observation_id':text,**{name:ref('Meaning') for name in LANE_MEANINGS}}),
        'Interpretation':obj({'status':enum('unknown','conflicting','descriptive_only'),'reasons':arr(enum(*diagnostics)),
            'comparability_outside_intended_change':{'const':'not_established_by_display_arithmetic'},
            'effect_isolation':{'const':'not_established_by_display_arithmetic'}}),
        'Dependence':obj({'same_image':{'const':True},'baseline_reused_in_factorized_form':{'type':'boolean'},
            'direct_baseline_coefficient':{'const':0},'independence_established':{'const':False},
            'factorization_equal_to_direct':nullable({'type':'boolean'})}),
        'SourceDependency':obj({'source_ref':record_reference('source'),'artifact_ref':text,
            'image_byte_sha256':{'type':'string','pattern':'^[0-9a-f]{64}$'},'lane_id':text,
            'signal_region':box,'background_region':box}),
        'Sensitivity':obj({'kind':{'const':'explicit_available_roi_assignment_range_not_sampling_interval'},
            'status':enum('complete','partial','no_available_values'),'bounds_unavailable_assignments':{'const':False},
            'included_assignment_ids':arr(text),'unavailable_assignment_ids':arr(text),
            'sampling_confidence_level':{'type':'null'}}),
    }
    # V1 dependencies have no background method; V2 retains that original field.
    v2=cp(D['SourceDependency']);v2['properties']['background_method']=enum('mean','median');v2['required'].append('background_method')
    D['SourceDependency']={'oneOf':[D['SourceDependency'],v2]}
    D['Dependency']=obj({'assignment_id':text,'source_dependency':ref('SourceDependency')})
    D['Cell']=obj({'value':{'type':['number','null']},'exact':nullable(ref('Rational')),
        'lower':nullable(ref('Rational')),'upper':nullable(ref('Rational')),
        'unit':enum('display_fraction','display_darkness_sum','pixel_count','gray_level','gray_level_sum'),
        'formula':enum(*formulas),'status':enum('measured','calculated','unavailable','available_range'),
        'unavailable_reason':nullable(enum(*reasons)),
        'projection_reason':nullable(enum('numerical_projection_range')),
        'qualifications':arr(enum(*qualifiers)),'sampling_standard_uncertainty':{'type':'null'},
        'confidence_interval':{'type':'null'},'sensitivity':nullable(ref('Sensitivity'))})
    D['Science']=obj({'global':obj({name:ref('Meaning') for name in inputs.CONTEXT_FIELDS}),
        'lanes':arr(ref('Lane')),'comparison_roles':nullable(obj({role:nullable(text)
            for role in ('baseline','protein','competitor')})),
        'interpretation':nullable(ref('Interpretation')),
        'interpretation_basis':{'const':'investigating_episode_nominations'},
        'intensity_meaning':{'const':'selected_display_darkness_255_minus_gray'},
        'sampling_uncertainty':obj({'status':{'const':'not_supplied'},'value':{'type':'null'}}),
        'detector_response_calibration':obj({'status':{'const':'not_supplied'},'value':{'type':'null'}}),
        'unimplemented_quantities':arr(enum('calibrated_molecular_occupancy','binding_observation_likelihood')),
        'independent_preparation_count':{'type':'null'}})
    D['NumericLocation']={'oneOf':[obj({'kind':{'const':'image_region'},'source_ref':record_reference('source'),'region':box}),
        obj({'kind':{'const':'utf8_span'},'source_ref':record_reference('source'),'start':{'type':'integer','minimum':0},
            'end':{'type':'integer','minimum':1}}),
        obj({'kind':{'const':'unresolved'},'source_ref':record_reference('source')})]}
    D['Method']=obj({'assignment_id':text,'lane_id':text,'background_method':enum('mean','median'),
        'method_basis':enum('v1_mean_definition','explicit_v2_nomination')})
    row=obj({'version':{'const':FACT_VERSION},'sheet_ref':record_reference('source'),'component_key':text,
        'view':enum(*VIEWS),'component':enum(*COMPONENTS),'assignment_id':nullable(text),'lane_id':nullable(text),
        'region_kind':nullable(enum('background','whole_lane','band')),'band_id':nullable(text),
        'band_role':nullable(enum('shifted','free','other')),'cell':ref('Cell'),'scientific_context':ref('Science'),
        'numerical_dependencies':arr(ref('Dependency')),
        'dependence':arr(obj({'assignment_id':text,'source_dependence':ref('Dependence')})),
        'roi_methods':arr(ref('Method')),'origin':enum('graph_derived','synthetic'),
        'numeric_locations':arr(ref('NumericLocation'))})
    return {'$schema':'https://json-schema.org/draft/2020-12/schema','type':'array','items':row,'$defs':D,'x-source':FACT_SOURCE}


__all__=['PROVIDER','OPERATION','FACT_SOURCE','VERSION','FACT_VERSION','COMPONENTS','VIEWS',
    'RAW_COMPONENTS','CORRECTED_COMPONENT','LANE_COMPONENTS','COMPARISON_COMPONENTS','LANE_MEANINGS',
    'REQUEST_COMPONENTS','REQUEST_VIEWS','REQUEST_KEYS','gel_population_schema','gel_cells_schema','validate_population_arguments']
