"""Pure dispatch for supplied HMMER outputs and numerical scoring sheets.

Resource selection and acquisition remain with the owning episode. These
functions select actual native formats, populate sheets and calculate their
components. They perform no I/O, reference lookup, submission or observation.
"""
from __future__ import annotations
HMMER_DOMAIN_METRICS = ('model_length', 'sequence_length', 'model_span_positions', 'sequence_span_residues', 'sequence_envelope_residues', 'model_span_coverage', 'sequence_span_coverage', 'sequence_envelope_coverage', 'paired_positions', 'insert_positions', 'delete_positions', 'alignment_columns', 'paired_model_coverage', 'paired_sequence_coverage', 'sequence_identity_fraction', 'consensus_identity_fraction', 'alignment_identity_fraction', 'api_identity_fraction', 'native_domain_score_bits', 'native_domain_bias_bits', 'native_conditional_evalue', 'native_independent_evalue', 'native_accuracy', 'posterior_lower_mean', 'posterior_upper_mean')
