# Specificity qualification of the conditional TyrA cells

This additive precision note applies to the `f` and `g` rows in
`SOURCE_TO_CANONICAL_CELLS_001.md` and `CANONICAL_INPUT_SCENARIOS_001.json`.
It does not amend the A104 formula or resolve an original assay identity.

**A cofactor appearing in Table4 is not, by itself, evidence of exclusive
cofactor specificity.** The narrow-profile conversion additionally relies on
the source's explicit specificity statements in the Results subsection
*Specificity for the pyridine nucleotide co-substrate within the TyrA
superfamily*. That subsection describes NAD specificity as the property of
the rigorously characterized P. stutzeri and P. aeruginosa examples, then
contrasts Acinetobacter's NADP specificity with the Pseudomonas/Azotobacter
sister group. The exact source terms are “NAD+-specific” and “NADP+-specific”.
[Song et al., specificity Results](https://pmc.ncbi.nlm.nih.gov/articles/PMC1173090/).

The finite dimension used by the conditional narrow examples is:

| Dimension | Allowed resolved classes | Unresolved case |
|---|---|---|
| Cofactor profile | NAD+-specific; NADP+-specific; both accepted | An assay lists one cofactor without establishing the other's exclusion |
| Cyclohexadienyl substrate acceptance | Both PPA and AGN accepted; PPA only; AGN only; a specified different profile | A reported broad family label or uncharacterized member |

Here `f` is the joint **NAD+-specific / both PPA and AGN** class, and `g` is
**NADP+-specific / both PPA and AGN**. These classes are mutually incompatible
on cofactor specificity. The broader `h` retains only positive use of both PPA
and AGN; it requires no cofactor restriction and no claim that all other
substrates were excluded. Cofactor-specific labels and unknown extra biological
activities are different scopes; the latter are not silently excluded.

The observed source evidence is a reported experimental assignment in this
comparative paper. **Original selective assays, tested concentration ranges,
negative readouts, detection limits and quantitative selectivity were not
independently inspected.** Thus this packet does not claim those numerical
measurements exist in the inspected table or that a strict selectivity threshold
has been verified. Its narrow C examples condition on accepting the paper's
reported specificity classification **as well as** the source-to-tip mappings.
They are not unconditional experimentally revalidated specificity scores.

The source-to-cell chain is therefore:

```text
Table4 positive substrate/cofactor assignments
 + explicit Results specificity assignments
 + declared assay/core-to-tip mapping scenario
 -> canonical joint function sets {f}/{g}
 -> existing counts and B_f
 -> C_f=2/5 in P5, or C_f=0 for known heterogeneity in PA6.
```

If only Table4's positive cofactor-use entries are admitted, or if the reported
selectivity assignments are not accepted as established at this resolution,
the **narrow-profile specimen above is not populated**: preserve the unmeasured
alternative-cofactor response and the incomplete class mapping. Do not label
those activity-only rows `{f}` or `{g}`, or report the illustrated PA6 zero as
known functional heterogeneity. This limitation concerns which class inputs
are available; it does not create a numeric selectivity weight or alter `C`.
The broader positive PPA/AGN-use assertion and its conditional3/6 calculation
remain separately traceable to the reported activity assignments.

The existing sixteen enumerated identity scenarios in `ARITHMETIC_RESULTS_001`
condition on the reported specificity interpretation. They do not assign a
probability to that interpretation or resolve its original assay evidence.
`unknown_operands` for an unconditional narrow result therefore also includes
the scope/measurement support for an exclusive cofactor assertion, in addition
to the original assay-to-tip correspondence. No unconditional narrow or whole
A104 point is supplied by these records.
