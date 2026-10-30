# Supplied Addgene sequence-page reader, 738

Implementation and verification evidence under 739 CONTRACT_001 and its A/B
addenda. This packet does not replace the original user goal or close the
gene/plasmid whole-tool rows, public ToolInfo, resource-child or episode paths.

Delivered exports in `gene_annotation_episode/addgene_sequence_native.py`:

- `read_addgene_sequences(content: bytes, *, source_ref: str, requested_id: str,
  response_complete: bool) -> dict`
- `ADDGENE_SEQUENCE_PAGE_SCHEMA`
- `validate_addgene_sequence_page(value) -> dict`

The module only interprets supplied UTF-8 HTML. It retains metadata alternatives,
native sequence headers/text, source section assertions and element locators.
Current repeated native sequence links coalesce within their containing section.
Literal legacy textarea data joins an ID only through unambiguous surrounding
native identity. Sequence normalization removes ASCII whitespace only, preserves
case and IUPAC DNA, and rejects malformed literal characters. Textarea raw inner
markup is retained and rejected rather than removed. HTML character references
are decoded once. Unclosed textarea prefixes remain inspectable with an explicit
incomplete-literal issue. No topology, biological confidence or numerical score
is inferred. The validator enforces a closed schema, typed values, ordinal,
status, category, literal, issue and locator relationships and returns a detached
copy. The parser performs no I/O, link-following or native execution.

The original `check203_addgene738` ran once using the explicit retained155e
Python executable/stdlib and retained134c dependencies, with both original201
Addgene entity/JSON prospectively staged by `--support-file`. Its original handle
is `verification/tool_graders_hmmer_map_verification_2026-10-28_529/check203_addgene738/handle.json`.
The collected result is return code 0, terminal and quiescent. All 46 cases
passed in 0.24 seconds. Source, dependency, stdlib, binary and selected stdlib
source pins are unchanged. Execution audit has no outside modules or unbound
mappings; native and original retained fixture pins are unchanged. The durable
handle records 20 GiB cgroup RAM, swap zero, 4 GiB monitored scratch with possible
overshoot, equal hard per-file limit, and no wall-time cap. Filesystem isolation
is not claimed.

One case replays the genuine 211,547-byte saved current pUC19 page, SHA256
`deb0393a4b1c71ae21e438a7dd2a6f410defbc83c3e939c2ce10faf0b4b30c4d`.
It retains IDs 513490, 91118 and 91449; one full and two partial Addgene-verified
source categories; two original href locators per row; explicit authentication
requirement; and null sequence/header/textarea fields. The unrelated empty
`textarea name=sequence` does not become a result. The remaining 45 cases are
labelled engineering HTML/schema counterexamples covering legacy alternatives,
categories, identity joins/ambiguities, conflicting literals, case and symbols,
raw markup, entity decoding, empty/invalid/incomplete input, generic login,
partial preservation, caller operands, detached JSON and schema tampering.
Engineering snippets are not biological measurements.

Historical capture qualification stays intact: original201's two capture-custody
checks passed, but its overall return code was 4 because its audit observed the
unbound `/usr/lib/x86_64-linux-gnu/libnss_mdns4_minimal.so.2`. It was collected
terminal/quiescent with five unchanged closure pins. Reader203 does not erase
that failure or establish clean closure of capture201. No requests were repeated,
and no authorized authenticated Addgene route or credentials were inferred.

`VERIFICATION_001.json` retains exact source/test/contract and run artifact pins,
all 46 actual case reports, the collected receipt, execution audit, resource
metadata and the capture qualification. Parser source is frozen at SHA256
`dd3d76ca0b1440fed1db0d8e9e9737973f6a19d42b546c171b46c7ca165b2397`;
test SHA256 is
`833391f2f10276ec772e78e9ae7e3e42922aa512e43569e3d7135eddba670909`.
These checks establish the supplied-page parser component only. Actual
authenticated sequence acquisition and all original R1-R7/full public-resource
episode obligations remain open. Existing shared extraction scoring is unchanged.
