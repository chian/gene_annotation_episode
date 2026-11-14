"""Pure supplied-measurement CD sheets and inspectable source heuristics.

Inputs are JSON records with ``schema``, optional ``sample_key``, ``sample_type``
(``protein`` or ``nucleic_acid``), ``spectrum`` and optional ``thermal``. Spectrum
records contain ordered ``wavelength_data``/``cd_signal_data`` arrays,
``wavelength_unit='nm'`` and an explicit ``signal_unit``. Thermal records contain
ordered ``temperature_data``/``thermal_cd_data`` arrays, ``temperature_unit='degC'``,
``signal_unit`` and optional nullable ``measurement_wavelength_nm``. Signal units
are ``mdeg``, ``delta_epsilon`` or explicitly ``unknown``; no conversion occurs.
Numeric operands have an explicit binary64 interpretation. Integers that cannot
be represented exactly in binary64 are retained but unavailable to calculation.

This is componentwise calculation of the Biomni source's descriptive arithmetic,
not execution of that function. Counts are sampled-point counts, not structure
fractions. Min/max normalization is relative signal, not an unfolding fraction.
The sampled midpoint and source width/labels are not fitted melting parameters.
No calibration, baseline, concentration, uncertainty or confidence is invented.
There is no acquisition, file access, fitting, native call or episode behavior.
"""
from __future__ import annotations
QUALIFICATIONS = ['source_labels_are_heuristics_not_calibrated_secondary_structure', 'sign_counts_depend_on_supplied_baseline_sampling_density_and_duplicates', 'no_baseline_or_calibration_correction_performed', 'relative_signal_is_not_a_measured_unfolded_fraction', 'sampled_midpoint_is_not_a_fitted_melting_temperature', 'source_width_uses_endpoint_difference_and_N_points_not_N_minus_1_intervals', 'no_replicate_uncertainty_or_gene_function_probability']
SPECTRAL_FEATURES = {'protein': (('alpha_helix_sign_count', 190, 195, 'positive'), ('beta_sheet_sign_count', 215, 220, 'negative'), ('random_coil_sign_count', 195, 200, 'negative')), 'nucleic_acid': (('g_quadruplex_sign_count', 290, 300, 'positive'), ('b_form_sign_count', 270, 280, 'positive'))}
