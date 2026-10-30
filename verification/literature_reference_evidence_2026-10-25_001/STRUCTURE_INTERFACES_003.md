# Scientific selector types at the actual return boundary

The ordinary closed parent-form compiler rejects plain strings, including
source-selector fields copied under interface002. This exposed a real missing
consumer path. Retain exact panel values and their scientific meaning; do not
remove them, disguise them as record references or relax arbitrary text.

The targeted selector schema/runtime now uses three explicit semantic formats:

| Format | Meaning and permitted spelling |
| --- | --- |
| structure_identifier | Nonempty printable ASCII token with no whitespace: [!-~]+. Actual author chain, component, atom and alternate labels; no generated findings. |
| structure_residue_number | Signed decimal integer spelling: -?[0-9]+. Preserves the actual author residue token. |
| structure_insertion_code | Empty for no insertion, otherwise a printable non-whitespace token: [!-~]+. |

The reader's existing explicit unknown/invalid-selector exclusions remain.
Its schema replaces selector minLength/plain strings with these semantic types,
and its runtime validates the same spelling. Literal source-witness contracts
are unchanged. Storage copies the corrected original panel schemas and
validates all values against its immutable saved definitions.

A fresh narrow owner, structure_selector_types, owns only communication.py
and new tests/test_structure_selector_communication.py to implement these
semantic types in form compilation/value validation. They are not reference
formats and must not call the reference resolver. No general minLength,
arbitrary pattern or open-string extension is authorized. Existing scientific
and tool-grader forms keep their meanings. Root owns the literature binding's
implementation identity, prompts and assembled checks.

The first attempt to launch the fresh owner hit the four-active-agent limit.
The still-waiting verification worker was interrupted before any example was
launched; a fresh selector owner then started. Its prepared script and original
source records remain intact. Resume that related verification task after the
joined selector boundary is ready; no scientific episode or configured-model
run is interrupted or restarted by this coding coordination.
