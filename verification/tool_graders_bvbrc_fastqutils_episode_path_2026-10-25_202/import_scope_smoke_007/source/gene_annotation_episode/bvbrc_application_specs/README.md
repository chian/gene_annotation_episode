# Retained BV-BRC application definitions

These 24 definitions are source contracts, not an installed or authenticated
service catalogue. They support deterministic preparation only. They are not
tool-library entries or scientific scoring sheets.

`MANIFEST.json` records the fixed required identities, source-native identities,
original source URLs, SHA256, Git tree and blob identities, and exact derivations.
The Git tree identities are not asserted to be Git commit or deployed versions.
`original/` preserves every official source byte from the earlier retained study.
`derived/` preserves the same bytes except for five identified comma removals in
two documents:

| Required identity | Original zero-based byte offsets removed |
| --- | --- |
| CoreGenomeMLST | 544, 839 |
| WholeGenomeSNPAnalysis | 565, 983, 1208 |

The correction is permitted only for the two exact original SHA256 values
listed in the Python module. Other malformed documents are rejected. Derived
files are inspection/preparation copies; nothing is submitted or installed by
this package. No generic JSON repair is used.

The GenomeAnnotation definition also repeats the JSON member `type` inside
`code`, with values `enum` then `int`. The retained bytes and derived bytes both
keep the duplicate. The loader explicitly records both values in
`duplicate_object_keys`; its usable object retains the integer type and the
enumeration. Integer/enumeration intersection matches the supplied-code use in
the inspected producer. It never silently discards the duplicate source fact.

Parameter declaration arrays remain arrays, including duplicate `max_bases`,
`genome_size`, and `reference_genome_id` declarations. No declaration wins over
another. Values are checked against every applicable declaration, and explicit
qualifications report the conflicts. Source defaults are retained as source
facts and never inserted into requests.

The fixed goal identity `InfluenzaHASubtypeConversion` maps to retained native
source ID `HASubtypeNumberingConversion`. This mapping is disclosed in each
prepared result's diagnostics and does not confirm a deployed alias.

The Python preparer returns `ok` or `invalid`. Any error gives a null value.
An `ok` result retains all supplied parameters and StartParams exactly; it can
still carry qualifications for unverified source behavior, unknown fields,
uninspected array members, Workspace references, or remote deployment. All
qualifications must remain available to the consuming execution path.

Supplied definition envelopes must retain content, hash, source kind/URL,
identity and duplicate/correction metadata. The caller remains responsible for
proving that a service definition actually came from its retained response.
Producer-specific checks apply only to the inspected definition hashes. A
different real service definition receives declaration checks and an explicit
qualification that its producer behavior has not been established.

Detailed tests and additive source findings are in
`verification/tool_graders_bvbrc_application_preparation_2026-10-24/`.
