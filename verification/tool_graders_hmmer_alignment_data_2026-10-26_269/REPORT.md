# B1 build/mask pure implementation handoff — check004 snapshot

The final additive correction and source hashes are in
[REPORT_ADDENDUM_001.md](REPORT_ADDENDUM_001.md). This earlier snapshot and its
receipts remain intact as the record preceding explicit returned mapping spans.

Implemented only the two B1 modules, their matching two test files and this
verification directory. No shared producer, dispatcher, library, accounting,
episode, prompt or credit code was changed. Production binding remains root/D1
work. The original B1/M1 contracts and immutable user goal remain authoritative.

The ports and every numerical field's inputs, formula/native source, units,
population, coordinate convention and missing behavior are documented in
[INTERFACE_AND_NUMERICAL_MEANINGS.md](INTERFACE_AND_NUMERICAL_MEANINGS.md).
Full current sheets and calculations are in [filled](filled), with concise
numerical values in [FILLED_EXAMPLES.json](FILLED_EXAMPLES.json).

## Actual verification

- Final bounded test receipt: [check004/receipt.json](check004/receipt.json),
  **48 passed in 0.52 s**. Earlier checks are retained: 39/44/44 passed as
  coverage and relationship validation were added. Tests use .venv Python,
  PYTHONDONTWRITEBYTECODE=1 and existing local_jobs with 20 GiB RAM, 4 GiB
  scratch and no wall cap. No installation, network or HPC work occurred.
- Five retained native 259 builds: protein, DNA, RNA, annotated protein and
  single-sequence matrix. All four retained alimask modes were parsed and
  calculated. Fifty relevant 259 files were checked against the original
  EVIDENCE_MANIFEST hashes; no native data was recreated to fit a fixture.
- Three independently retained producer267 gappy/fragment fast maps were
  compared against B1 for wnone, wgiven and PB.
- **11 new native alimask invocations** under the same local_jobs limits:
  seven expected successes and four expected exit1 failures. Full inputs,
  exact argv/executable hash, stdout, stderr and receipts are under [native](native).
  The successes cover model-span masking with inserts, adjusted ali2model
  endpoints plus no-map, all three supported fast weighting branches with
  ambiguity/nonresidue/missing symbols, and replacing/appending an existing mask.
  The failures confirm native model length at N+1 for each fast branch and
  native rejection of hand mode without RF. No unsafe after-last-match ali2model
  request was executed.
- The native harness initially looked for an expected native error in stdout;
  the actual error was in stderr. That harness assertion was corrected. Existing
  recorded invocations were reused without rerunning or overwriting them.
- [examples001/receipt.json](examples001/receipt.json) records a separate bounded
  reread/recalculation of all 16 filled examples using the final sources. Every
  successful native mask/map comparison passed. Earlier native calculation files
  remain historical; `filled/` contains the current recalculation.
- Saved-sheet JSON recalculation runs with file, process and network sentinels.
  Additional cases cover invalid/missing/partial records, malformed numbers,
  invalid MM geometry/symbols, missing RF, duplicate labels/models/byte occurrences,
  wrong source hashes, forged M1 arrays, ordered associations, partial trailing
  models, UTF-8 suffix failure after valid MSAs, explicit unknown formats,
  nonfinite KL, absent background, changed tolerances, interval overlap/capacity/
  bounds, missing selected summary and conflicting saved references.

## Filled numerical examples

| Example | Actual retained/calculated values |
| --- | --- |
| Protein build | 3 sequences; 14 source columns; 12 model and resaved columns; model/source fraction 0.8571428571428571; EFFN3; effective/input ratio1. Position5 F/Y counts2/1. Mean entropy0.07652489498826755 bits; explicit-background mean KL4.376066019802603 bits versus native rounded4.376. |
| DNA/RNA builds | 3 sequences; 12 columns/states; EFFN3; mean entropy0.9925134248800135 bits; uniform explicit-background KL1.0074921672642938 bits versus native1.007. |
| Annotated protein | Complete RF/MM/SS_cons and model annotations preserved; mean KL2.450911195065786 bits versus native2.451. Input illustrative cutoffs remain supplied metadata, not calibrated confidence. |
| Singlemx | MSA name single_protein versus model NAME single; 1 sequence, 12 columns/states, EFFN1; KL0.6282749544993826 bits versus native0.628. Model position1 A probability exp(-1.27959)=0.27815131911860913; not an empirical single-sequence frequency. |
| Overlap mask2-4,4-6 | Actual MM `.mmmmm........`; 5 unique masked columns/14=0.35714285714285715; new5, removed0, retained0. |
| Insert-containing hand model span | RF `xx..xx` gives model map[1,2,5,6]; model range2-3 masks all alignment columns2-5, 4/6=0.6666666666666666. |
| Adjusted ali2model | RF `.x..x.` maps[2,5]. Requested1-6 returns source endpoints2-5 and model1-2. Requested3-4 returns native no-map, retaining requested endpoints. |
| New fast examples | wnone/wgiven/PB all produced map[1,2,3,5,6] for the supplied eight-column ambiguity/fragment example. Explicit request for model6 failed natively with computed length5 in each branch. Complete weights/marked sequences/occupancies remain in the saved results. |
| Existing mask replacement | Source MM `m.m...`, ranges2-4,3-4: output `.mmm..`; requested union3, actual3/6, new2, removed1, retained1. |
| Existing mask append | Same source/ranges: output `mmmm..`; actual4/6, new2, removed0, retained2. |

## Remaining limits and consuming handoff

Established reader grammar is Stockholm/Pfam. AFA/A2M/Clustal/PHYLIP/PSI-BLAST
and unaligned single-sequence formats remain explicit unknown source populations;
no extension-based guess or native conversion is hidden in a reader. Complete
M1 output models can still be retained independently of unavailable source joins.
Independent fast map reconstruction supports explicit amino/DNA/RNA with wnone,
wgiven or nonsampled PB up to50,000 sequences. GSC/BLOSUM, PB sampling and absent
explicit fast alphabet remain exact unavailable branches. Hand maps only need
RF; their coordinate meaning is independent of relative weights.

Parent-selected missing output roles need explicit propagation. The pure payload
map can carry `summary: []` to preserve selected-but-absent summary without
fabricating bytes or an occurrence. Missing roles omitted entirely cannot encode
that distinction; native redirected empty stdout still yields missing-header
diagnostics and unresolved associations, not a complete zero summary. The exact
sealed operation must not be altered by a worker to guess selection metadata.

No complete selected-tool/resource-child/typed-receiver path was run by B1.
No claim is made about root/D1 integration, new hmmbuild live execution, API/HPC
availability, library installation or full fixed-scope completion. The public
map port is available to producer267, but B1 does not import producer internals.

## Exact final source SHA-256

| File | SHA-256 |
| --- | --- |
| gene_annotation_episode/hmmer_alignment_preparation_data.py | 17177f61891d65eef10086716c4166f9b7338607cbf862c743ac25d1a7ef7975 |
| gene_annotation_episode/hmmer_alignment_preparation_calculations.py | 94d4c4b4017f79334cdce578497cd5cc7b82e1b8f0e7742827b99e3e2d1a691c |
| tests/test_hmmer_alignment_preparation_data.py | 8bcd5af97fbaeaf7ae2554c3d2e4c35403f32ec0daba8235d47cff779761e825 |
| tests/test_hmmer_alignment_preparation_calculations.py | bf82903706d6f48a1ba76ae25a3598e866f1e79848114e0ca417daa020204883 |

[SOURCE_AND_EVIDENCE_MANIFEST.json](SOURCE_AND_EVIDENCE_MANIFEST.json) contains
the source and reused-source hashes, 259 evidence hashes, native receipt list
and retained file hashes at packaging time. The manifest itself, this final
report and the enclosing examples001 receipt are naturally later packaging
records rather than recursively hashed entries of that snapshot.
