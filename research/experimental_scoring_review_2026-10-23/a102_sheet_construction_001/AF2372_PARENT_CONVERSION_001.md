# AF2372: measured structural similarity and its scoring conversion

New parent research record. No historical records or production scoring are changed.
This does not finish A102 or adopt a score transformation.

## Comparison and source coverage

Stieglitz et al., *Crystal structure of a dual activity IMPase/FBPase
(AF2372) from Archaeoglobus fulgidus*, JBC (2002),
DOI 10.1074/jbc.M201042200, PMID 11940584.

The target-side structure is AF2372 from Archaeoglobus fulgidus. The comparison
is MJ0109 from Methanococcus jannaschii. These are structures of separate
proteins, not an experiment mixing both proteins or replacing one with a mutant.
Each monomer has 252 residues. The paper reports a SEQUOIA superposition of
209 positions with RMSD 1.5 angstrom. The narrative does not supply the exact
paired positions, atom set, chain pair, or structure-state pair for this result.
MJ0109 structure 1DK4 was used as a molecular-replacement probe; that does not
establish that it was the exact operand of the reported comparison. The
structure-solution relationship is also relevant to independence.

Parent inspected the complete extracted primary text, lines 0–798, including
Methods, Results, tables available as text, captions, and references, retained
as sources/AF2372_extracted_primary_lines.txt. The extraction covers 799 unique
line numbers; an initial cross-page-line parsing omission was repaired before
the remaining text was read. Table V's numerical matrix remains an image that
the browser screenshot did not return in an inspectable form. It was not read.
The two retained AF2372 conversion packets were also read. Their interpretations
are not adopted as source measurements.

After these reads the complete required authority set was reread. Groups 1–5
were completed before context compaction. Group 6's output was lost at that
boundary and was repeated: research AGENTS.md, SOURCE_CORRECTIONS.md,
A105_REVIEW_ASSIGNMENTS_2026-10-23_001.md, then the active goal attachment and
the latest human direction. No other primary paper was opened between this
reset and the present conversion.

## Native numerical cells

| Cell | Value | Meaning and limit |
|---|---:|---|
| Target sequence length | 252 residues | Whole monomer; not an atom count |
| Reference sequence length | 252 residues | Whole monomer; not an atom count |
| Reported aligned extent | 209 positions | Pair map is not supplied here |
| Reported RMSD | 1.5 angstrom | Exact comparison atom denominator is unavailable |
| Target coverage | 209/252 = 0.829365079365 | Derived from reported aligned extent and length |
| Reference coverage | 209/252 = 0.829365079365 | Same denominator in this example only |
| Positions outside reported extent | 43 per sequence | Does not identify disorder, missing coordinates, or functional divergence |

Do not calculate atomic sum of squared errors as 209 times RMSD squared: the
209 residue/position count is not a documented atom count. Do not invent a
TM-score from this RMSD or assume a local functional-site comparison occurred.

## Explicit proposed transformation, with its scale exposed

For this RMSD-and-extent descriptor, the worker proposed:

    coverage = aligned_positions / max(target_length, reference_length)
    geometric_match = 1 / (1 + (rmsd / half_response_distance)^2)
    structural_descriptor = coverage * geometric_match

The distance is expressed in the same unit as RMSD. It is an unadopted scoring
parameter, not a measured error bar or a fact supplied by the paper. At 2
angstrom, geometric_match = 0.64 and structural_descriptor = 836/1575 =
0.530793650794. Changing both distance units from angstrom to nanometres must
leave this output unchanged.

| Half-response distance | Geometric match | Structural descriptor |
|---|---:|---:|
| 1 angstrom | 4/13 | 209/819 = 0.255189255189 |
| 2 angstrom | 16/25 | 836/1575 = 0.530793650794 |
| 3 angstrom | 4/5 | 209/315 = 0.663492063492 |

This sensitivity is a proposed-policy sensitivity, not biological uncertainty.
The descriptor is neither a probability of correct function nor independent
evidence of substrate identity. It measures this proposed combination of
extent and geometric similarity. The whole A102 formula still needs review
against its declared functional scope and its required inputs.

## What cannot be filled from this comparison

The exact local functional-site pair map and corresponding geometric fit are
unavailable. The full competing-function comparison panel is unavailable.
The paper's separate reference to another comparison reaching 2.5 angstrom
cannot establish a stronger/weaker functional match without its corresponding
extent, map, and scope. Those operands remain missing, not zero.

If a proposed functional-scope calculation multiplies this descriptor by a
required but unknown factor bounded [0,1], its result is bounded
[0, 0.530793650794], with no point value. That interval is conditional on that
proposed multiplication rule; it is not a confidence interval. Requiring a
factor also requires explaining why it is necessary for the particular claim;
an exact-substrate question and a whole-fold question need not have the same
required information.

## Reliability and shared measurements

The paper reports five AF2372 crystal conditions. They are not five independent
homolog matches. All-reflection Rwork/Rfree pairs are 0.215/0.273,
0.188/0.212, 0.201/0.288, 0.213/0.244, and 0.175/0.210. Their gaps are
0.058, 0.024, 0.087, 0.031, and 0.035. These are model-quality diagnostics,
not functional-match probabilities; one minus Rfree is not a confidence score.
The selected between-protein comparison's exact structures and the reference
structure's relevant quality inputs remain unspecified here.

The mobile-loop and ligand-state observations can explain why structural state
matters. They do not supply a missing homologous-site comparison. The paper's
biochemical results belong in their own evidence cells and must not be counted
again as independent geometric measurements in A102.

## Exact fields the comparison can populate

These are numerical sheet inputs, not prompt text or reader implementation:

    target_length_residues: 252
    reference_length_residues: 252
    aligned_positions: 209
    rmsd_angstrom: 1.5
    target_reference_pair_map: null
    rmsd_atom_count: null
    target_structure_chain_and_state: null
    reference_structure_chain_and_state: null
    functional_site_comparison: null
    same_scope_competing_function_comparisons: null
    half_response_distance_angstrom: 2.0  # proposed parameter only

The independently executable arithmetic check is check_af2372_001.py. Its
receipt is parent_arithmetic_001.json. Neither file runs an alignment or
substitutes missing paper measurements with synthetic protein data.
