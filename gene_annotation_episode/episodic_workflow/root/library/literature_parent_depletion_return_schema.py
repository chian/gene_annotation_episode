"""Original numerical return contract; no reader, calculator or repository activation."""
from gene_annotation_episode.domain import obj

COMPONENTS=('active_parent_removal','inactive_parent_removal','abiotic_parent_removal',
    'active_reported_sd','inactive_reported_sd','abiotic_reported_sd',
    'active_minus_inactive','active_minus_abiotic')
NAMESPACE='literature_parent_depletion_cells'
def parent_depletion_cells_schema():
    ref={'type':'string','format':'reference','x-reference-namespace':'source'}
    artifact={'type':'string','format':'reference','x-reference-namespace':'artifact'}
    text={'type':'string'}
    return {'type':'array','x-source':NAMESPACE,'items':obj({
        'sheet_ref':ref,'evidence_source_ref':ref,'workbook_artifact_ref':artifact,
        'component':{'type':'string','enum':list(COMPONENTS)},'evaluation_scope':{'type':'string','const':'finite_parent_compound_removal'},
        'value':{'type':'number'},'exact_decimal':text,'unit':{'type':'string','const':'fraction'},
        'status':{'type':'string','const':'point'},'origin':{'type':'string','enum':['reported','calculated']},
        'formula':text,'compound':text,'submix':text,'time_hours':{'type':'integer','minimum':0},
        'sheet_name':text,'row_number':{'type':'integer','minimum':1},
        'source_cell_addresses':{'type':'array','minItems':1,'maxItems':2,'items':text},
        'input_measurement_keys':{'type':'array','minItems':1,'maxItems':2,'items':text},
        'shared_active_observation_key':text,
        'normalization_status':{'type':'string','const':'source_relative_removal_denominator_raw_values_unavailable'},
        'repetition_basis':{'type':'string','const':'unknown'},'active_control_covariance':{'type':'string','const':'unknown'},
        'equal_mutant_protein_amount':{'type':'string','const':'unknown'},
        'product_identity_for_studied_enzyme':{'type':'string','const':'unknown'},
        'reported_sd_of_difference':{'type':'null'},'standard_error_of_difference':{'type':'null'},
        'difference_uncertainty_status':{'type':'string','const':'joint_replication_and_covariance_unknown'},
        'product_coupling_factor':{'type':'null'},'annotation_credit':{'type':'null'}})}


