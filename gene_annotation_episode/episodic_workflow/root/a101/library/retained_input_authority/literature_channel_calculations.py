"""Pure electrical components for an explicitly interpreted source experiment.

Chord conductance combines current magnitude and driving voltage. It is neither
an I--V slope nor a reliability weight. Charge equivalents are not a specified
ion's flux. Source interpretation, source custody and later credit have other
owners; this module has no I/O or episode state.
"""
from __future__ import annotations
PRIMITIVE_ORDER = ('current', 'applied_voltage', 'reversal_voltage')
QUANTITIES = (*PRIMITIVE_ORDER, 'reported_conductance')
CURRENT_KINDS = ('signed_current', 'current_step_magnitude', 'unknown', 'conflicting')
ARRANGEMENT_RELATIONS = ('same_electrical_arrangement_supported', 'different_electrical_arrangements', 'unknown', 'conflicting')
COMPONENTS = (*QUANTITIES, 'absolute_driving_voltage', 'chord_conductance', 'charge_equivalent_rate', 'chord_conductance_variance', 'chord_conductance_standard_uncertainty')
UNITS = {'current': 'pA', 'applied_voltage': 'mV', 'reversal_voltage': 'mV', 'reported_conductance': 'pS', 'absolute_driving_voltage': 'mV', 'chord_conductance': 'pS', 'charge_equivalent_rate': 'elementary_charge_equivalents_per_s', 'chord_conductance_variance': 'pS_squared', 'chord_conductance_standard_uncertainty': 'pS'}
MEANINGS = {'current': 'Source current or current-step magnitude under the declared baseline; not an isolated ion flux.', 'applied_voltage': 'Source applied voltage under its retained sign convention.', 'reversal_voltage': 'Source reversal voltage under its own retained ionic conditions.', 'reported_conductance': 'Conductance reported by the source, separate from the defined chord calculation.', 'absolute_driving_voltage': 'Magnitude of applied minus applicable reversal voltage; the chord denominator.', 'chord_conductance': 'Current magnitude divided by driving-voltage magnitude under supported condition applicability; not differential conductance.', 'charge_equivalent_rate': 'Magnitude of electrical charge flow in elementary-charge equivalents per second; not ion identity, pore count or molecular turnover.', 'chord_conductance_variance': 'Conditional first-order variance of the defined chord from the supplied full primitive covariance.', 'chord_conductance_standard_uncertainty': 'Square root of conditional first-order chord variance; no confidence level is implied.'}
SECTIONS = {name: 'electrical_measurement' for name in QUANTITIES}
SECTIONS.update(absolute_driving_voltage="conditions_and_normalization",
                chord_conductance="conditions_and_normalization",
                charge_equivalent_rate="charge_attribution_limit",
                chord_conductance_variance="measurement_uncertainty",
                chord_conductance_standard_uncertainty="measurement_uncertainty")
