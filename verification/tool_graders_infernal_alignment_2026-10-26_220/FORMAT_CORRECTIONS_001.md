# Native findings and additive field qualification

The authoritative objective and all 16 principles were reread verbatim after
the complete cmalign manual, relevant native source, and actual outputs were
examined, before these findings were translated into numerical fields.

## Rendered gaps do not establish deletion-state counts

`src/cm_parsetree.c`, `Parsetrees2Alignment`, initializes consensus cells to
`-` (lines 1061–1081), then writes emissions and deletion states (1089–1212).
Unvisited model positions can therefore retain the same gap symbol as actual
deletion states. Its local-end output records emitted residues (1324–1343),
not which consensus positions were skipped by the transition. `--miss` replaces
terminal gaps for truncated traces only when selected (1306–1320).

Add `model_gap_positions`: the exact rendered gap count at RF consensus
positions. Keep `deleted_model_positions` null except when explicit global,
nontruncated settings and valid model geometry establish that gap cells have
deletion semantics. `local_end_skipped_model_positions` remains null without
the actual traceback. Parent accepted this clarification before implementation.

`cmalign.c:1884–1888` calls `Parsetrees2Alignment` with `do_full=TRUE`; every
consensus column is retained. Native RF `~` marks EL emissions, `.` marks IL/IR
insertions, and the remaining RF positions represent consensus positions
(`cm_parsetree.c:1363–1412`). Validate their count against supplied model CLEN
or an unambiguously associated sidecar model header before assigning complete
model coordinates. A model mismatch keeps raw RF indices but suppresses model
coordinates and model-dependent ratios.

## Original sequence coordinates in match-only output

`--ifile` and `--elfile` preserve discarded emission ranges even with
`--matchonly` (`cm_parsetree.c:1135–1194,1324–1343`). Reconstruct original
positions only after validating model/name/occurrence/length, disjoint in-range
triples, and retained-length plus omitted-count equality. No guessed substring
offset is permitted. Without the required sidecars, retain output positions
and model occupancy; original sequence coverage requiring that validated map
is null. In full output, every retained nucleotide advances the original
coordinate by one; supplied sequence/length disagreement invalidates that join.

## Numerical definitions frozen before implementation

- Counts: native nucleotide symbols at consensus, IL/IR and EL columns;
  rendered gaps and native `~` missing symbols separately. Alignment columns
  are zero-based; original sequence positions and model positions are one-based.
- Model occupancy = occupied consensus positions / validated CLEN. Sequence
  matched coverage = occupied consensus positions / validated original length
  only with an exact original-coordinate map. Zero denominator returns null.
- PP bounds: 0 = [0,.05), d = [(10d−5)/100,(10d+5)/100) for 1..9,
  * = [.95,1]. Sum integer hundredths and divide by the count of retained
  nucleotides with available PP. Missing PP contributes neither zero nor a
  denominator observation. Upper bound is inclusive only if all bins are *.
  Native `avg pp` remains a separate, rounded native statistic over the full
  input sequence, including residues omitted by match-only rendering.
- Column occupancy = residue rows / (residue + gap rows). Count missing,
  nonresidue and geometry-unavailable rows separately. Ambiguous RNA symbols
  count as retained nucleotides, without claiming a known base identity.
- WUSS pairs: matching nested brackets and matching uppercase/lowercase
  pseudoknot letters. Reject an unbalanced or crossing bracket grammar rather
  than invent a partial structure. At each pair, retain per-row categories.
  Pairing denominator is rows with two unambiguous A/C/G/U bases after the
  explicitly declared uppercase, T-to-U normalization; numerator is
  AU/UA/GC/CG/GU/UG. Missing, gap, nonresidue, ambiguous and unavailable rows
  are separate exclusions. No gap becomes a noncanonical observed pair.
- Native score and timing fields retain 1.1.5 `output_scores` meanings and
  printed precision (`cmalign.c:2016–2061`). Bits, avg pp and scientific
  alignment counts remain separate from band/alignment/total seconds and
  matrix MB. No combined score is defined.

Shared code is limited to the existing Stockholm grammar reader, finite JSON
validation, and quantization interval utility after confirming identical format
or mathematics. HMMER biological geometry and PP_cons population assumptions
are not reused. All native annotations survive in the sheet.

## Native --mapali sidecar header omission

The actual 1.1.5 --mapali run omits the advertised model-name/CLEN line from
both insert files. `cmalign.c:1856,1877–1878` prints it only when the first
trace's native index is zero; the inherited prefix prevents that condition.
The original objective/principles and workload were reread verbatim after this
new format finding. Parent accepted the following additive handling: only a
declared mapali operation plus explicit supplied model name/CLEN can associate
these headerless rows. The parsed section records `native_header_present=false`
and `header_source=supplied_model_for_declared_mapali`. Native header absence is
retained as a qualification. It does not establish mapali or a native model ID.
Without supplied identity/CLEN these rows stay unassociated. RF count and any
supplied native model header must still agree before model coordinates are used.

## Native duplicate-name rewrite and score occurrence offsets

An actual --mapali collision run found that the 1.1.5 Easel writer prefixes
every Stockholm sequence/GR/GS name with its zero-padded zero-based row index
when any original names are duplicated. Sidecars keep original names.
`easel/esl_msafile_stockholm.c:1068–1298` was read in full, then the original
objective, all principles and workload were reread verbatim. Parent accepted
additive `native_name` and `name_mapping` fields while retaining the public
association `name`/`occurrence` keys and every original row/annotation.

Derivation requires the exact native warning, a terminated complete record,
consistent original row geometry, every generated prefix agreeing with row
index and native digit width, and duplicate original names after removing one
prefix. Otherwise the name is untouched. Ordinary identifiers containing `|`
are never heuristically stripped. All original annotations remain joined to
the unique printed name. The inherited prefix is validated against actual
supplied training rows and sequence content. --sfile excludes this prefix,
so its same-name occurrence is offset by the inherited same-name row count;
--ifile/--elfile occurrences include it. Explicit output occurrences are still
required to associate duplicate-name supplied sequence metadata.
