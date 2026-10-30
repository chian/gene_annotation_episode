# Closed C validator relationship clarifications

Additive to INTERFACES_002 and IMPLEMENTATION_OWNERSHIP_003; no value shape is
changed. Root implemented the input/association validators and namespace helper
in the new bvbrc_genome_alignment_input_contracts.py module. Acquisition,
metadata extraction, source-byte authentication and tool information remain
unfinished C responsibilities. These validators do not turn JSON assertions
into proof of same-run source custody.

The following exact relationship checks resolve the nullable fields in002:

- A bound member's source_length equals the complete ordered source-record
  component partition. An unresolved member keeps source_length null. Actual
  sequence strings and lengths remain available in identified file records;
  a missing same-run relationship cannot make them a verified member length.
- Complete returned FASTA records do not establish a complete genome census.
  The latter additionally requires explicit complete retrieval populations,
  reported total/returned agreement, evidence, same-run files and coverage of
  every original genome occurrence. Duplicate genome IDs retain occurrences.
- Bound artifact associations require declared and observed format agreement;
  known declared primary versions must agree with Mauve1/v4. The native-member
  namespace must match its actual document format.
- A bound BBCols interval-to-XMFA join is explicit and injective within its
  document pair. Native interval7 may map to exported block0, but interval8
  cannot also claim the same exported block in the untransformed writer model.
- Original feature maps must correspond exactly to explicit bound feature
  segments. Neutral XMFA inputs must preserve the validated C records and
  invocation, including original coordinates and source-path evidence.

The standalone examples/test evidence use synthetic task/custody envelopes and
actual parsed in-memory FASTA bytes. They verify types and relationships only;
they do not establish a deployed GenomeAlignment job or authenticity of the
synthetic receipts. Later extraction and host consumers must authenticate the
actual source bytes and recorded native producer relationships.
