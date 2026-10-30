# Preserve an unknown empty historical population

This additive correction leaves the original contract and all numerical
formulas unchanged. Root reread the immutable objective and all sixteen design
principles before accepting this interface correction.

`NativeCodonWorstSequenceRatios` gains one required field:

```text
missing_requirements: AcquisitionRequirement[]
```

An empty family list with unknown/partial/truncated completeness cannot be
distinguished from a known complete empty population through the existing empty
`genome_means`, `rows` and `family_maxima` arrays. Preserve that difference using
the already defined finite missing-input requirements. Do not create a dummy
family, genome, numerical score or observation to carry the distinction.

The new field contains the unique requirements arising from the explicit
evaluated family population, expected sequence membership and retained row
quantities for this calculation. Use the same IDs, kinds, roles and reasons
already fixed in CODON_CALCULATIONS_CONTRACT.md. Equal IDs must have equal
meanings. A known complete empty population has an empty requirement array;
unknown family completeness includes evaluated_family_population_required;
unknown expected sequence membership includes pretrim_sequence_population_required.
Ordinary row-level missing measurements keep their original requirements.
An incompatible observed value is not mislabeled as an acquisition need.

`codon_calculation_requirements` must resolve this field together with existing
quantity requirement IDs, without recalculation or I/O. The provider grader
merges these actual requirements into the saved component registry. Its later
requested projection still forwards only requirements relevant to that request.

Verify complete empty, unknown empty, partial empty and truncated empty inputs,
plus known families without supplied sequence rows. Their different meanings
must survive saved JSON replay. No changed scope, scientific scoring policy,
episode type, action, credit or continuation behavior is introduced.
