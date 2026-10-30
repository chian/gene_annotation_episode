# Native observations and additive interpretation

Authority remains WORKLOAD_001.md and the original attached goal. The original
objective and all 16 principles were read in full initially and reread verbatim
after native source/documentation examination and after the first real runs.

The installed 1.1.5 `cm_tophits.c` writers and retained native runs establish:

* Format 1 has 17 fixed fields followed by description. The user guide says
  "18 ... followed by" but counts description as field 18.
* Format 3 has 19 fixed fields followed by description.
* Format 2 has 28 fixed fields followed by description, including model and
  sequence lengths. Header-qualified older format 2 without those two lengths
  can retain missing denominators; no invented lengths.
* The actual format-2 fraction labels are afrct1/afrct2/wfrct1/wfrct2. The sheet
  uses the workload's anyfrct1/anyfrct2/winfrct1/winfrct2 names.
* Fractions are printed with `%6.3f`, not four significant digits as stated in
  prose. Scores/bias use one decimal, GC two decimals, E-values two significant
  digits. These are printed precision facts, not confidence intervals.
* Native `-` means absent/not applicable; `"` in win fields repeats the any
  fields; `-1` means the referenced hit was omitted (e.g. --oskip). It is not
  an index into another query's list. These tokens remain available verbatim.
* The format-2 writer resets noutput to zero for each query list. Reset to idx=1
  supplies a local overlap-reference boundary, not an original input ordinal.
  No-hit input records leave no rows. Formats 1/3 contain no explicit query
  boundary for repeated identical names. Completion and malformed/skipped-row
  qualifications remain separate.

Metadata `occurrence` remains a supplied input-record qualifier. It is NOT
filled from visible query lists. As root explicitly directed, occurrence-bearing
metadata cannot be resolved from tblout alone. Duplicate candidates are not
resolved by the first record, ordering, identical lengths or identical strings.
A unique exact name plus compatible accession and optional artifact scope is
the supported supplied relationship. The caller is responsible for supplying
the actual original operand records. Cross-artifact aggregation requires that
same unambiguous unscoped metadata row, not a shared label. When no such row is
available, a complete format-2 native query list can supply a local population;
other aggregate identities stay missing. Distinct populations do not establish
independent experiments.

## Numerical meanings fixed before implementation

All per-hit input quantities come from the retained native row or supplied
metadata; no analysis/acquisition is performed by either module. Invalid cells
are null with diagnostics while unrelated valid cells survive.

| Cell | Inputs and formula/native source | Units and denominator | Meaning, uncertainty, missing behavior |
| --- | --- | --- | --- |
| bitscore | native score | bits; one reported hit | native bias-corrected model score; printed precision; null if invalid |
| bias_bits | native bias | bits; one hit | native null3 (CM) / null2 (HMM) correction; not subtracted again |
| evalue | native E-value | expected false positives per native query search space | not probability; zero retained; no finite log substitution; search-space settings retained |
| gc_fraction | native gc | fraction; nucleotides in native hit | printed native fraction; no missing composition invented |
| model_span_length | model_to-model_from+1 | model consensus positions | inclusive span; null if endpoint relationship invalid; not aligned paired count |
| sequence_span_length | abs(sequence_to-sequence_from)+1 | physical nucleotides | inclusive span; minus strand preserves model direction; null if invalid |
| model_span_fraction | model_span_length / validated consensus_length | dimensionless; complete model consensus | null if length absent, ambiguous or conflicting; not paired coverage |
| sequence_span_fraction | sequence_span_length / validated sequence_length | dimensionless; complete physical sequence | null for absent/conflicting length; not paired coverage |
| aggregate hit_count | selected reported rows, or selected ! rows | hit representations; declared hit_scope | repeats retained; no claim of independence |
| union numerator | cardinality of union of valid sequence intervals | physical nucleotides, same resolved sequence and strand | zero only for known empty selected population; partial invalid geometry explicitly flagged |
| union fraction | union numerator / consistent validated sequence length | dimensionless | no fraction if any selected coordinates or denominator invalid; observed partial numerator remains visible |
| overlap length | max(0,min(ends)-max(starts)) | physical nucleotides | zero-based half-open intervals; pair membership retained |

Native one-based inclusive endpoints are preserved. Interval conversion is
[min(start,end)-1,max(start,end)] for sequence and [model_from-1,model_to] for
model. No spans imply residue alignment, identity, probabilities or annotation
credit. Native E-values are per-query; multiple-query multiplicity and actual
search space are not inferred from the returned hit population. Known 1.1.5
mixed reporting/inclusion mode and --anytrunc limitations are retained. Unknown
settings remain absent. Source: cm_pipeline.c 855-869, cm_tophits.c 2232-2957,
documentation/userguide/tabular.tex, native manual pages, and
https://eddylab.org/infernal/Userguide.pdf.
