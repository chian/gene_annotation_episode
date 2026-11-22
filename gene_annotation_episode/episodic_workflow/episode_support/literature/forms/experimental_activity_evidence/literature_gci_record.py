"""The extracted record of ONE grating-coupled interferometry (GCI) experiment.

What a leaf extraction holds for one GCI experiment (for example on a Creoptix WAVE instrument): one binding
experiment, or replicate runs reported as one result, in the same operand shape as the SPR, ITC and BLI records and
the existing A105 assay grading inputs (value, unit, status, reason, measurement_keys, source_refs, origin,
native_component). A value the source did not give is an operand with status 'unavailable', value None and a reason;
it is never 0 and never omitted. The plain constructors point, unavailable and fact are the SPR record module's; they
are shared because they only build operands.

GCI differs from SPR and BLI in what the instrument does: a waveguide chip with an evanescent field gives a very
sensitive, flow-based mass signal (the response is a surface mass in pg/mm^2, or in response units RU), so the
immobilized amount is small and the sample consumption low; the signal tolerates the bulk and solvent (DMSO) effects
only after they are corrected with a reference channel and solvent-correction injections; the analyte is injected
in flow, so mass transport matters; and the waveRAPID mode replaces a concentration series with repeated short pulses
of one concentration, which makes fast kinetics measurable and so replaces the series rule. Each channel of a chip is
a surface of its own, but channels of one chip share the chip. The form keeps exactly those things.

Record fields
-------------
version, experiment_type ('gci'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref (the protein in the flow), immobilized_preparation_ref (the partner on the
               chip), chip_ref (the chip, or chip lot), dataset_ref: each a string or None (unknown).
               The converter hands them to the merger as its dependence keys (chip_ref as the surface key).
quantities     kd, kd_steady_state, kon, koff, response_max, kd_spread, immobilization_level, analyte_mass, ligand_mass,
               stoichiometry, dissociation_time, replicate_count: one operand each.
               Units: kd/kd_steady_state/kd_spread pM, nM, uM or mM; kon M^-1 s^-1; koff s^-1; response_max and
               immobilization_level pg/mm2, ng/mm2 or RU (the surface mass, or response units); analyte_mass and
               ligand_mass kDa (the molecular mass of the analyte in the flow and of the partner on the chip);
               stoichiometry dimensionless (analyte molecules per immobilized molecule, as the passage states it);
               dissociation_time s or min (the length of the dissociation phase after the analyte injection);
               replicate_count count.
concentration_series
               operand whose 'value' is a list of analyte concentrations (unit pM, nM, uM or mM), or None when not
               given. For waveRAPID it is the one concentration (or the few) pulsed.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None. What kd_spread is.
fit_model      '1:1', 'bivalent_analyte', 'heterogeneous_ligand', 'two_state', 'steady_state', 'other' or None.
chip_type      'planar_polycarboxylate', 'polycarboxylate_hydrogel', 'streptavidin', 'nta', 'other' or None. The
               chip's surface chemistry, kept in the record for the reviewer and the chip identity; no criterion
               judges it.
facts          name -> {'answer', 'source_refs'}. Names and answer sets in FACTS below. No fact holds text: a
               controlled answer only.
               binding_detected is the experiment's stated yes/no result (the passage
               says the two partners bound, or says they did not); no criterion reads
               it. It lets a result stated without a constant count (owner, 2026-11-22).
choice_support name -> support of each plain choice field (spread_kind, fit_model, chip_type), None when the field is not
               stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_spr_record import SUPPORTS, fact, point, unavailable   # support: see literature_spr_record (every stated value carries 'support'; the constructors default it to 'direct' for forms built outside the extraction)

VERSION = 'a105_gci_record_v1'
EXPERIMENT_TYPE = 'gci'
QUANTITIES = ('kd', 'kd_steady_state', 'kon', 'koff', 'response_max', 'kd_spread', 'immobilization_level', 'analyte_mass', 'ligand_mass', 'stoichiometry', 'dissociation_time', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'chip_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
FIT_MODELS = ('1:1', 'bivalent_analyte', 'heterogeneous_ligand', 'two_state', 'steady_state', 'other')
CHIP_TYPES = ('planar_polycarboxylate', 'polycarboxylate_hydrogel', 'streptavidin', 'nta', 'other')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'reference_channel_subtracted': YES_NO, 'double_referenced': YES_NO, 'bulk_solvent_corrected': YES_NO, 'baseline_stable': YES_NO, 'regeneration': YES_NO, 'independent_channels_or_chips': YES_NO, 'immobilized_partner_active': YES_NO, 'analyte_bivalent_or_oligomeric': YES_NO, 'mass_transport_checked': YES_NO, 'nonspecific_binding_checked': YES_NO, 'single_estimate_method': YES_NO, 'repeated_pulse_kinetics_used': YES_NO, 'binding_detected': YES_NO}

CONCENTRATION_UNITS = ('pM', 'nM', 'uM', 'mM')
MASS_UNITS = ('pg/mm2', 'ng/mm2', 'RU')
TIME_UNITS = ('s', 'min')
# The unit vocabulary of each quantity (and of the concentration series): the units a record may carry.
UNITS = {'kd': CONCENTRATION_UNITS, 'kd_steady_state': CONCENTRATION_UNITS, 'kon': ('M^-1 s^-1',), 'koff': ('s^-1',), 'response_max': MASS_UNITS, 'kd_spread': CONCENTRATION_UNITS, 'immobilization_level': MASS_UNITS, 'analyte_mass': ('kDa',), 'ligand_mass': ('kDa',), 'stoichiometry': ('dimensionless',), 'dissociation_time': TIME_UNITS, 'replicate_count': ('count',), 'concentration_series': CONCENTRATION_UNITS}
