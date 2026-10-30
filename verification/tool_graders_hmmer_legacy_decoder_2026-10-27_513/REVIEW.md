# HMMER2 ASCII decoder implementation evidence

This packet records responsibility 3 of the reviewed 511 coding handoff and
508 implementation contract. It does not change the supplied goal or mark the
HMMER family, R2, a resource, or an episode integration complete.

Implemented files:

- `gene_annotation_episode/hmmer_model_legacy.py`
- `tests/test_hmmer_model_legacy.py`

`BEFORE.json` records that both owned files were absent before this work.
`CHANGES.diff` contains their complete additions. `STATIC_REVIEW.json` records
their current hashes and the successful host-stdlib AST syntax inspection.
The first syntax inspection found an accidental colon after a test decorator;
that source error was repaired before the successful inspection. No application
or scientific module was imported. No test, converter, native command or model
loader was run. The 24 test functions and their parameter cases are written,
not verified; root owns the integrated frozen lifecycle verification run.

The complete retained H2 source writer (`h2_io.c`, including `printprob` and
`h2_multiline`), `read_asc20hmm`, `h2ascii2prob`, and `hmmconvert.c` were read.
The relevant model flag/storage, transition and format definitions in `hmmer.h`
and the complete Easel canonical RNA/DNA/amino constructors were inspected.
The complete common model extractor, its existing tests, shared source-cell
module and shared model-calculation implementation were read. The artifact
consumer's distribution and metadata paths were inspected; the separate shared
consumer owner owns its complete changes and integrated validation.

The authentic retained native output reused is:

`verification/tool_graders_hmmer_preparation_contracts_2026-10-26_259/native/hmmconvert_legacy2/stdout.log`

Its established SHA256 is
`37a65d6515e1d4b657ff8ea3ce70cc002e6fedfec9abcb43d9bced646b87de7b`.
It is a native conversion of a synthetic alignment, not biological evidence.
The focused native tests compare every original token of all 12 match/insert/
transition groups, NULE, XT, NULT, begin and entry/exit slots, plus native
metadata, terminal placeholders, original ordinals and source line/byte bounds.
The literal position-1 A score 3666 and its NULE score 656 remain retained;
their nominal value above one must not make the extraction population partial.
Position-5 F/Y scores 4070/3454 and NULE scores -333/-717 remain separate.

The implementation calls the one shared `hmmer2_probability_cell` port for all
source probability tokens. It adds no probability reconstruction, entropy,
normalization, occupancy or scoring implementation. Original H2 EVD/checksum
data remain legacy fields. Initial H3 insert/transition fields, modern
calibration, composition, EFFN, MAXL, CONS and MM are not manufactured.

Root confirmed two representation details in the conversation:

- Preserve the actual transition-column header through the existing ordered
  `headers` accessor, including malformed labels, using its actual first token
  and remaining value/tokens/line. Shared consumers exclude this body-label row
  from interpretation as a new optional model parameter. Only the first seven
  original labels populate common core transition symbols. The two native
  entry/exit cells remain in the ordered legacy list.
- NULT uses neutral `slot_0`/`slot_1` labels. The inspected writer emits loop
  then move, but an imported file does not itself establish that producer.
  The begin-row labels B->M1/unused/B->D1 follow the retained reader's inputs.

The shared consumer owner was also informed that a malformed final transition
label cannot establish zero m->e merely because the eighth/ninth source slots
remain decoded. Its dependent normalization check must retain that limitation;
the literal seven-slot subtotal is still available where its labels are valid.

Labeled synthetic tests cover the original Nucleic label with actual T/U body
symbols; zero counts; optional/unknown/duplicate headers; EVD and old checksum
retention; absent, malformed, duplicate and short NULE; exact signed integer
tokens; zero NULE with a finite score retained as an invalid log-odds reference
with nominal zero, distinct from underflow and an explicit `*` structural zero;
malformed score/flag/annotation
and label cases; numeric RF/CS characters; CRLF/multibyte coordinates; duplicate
model/occurrence identity; partial last rows; next-signature recovery; invalid
UTF-8; empty versus invalid/unsupported nonempty populations; and the common
dispatch's original capture and occurrence-digest qualifications.

No new extraction issue code or common helper was required. The dispatcher
owner was given the exact port and population behavior. Shared numerical and
saved-result consumers remain under worker 511; public dispatch and unchanged
HMMER3 regression ownership remain under worker 512. The current source and
tests are ready for root's integrated verification, without a claim that they
have passed it. Historical HMMER2 binary/EVD scientific interpretation and the
separate alignment-map/message/resource obligations remain unverified here.
