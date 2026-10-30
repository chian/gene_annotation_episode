# Concrete numerical operand references for A/B/C

This clarifies the reviewed177 formulas before independent implementations meet.
It changes no native measurement or formula. FieldRefs use the original report
ordinal and JSON pointers into that ReaderResult, as required by177. A numeric
cell's inputs are the unique set below, in first native occurrence order. An
equivalent unique order is allowed by semantic validation. No derived sheet
pointer is substituted for an original observed operand.

* Report displayed membership counts reference `/queries`. Nested counts are
  deterministic counts of the complete nested arrays in that observed array.
* Query displayed description count references its `/descriptions` array;
  subject, HSP and block counts reference its complete `/subjects` array.
* Subject displayed HSP/block counts reference its complete `/hsps` array.
* HSP reported I/DI, P/DP and G/DG fractions reference their two native cells.
  Reported paired count references G and DG. Reported nonidentical paired count
  and identity-among-pairs reference I, DI, G and DG, including the equality
  condition between native denominators.
* B defines actual block-cell operands from its native strings, starts/ends and
  same-occurrence length cells. A validates those exact outputs using B. C
  carries them unchanged into each HSP's block list.
* An HSP trace count references the union of inputs of that count in all
  included usable-string blocks. A valid-subset count also references the
  two symbol cells of each excluded block, so the supplied population and
  exclusion are inspectable. Gap-run totals additionally reference both axes'
  start/end cells at every block boundary where continuity is needed.
* Trace fractions reference the union of their numerator and denominator count
  inputs. Sum-of-gaps uses both gap counts' input sets. The actual integer
  numerator/denominator remain in ExactFraction.
* An aggregated position union's count references every constituent block
  position-union count's inputs, including unavailable blocks' operands. Its
  coverage adds the original same-occurrence length field. Its support keeps
  included/excluded blocks and missing-trace HSPs independently. No usable
  geometry means missing/invalid/conflict as applicable, never an invented0.
* A subject graph's B-produced distinct/repeated pair count inputs define the
  observed operand set for compatible unique-pair counts. The compatible
  ratios use those counts and retain the same observed input set. Their values
  are obtained from each unique edge's consistent column classification once.
* Disjoint native HSP identity and column sums reference every HSP's I/DI cells
  plus both axes' occupied-union count inputs and usable-string count inputs.
  These operands establish native-count agreement and disjointness. Each of
  the three related aggregate cells uses that same prerequisite operand set.
* Query any-subject paired coverage combines the query paired unions from all
  displayed subjects; its coverage denominator is that query's reported length.
  The special native-no-hit0/L case references the no-hit marker, descriptions,
  subjects and query length explicitly. Empty-without-marker supplies no0/L.

No HSP trace blocks produces missing counts/fractions and explicit missing-trace
support. For a single usable string block, gap-run totals equal its block counts:
there is no inter-block boundary to test. Multiple blocks require complete
usable strings and known contiguous coordinates on both axes for gap-run totals.
Geometry completeness is still independent of string/gap-run counts.

Use DirectionalNumericalContractError(ValueError) with `.code` and `.pointer`
strings. A exports canonical_sheet_sha256(sheet), using UTF-8 JSON with sorted
keys, compact separators, ensure_ascii=False and allow_nan=False. C uses that
same helper. Numerical argument failures become closed failure Issues with
argument_pointer; source references are empty when no valid observed sheet
exists. No native data is changed to make a validator succeed.
