"""Original numerical return contract; no reader, calculator or repository activation."""
from gene_annotation_episode.domain import obj

COMPONENTS = ("reported_ratio", "difference_from_reference", "log_reported_ratio",
              "calibrated_amount_ratio", "amount_adjusted_effect",
              "source_profile_log_ratio", "source_signed_index")
REASONS = ("no_ratio_observations", "source_measurement_unavailable",
           "source_representation_conflict", "incomplete_conflicting_representations",
           "zero_reported_ratio", "numerical_model_range",
           "amount_calibration_unreported", "response_model_unreported",
           "uncertainty_model_unreported")
SIGNALS = ('protein_band','transcript_signal','other_reported_signal','unknown')
REFERENCES = ('tagged_wt_complementation','endogenous_wt','other_reported_reference','unknown','conflicting')
ARRANGEMENTS = ('single_preparation','replacement','coexistence','not_applicable','unknown','conflicting')
BINDINGS = {'subject_ref':'reference','variant_ref':'reference','comparison_reference_ref':'reference'}


def ratio_cells_schema():
    reference={'type':'string','format':'reference','x-reference-namespace':'source'}
    properties={'sheet_ref':dict(reference),'evidence_source_ref':dict(reference),
        'component':{'type':'string','enum':list(COMPONENTS)},'value':{'type':['number','null']},
        'value_candidates':{'type':'array','uniqueItems':True,'items':{'type':'number'}},
        'candidate_basis':{'type':'string','enum':['received_source_representations']},
        'raw_representation_roster_complete':{'type':'boolean'},
        'unit':{'type':['string','null'],'enum':['fraction','dimensionless',None]},
        'status':{'type':'string','enum':['populated','conflicting','unavailable']},
        'origin':{'type':'string','enum':['reported','synthetic','visual_transcription','derived','proposed']},
        'unavailable_reason':{'type':['string','null'],'enum':[None,*REASONS]},
        'conditional_on':{'type':'array','items':{'type':'string','enum':['source_interpretation']}},
        'uncertainty_kind':{'type':'string','enum':['unreported']},
        'independent_preparation_count':{'type':['integer','null'],'minimum':0},
        'source_origins':{'type':'array','uniqueItems':True,'items':{'type':'string','enum':['reported','synthetic','visual_transcription']}},
        'interpretation_kind':{'type':'string','enum':['episode_source_interpretation']},
        'signal_kind':{'type':'string','enum':list(SIGNALS)},'reference_role':{'type':'string','enum':list(REFERENCES)},
        'arrangement':{'type':'string','enum':list(ARRANGEMENTS)}}
    for name,namespace in BINDINGS.items():
        properties[name]={'type':['string','null'],'format':'reference','x-reference-namespace':namespace}
    return {'type':'array','items':obj(properties),'x-source':'literature_ratio_cells'}
