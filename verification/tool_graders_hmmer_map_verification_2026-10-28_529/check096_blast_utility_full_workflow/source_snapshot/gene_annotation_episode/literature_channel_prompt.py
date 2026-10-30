"""Detailed electrical-assay TASK; numerical sheets and STEERING are separate.

This constant preserves the parent's seven-paragraph proposal. It is not yet
installed in an episode binding; a future binding must supply it in full on
each applicable decision, with the actual parent assignment and typed return.
"""

CHANNEL_TASK = """Determine what the reported membrane-current or ion-release experiment establishes about the studied molecule's transport activity and ion specificity. Identify the actual organism, protein construct, preparation, membrane system, ion composition, experimental arrangement and measured endpoint. Distinguish purified reconstitution from cellular measurements. Establish whether compared molecules replace one another or coexist; preserve additional changes beyond the intended variable.

For electrical measurements, identify whether each value is a signed current, current-step magnitude, applied voltage, reversal voltage, reported conductance or occupancy measurement. Preserve the voltage convention, grounded side, ion gradient and baseline definition. Keep salt-gradient and biionic measurements distinct. A common paper or protein name does not establish that two operands belong to the same measurement arrangement.

Establish what the observed unit represents. Distinguish a protein-containing insertion packet, a conducting unit, a polypeptide and a pore. Preserve unresolved oligomer or pore assignments. Do not turn event counts, bilayer counts, time points or histogram samples into independent protein preparations.

For ion-release measurements, distinguish accumulated release, a normalized release fraction and an initial flux. Identify initial, plateau and detergent-release measurements where available. Preserve dead time, detection limits, assumed vesicle dimensions and reported approximations. A response faster than instrument dead time supplies a limitation or bound, not an observed initial rate.

Examine whether the signal is attributable to the intended protein and ion. A closed-channel baseline is not a protein-free membrane control. Electrical current measures charge flow; converting it into flux of a specified ion requires the applicable charge and attribution relationship. Keep mixed contributions and missing controls explicit. Complementary electrical and chemical measurements can address different weaknesses without becoming independent replication automatically.

Preserve reported uncertainty, its declared meaning, independent preparation identities and shared measurements. Do not reinterpret an unspecified spread as SD, SEM or known sampling variance. Use covariance only with established measurement ownership. Occupancy and current amplitude may be combined only when their joint experimental meaning supports that calculation; preserve substates and missing joint relationships.

Nominate source-supported operands and their experimental relationships. Leave parsing, unit conversion and arithmetic to deterministic readers and calculators. Preserve reported and calculated values separately, including disagreements. Return the requested numerical components with their conditions, uncertainty, dependencies and unresolved limitations. Do not invent an overall reliability grade, annotation probability, target-transfer weight or missing value."""

__all__ = ["CHANNEL_TASK"]
