"""The extracted record of ONE bio-layer interferometry (BLI) experiment.

What a leaf extraction holds for one BLI experiment (one set of sensorgrams, or replicate sensors reported as one
result), in the same operand shape as the SPR and ITC records and the existing A105 assay grading inputs (value,
unit, status, reason, measurement_keys, source_refs, origin, native_component). A value the source did not give is an
operand with status 'unavailable', value None and a reason; it is never 0 and never omitted. The plain constructors
point, unavailable and fact are the SPR record module's; they are shared because they only build operands.

BLI differs from SPR in what the instrument does: the response is a wavelength shift in nanometres (nm), not
resonance units; the sensor tips are dipped into wells that are shaken, not perfused, so there is no flow cell and
no flow-based mass-transport test, but the loaded ligand density drives avidity and rebinding; each sensor is a
separate physical object (sensor-to-sensor variation, usually a single use), and the dissociation step is a fixed
window whose length decides whether koff can be measured. The form keeps exactly those things.

Record fields
-------------
version, experiment_type ('bli'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref (the protein in the well), immobilized_preparation_ref (the partner loaded on
               the sensor), sensor_ref (the sensor or sensor lot), dataset_ref: each a string or None (unknown).
               The converter hands them to the merger as its dependence keys (sensor_ref as the surface key).
quantities     kd, kd_steady_state, kon, koff, response_max, kd_spread, fit_r_squared, loading_level,
               dissociation_time, replicate_count: one operand each.
               Units: kd/kd_steady_state/kd_spread nM, uM or mM; kon M^-1 s^-1; koff s^-1; response_max and
               loading_level nm (the wavelength shift); fit_r_squared dimensionless (the R-squared of the fit, at
               most 1); dissociation_time s or min (the length of the dissociation step); replicate_count count.
concentration_series
               operand whose 'value' is a list of analyte concentrations (unit nM, uM or mM), or None when not given.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None. What kd_spread is.
fit_model      '1:1', '2:1_bivalent_analyte', 'heterogeneous_ligand', 'steady_state', 'other' or None.
biosensor_type 'streptavidin', 'anti_his', 'ni_nta', 'protein_a', 'protein_g', 'anti_human_fc', 'anti_gst',
               'amine_reactive', 'other' or None. The sensor surface chemistry; kept in the record for the reviewer
               and for the sensor identity, no criterion judges it.
facts          name -> {'answer', 'source_refs'}. Names and answer sets in FACTS below. No fact holds text: a
               controlled answer only.
choice_support name -> support of each plain choice field (spread_kind, fit_model, biosensor_type), None when the field is not
               stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_spr_record import SUPPORTS, fact, point, unavailable   # support: see literature_spr_record (every stated value carries 'support'; the constructors default it to 'direct' for forms built outside the extraction)

VERSION = 'a105_bli_record_v1'
EXPERIMENT_TYPE = 'bli'
QUANTITIES = ('kd', 'kd_steady_state', 'kon', 'koff', 'response_max', 'kd_spread', 'fit_r_squared', 'loading_level', 'dissociation_time', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'sensor_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
FIT_MODELS = ('1:1', '2:1_bivalent_analyte', 'heterogeneous_ligand', 'steady_state', 'other')
BIOSENSOR_TYPES = ('streptavidin', 'anti_his', 'ni_nta', 'protein_a', 'protein_g', 'anti_human_fc', 'anti_gst', 'amine_reactive', 'other')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'reference_sensor_subtracted': YES_NO, 'buffer_reference_subtracted': YES_NO, 'baseline_stable': YES_NO, 'loading_step_documented': YES_NO, 'regeneration': YES_NO, 'independent_sensors': YES_NO, 'immobilized_partner_active': YES_NO, 'analyte_bivalent_or_oligomeric': YES_NO, 'avidity_rebinding_considered': YES_NO, 'mass_transport_considered': YES_NO, 'nonspecific_binding_checked': YES_NO, 'single_estimate_method': YES_NO}

CONCENTRATION_UNITS = ('nM', 'uM', 'mM')
# The unit vocabulary of each quantity (and of the concentration series): the units a record may carry.
UNITS = {'kd': CONCENTRATION_UNITS, 'kd_steady_state': CONCENTRATION_UNITS, 'kon': ('M^-1 s^-1',), 'koff': ('s^-1',), 'response_max': ('nm',), 'kd_spread': CONCENTRATION_UNITS, 'fit_r_squared': ('dimensionless',), 'loading_level': ('nm',), 'dissociation_time': ('s', 'min'), 'replicate_count': ('count',), 'concentration_series': CONCENTRATION_UNITS}
