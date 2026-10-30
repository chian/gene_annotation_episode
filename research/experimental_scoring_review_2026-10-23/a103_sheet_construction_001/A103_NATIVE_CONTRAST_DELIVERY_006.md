# A103: corrected completion evidence for the numerical research sheet

This additive record repairs the criterion3 gap identified after the earlier
delivery004. It preserves the premature completion claim and all original
examples. The current numerical proposal remains
`../a103_complete_deliverable_023/NUMERICAL_SHEET.md`, with its exact fields,
source table and synthetic examples. The new source-linked native contrast is
`../a103_scored_published_contrast_031/FILLED_CONTRAST.md` and its corrected
`PRINT_HANDOFF_002.md` / `filled_cells_002.json`.

## Actual filled contrast

| Separate one-question reference-pair sheet | Native neighborhood score | t | S | O | c=S(1-O) |
|---|---:|---:|---:|---:|---:|
| RibK/RibB, 243232.MJ_0055 and 243232.MJ_0056 | .956 | .956 | .956 | 0 | .956 |
| BioY/BioN, 272942.RCAP_rcc03249 and 272942.RCAP_rcc03250 | .844 | .844 | .844 | 0 | .844 |

Each sheet has one compatible neighborhood question with weight1. Native-route
C and E are not applicable; no matched-cohort statistics are invented. The
second pair's combined score is .999 and is excluded, just as the first pair's
combined .959 is excluded. The neighborhood difference .112 is descriptive,
not a calibrated biological comparison across species. Other channels do not
enter A103.

Both are retained database observations linked to published biological cases.
Neither is presented as a number reported by the original paper. The new BioY
record was saved on2026-10-24 UTC. The same-session version endpoint reported
STRING12.5; the generic requested endpoint and complete request operands are
retained rather than falsely described as version-pinned requests.

Official UniProt entries D5ARG8 and D5ARG9 link the exact BioY/BioN genes, loci,
SB1003/taxon272942 and STRING identifiers. BioN's cbiQ3 alias is explicit. This
establishes the reference-locus link, not sequence identity with the historical
assayed construct. No supplied target material or ybhP was mapped to these
pairs. Their numerical values do not become target-annotation scores.

The historical BioY count-route denominator/background remains missing; its
approximate association fraction is not converted to exact50/150. The old
150/127 and selected RibK9/9 quantities remain excluded diagnostics. Direct/
transferred native-channel breakdown, biological calibration uncertainty and
historical construct correspondence remain explicitly unreported.

## Completion criteria and exact verification boundary

1. The existing sheet defines numerical cells, units, denominators, native scale,
   missingness and separate identification/calibration/sampling uncertainty.
   The new exact .844 computational value has no invented biological interval.
2. Count and native routes and their combination into S(1-O) are unchanged and
   explicitly calculated. Count overlap and association contrast remain distinct.
3. The two native cases now fill actual scoring cells through the entire native
   route. Their checked values contrast with the earlier diagnostic-only case
   justification, which was insufficient.
4. Exact repeated pair responses are one observation; aliases identify subjects
   and do not add strength. Existing dependency, contradictory-record, missing
   pair and nondetection rules remain controlling.
5. The original source table is supplemented by worker031's source/identity
   trace and request manifest. Paper inspection belongs to that worker; this
   parent did not reopen the underlying primary paper or its paper-specific
   packet for this delivery.
6. The exact population contract is unchanged. Corrected filled_cells002 uses
   its existing enum/units and actual numeric fields. The first generated
   specimen's formatting defects remain documented separately.
7. The parent printed .844 versus .956 and their scope in commentary; the final
   ten-sheet delivery retains the contrast and proposed-policy limitation.

Parent independently read the complete new mapping/version/single-pair and
UniProt records, the retained RibK pair record, new request manifest, full
FILLED_CONTRAST, final print handoff, corrected filled cells, field-correction
note and both worker receipts. It ran `check_native_contrast_005.py`:22 bounded
identity/arithmetic assertions passed and were saved in
`native_contrast_parent_arithmetic_005.json`. The worker's28 arithmetic/identity
checks and13-cell format check were inspected, not rerun; their overlapping
counts are not summed as independent validation. No native source retrieval
was repeated by this parent check.

The research sheet's identified gap is closed. This is not approval of its
numerical conventions, implemented readers, production credit integration,
biological calibration or a completed target annotation. No earlier record,
production code, prompt, library or running investigation was changed.
