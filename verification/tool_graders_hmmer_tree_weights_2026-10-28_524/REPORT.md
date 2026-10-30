# GSC/BLOSUM raw-weight helper authoring record

Status: source-inspected implementation and synthetic tests authored; host
stdlib AST parsing passed. No application/test import, test execution, compiler,
native program, network call, resource job, or integrated return was executed by
this worker. This packet does not establish native equivalence or completion of
R2, any inventory row, or the overall R1–R7 goal.

The original supplied attachment remains the authority. No GOAL.md or replacement
goal/scope file was read, created, or edited. Contract 516 was read completely;
root accepted its helper split and explicitly confirmed the singleton trace
shapes. The goal objective and all ten operating principles were reread verbatim
after source examination and before handoff.

## Owned changes

- `gene_annotation_episode/hmmer_alignment_tree_weights.py`: two pure raw-weight
  ports, one shared native digital pair-identity calculation, exact-source UPGMA
  and native single-linkage stack order. Production imports are only future
  annotations and stdlib `math`.
- `tests/test_hmmer_alignment_tree_weights.py`: 15 source-derived synthetic test
  methods; they use `unittest` assertions and can be collected by root's test
  runner. They were parsed as text/AST only, never imported or run here.
- This evidence directory: before-absence record, source pins, static review,
  new-file diff, oracle proposal, and final manifest.

No shared sheet, normalizer, PB implementation, driver, worker, view, prompt,
library, literature grader, W05 function or existing test was edited.

## Native paths inspected completely for this helper

All native paths below are under `resources/software/infernal-1.1.5/easel/`.
Full-file hashes, including support headers, are in `source_pins.json`; a hash
pin alone is not a claim of full semantic inspection of every function in a file.

| Native path | Complete relevant functions inspected |
| --- | --- |
| `esl_msaweight.c` | GSC and BLOSUM documentation/functions, lines 656–894, including singleton, pre-normalization arithmetic and calls to DNorm/DScale |
| `esl_tree.c` | SetCladesizes, lines 279–311; cluster_engine and UPGMA, lines 1544–1747 |
| `esl_distance.c` | XPairId, lines 249–308; XPairIdMx and XDiffMx, lines 613–712 |
| `esl_msacluster.c` | SingleLinkage and text/digital linkage callback functions, lines 1–231 |
| `esl_cluster.c` | SingleLinkage documentation and complete implementation, lines 1–183 |
| `esl_alphabet.h` | Residue/gap/degenerate/missing/nonresidue code definitions, lines 92–119 |

The existing direct shared consumers were inspected as text:
`hmmer_alignment_preparation_calculations.py` lines 1–214 (including complete
digitization/reconstruction) and 410–549 (complete `_mask`). The root-owned
integration worker confirmed the exact ports and will feed ordered digitized
rows and canonical-then-degenerate symbol strings, normalize once, and retain
the returned diagnostics unchanged. Broader driver/result/return verification
belongs to that integration and root; it was not performed here.

## Exact behavior and meanings

`gsc_raw_weights(sequences, *, residue_symbols)` returns exactly
`{raw_weights, tree:{children,branches,clade_sizes}}`.
`blosum_raw_weights(sequences, *, residue_symbols, identity_cutoff)` returns
exactly `{raw_weights, clusters:{assignment,sizes,identity_cutoff}}`.

Both validate a nonempty list of equal positive-width strings. Supplied residue
symbols must be unique uppercase ASCII letters; input characters must belong to
those symbols or native `-`, `~`, `*`. The common caller owns digitization and
alphabet choice. Cutoffs accept built-in int/float values in [0,1], excluding
bool/nonfinite values, and are retained as float. Invalid alignment/settings or
calculated weights raise the closed `ValueError` strings `alignment_invalid`,
`settings_invalid`, or `weight_invalid`; there is no fallback algorithm.

Identity counts exactly matching residue codes, including equal degenerate
codes, divided by the minimum of the two row residue counts. Zero denominator
means native identity 0. GSC uses difference 1 minus identity, a zero diagonal,
native strict-< minimum scan, j-then-i column/row swaps, clade-weighted mean
distances, branch clipping, postorder branch totals and preorder allocation.
Zero-total subtrees split inherited weight in proportion to their clade sizes.
Internal node 0 is the root, positive children are internal nodes, and nonpositive
children are negative row ordinals. These are weighting trees, not biological
phylogeny measurements.

BLOSUM links at identity >= cutoff. Native available-stack deletion swaps and
the connected stack determine cluster IDs. Raw row weight is 1 / its cluster's
size. No cluster renumbering occurs. Singleton GSC returns raw [1.0] and empty
tree arrays; singleton BLOSUM returns raw [1.0], assignment [0], sizes [1]. These
singleton diagnostics are derived representations; native weighting exits before
building a tree or cluster object.

No helper normalizes weights. The common integration owns the one ordered Kahan
divide-then-scale normalizer, including native zero-sum behavior. No occupancy,
map, scoring sheet, annotation credit, continuation decision or resource
selection is added here. GSC retains its native O(N²) memory / O(N³ + LN²) time
structure without a new cap or timer.

## Concrete synthetic expectations, not observed native outputs

| Input and method | Source-derived expectation |
| --- | --- |
| GSC `[A,C,G,T]` | Raw `[0.5,0.5,0.5,0.5]`; children `[[2,1],[-2,-3],[0,-1]]`; clades `[4,2,2]` |
| GSC `[N,N,N,N]` | Raw `[0,0,0,0]`; all branches zero; common normalizer owns the zero-sum result |
| GSC `[A,A,A,C]` | Raw `[1/6,1/6,1/6,1/2]`; zero-length A subtree inherits 1/2 and shares by clade size |
| GSC `[--,~*,**]` | Raw `[0.5,0.5,0.5]`, because each off-diagonal identity is 0 |
| Pair `[A-CG,AT--]` | One identity / min(3,2) = 0.5; GSC raw `[0.25,0.25]`; BLOSUM links at exactly 0.5 but not its next larger float |
| BLOSUM `[AAAA,AACC,CCCC,GGGG]`, cutoff .5 | Transitive assignment `[0,0,0,1]`, sizes `[3,1]`, raw `[1/3,1/3,1/3,1]` |
| BLOSUM `[A,C,G,A,T]`, cutoff 1 | Native assignment `[0,2,1,0,3]`, sizes `[2,1,1,1]`, raw `[.5,1,1,.5,1]` |

Additional tests cover clade-weighted UPGMA distances, input order, degenerate
code equality, no input mutation, singleton absence of residues, cutoff 0/1,
malformed alignments, invalid symbol settings and invalid/nonfinite cutoffs.

## Actual checks and unfinished verification

AST parsing succeeded for the production and test files. Static inspection
confirmed one identity helper, no normalization calls, and no file/network/native
execution dependencies in production. `static_review.json` records exact
functions/import declarations without executing them. `changes.patch` is a
new-file diff from the observed prior absence, because this checkout is not a
Git repository. An initial `git status` inspection failed for that reason, and
an initial `python` invocation failed because only `python3` is available; neither
attempt performed application or scientific work.

Still required: root execution of the authored tests; native/source-linked oracle
comparison of raw weights, tie topology and native cluster IDs; shared Kahan and
occupancy/map verification; retained authentic CLI outputs; saved-only
recalculation; full child-owned requested returns and closed replay. Native
equivalence across compiler/platform arithmetic is unverified. Existing
R1–R7 deliverables, unsupported alignment grammars/alphabet inference, producer
context and native unsafe ali2model ranges remain under their original owners
and constraints; no unfinished obligation is removed by this helper delivery.
