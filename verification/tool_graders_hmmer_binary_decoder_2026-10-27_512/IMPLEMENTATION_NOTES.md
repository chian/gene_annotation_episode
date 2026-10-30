# Binary model decoder implementation handoff 512

This records implementation evidence for responsibility 2 in the 511 coding
handoff. It does not mark the goal, R2, native coverage or episode integration
complete. The supplied user attachment remains authoritative; GOAL.md was not
read and no goal or scope-amendment file was created.

Owned changes:

- `gene_annotation_episode/hmmer_model_binary.py`: pure bounded a--f binary
  decoder, original occurrence/model/byte identity, supported byte-order/layout
  interpretation, exact source-cell port reuse, ordered native metadata and
  projected headers, conditional payloads, unused slots, sentinel missingness,
  partial records and explicit unsupported/stopped streams.
- `gene_annotation_episode/hmmer_model_data.py`: only module description, new
  binary issue vocabulary, and dispatch of the two new decoder ports. Existing
  argument/digest/capture validation remains; outer association errors override
  decoder population state and incomplete capture prevents completeness.
- `tests/test_hmmer_model_binary.py`: retained authentic 259 binary fixture and
  labeled synthetic grammar/corruption cases, exact scalar bytes, all six
  revisions and both orders, flags, strings, annotation sentinels, zero/missing,
  invalid probabilities, original byte retention, partial records, duplicate
  occurrences, loss of framing and recognized stream-layout change.
- `tests/test_hmmer_model_data.py`: the existing two-format unsupported test now
  expects newly decoded native records. Other existing tests are unchanged.

Before snapshots and `SCOPED_DIFF.patch` retain the bounded changes. The common
record is constructed directly in the binary module; no shared helper change
was required by the HMMER2 worker. It imports the existing `_issue` vocabulary
and uses the shared `binary_probability_cell` without a second probability
reconstruction implementation.

Primary inspection included complete `p7_hmmfile_WriteBinary`, `read_bin30hmm`,
`write_bin_string`, `read_bin_string`, format magics, relevant complete model
flags/storage/transition/calibration/cutoff declarations and canonical Easel
alphabet declarations. The current shared source-cell implementation and the
existing HMMER3 ASCII parser/dispatch were read. The 508 field/consumer contract
and 511 handoff were read in full. The final same-layout stream rule in 508 was
confirmed by root: a recognized revision or byte-order change stops at its
known boundary with `binary_stream_layout_changed`; remaining bytes are retained
on the issue, without an invented next record or arbitrary resynchronization.

Host stdlib inspection only:

- `ast.parse` accepted all four owned source/test files.
- Comparing the original and current `_Reader` AST found no change to the
  existing HMMER3 ASCII reader.
- Reading original native bytes with stdlib `struct` established position 1 A
  as `0000803f` = 1.0, position 1 C as `00000000` = 0.0, position 5 F at byte
  352 as `74aa2a3f` = 0.666663408279419, and position 5 Y at byte 412 as
  `c4aaaa3e` = 0.3333340883255005. These are original retained binary32 values,
  not exact two-thirds/one-third replacements.

No application imports, tests, native conversions, native jobs or scientific
execution were launched by this worker. The tests are written, not passed.
Root owns the coordinated frozen native_lifecycle/local_jobs run and integrated
consumer/result/return verification under the specified 20 GiB RAM, 4 GiB
scratch, zero-swap resource limits, with no invented wall limit.

Authentic big-endian and historical a--e producer coverage remain unestablished;
constructed cases only establish the intended grammar checks once run. Historical
HMMER2/HMMER1 binary remain explicitly unsupported. Producer/compiler/ABI history,
discarded original ASCII text, custody, profile/index internals, alignment-map
gaps and separate message/resource obligations are not established by this
decoder. Existing saved unsupported extractions are not reinterpreted here.
