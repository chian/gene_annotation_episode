# XMFA input and caller failures

Additive clarification to accepted PROPOSED_CONTRACT.md, 2026-10-25. The
serialized document/result shapes and original frozen source remain unchanged.

Add two native-input diagnostic suffixes to the finite list:

* `empty_input`: decoded content contains no non-whitespace characters.
* `document_unrecognized`: nonempty content contains no recognizable format
  declaration or record boundary.

Both return invalid/null under the accepted failure contract. Do not use
`header_malformed` to describe input that contains no header. Headerless
recognizable records retain a partial document with `version_missing` and no
trusted coordinate interpretation. A header-only explicit Mauve1 document
retains unknown completeness and zero observed blocks, as already specified.

Caller misuse is separate from malformed native input. The implementation may
define a finite explicit set of `ValueError('xmfa_<suffix>')` codes for wrong
parameters, closed shapes, redundant counts, locations, native tokens and
identities. These errors do not add scientific measurements or change native
diagnostic meanings. There is no free-form model interpretation in either
failure channel.
