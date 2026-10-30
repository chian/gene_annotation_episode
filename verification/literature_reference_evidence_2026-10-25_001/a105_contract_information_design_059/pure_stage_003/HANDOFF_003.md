#059 stage1 pure helpers delivered for root review

Only the four released new files were written. Existing C7/runtime/provider/
registry/worker/communication/readers/calculators/TASK files remain unchanged.
This stage adds no registered operation, scientific router, capability filter,
axis sheet, controller observation or annotation credit.

| New file | Lines | SHA256 |
| --- | ---: | --- |
| gene_annotation_episode/schema_information_text.py |225|5b4ca71e09952b5673a765b1998d5c7a15c5bc72fa3eb957693ab4b54b6f2e64|
| gene_annotation_episode/episode_contract_information.py |234|ac152800cfd851017150aedecbdd43b42dcfd6556803f5ecf998805ae653e242|
| tests/test_schema_information_text.py |136|84158e92104fa41a6f2a6319317f6223213490afb149d0d5fa46d58c5c3ac67d|
| tests/test_episode_contract_information.py |245|1f71eeaedd6d810676adacfbdfb7732d7613a80af50599610af8e4779498fc72|

API_FREEZE_003.md was written before production coding and defines every public
signature and closed result/declaration shape. No material semantic change was
needed during implementation. Pure helpers accept caller-supplied frozen data;
they read no mutable registry, factory, database, source or model history.

The text codec retains all finite JSON content in named-definition tables:
unknown schema keywords, descriptions, enum/literal data, exact scalar types,
references, Unicode/line escaping, insertion order and array order. Its parser
rejects noncanonical, duplicate, unreachable, unknown or cyclic definitions.
No local or external schema reference is resolved. Content fingerprints are
sorted-key finite canonical JSON, preserving scalar types and signed zero.

Information helpers return exact supplied operation meanings/schemas or a
permitted child's declared return type, with host fingerprints and full text.
Unique actual names are required; unavailable selections return finite invalid
outcomes, and malformed declarations raise ContractInformationError. No lookup
is registered or mandatory. The future display must retain the separate exact
meaning field alongside text; schema/fingerprint payloads are host records.

Compact fact-form expansion accepts only an exact entire top-level
{$ref:"episode-fact:<source>"} field from the permitted child's supplied map.
It clones the original schema and exact x-source selector, preserves ordinary
literal fields/constraints and invokes the unchanged closed-form validator.
External/nested/sibling/unknown/wrong-role/conflicting references fail. It creates
no initial fact values. Fully literal forms retain their original behavior.

The returned host declaration retains the exact submitted schema_json string,
original child role, expanded-schema fingerprint and per-reference source-schema
fingerprints. source_had_x_source records whether the selector was already in
the original cloned type. Saved validation uses ONLY the saved compact string,
expanded schema and declaration; it derives the original source subtree from
that saved expanded field and never calls a current factory. It checks exact
types, literals, field/reference roster and fingerprints. This is consistency,
not original custody: a wholly replaced coherent record remains pure valid data.
Actual C1/C4 admission/authentication is unfinished integration work.

## Actual verification

Final frozen targeted command passed **167 tests in3.00s**, exit0. The589 copied
application/shared-loop Python files and two released tests stayed exact before/
after;70 application/test imports were verified from that pin. Four new files
and10 relevant current read-only dependencies stayed exact before/after launch.
This is a Python-only pure-test pin, not a model/runtime pin with static assets.
No whole live checkout stability claim is made while other sessions work.

Executed pin manifest SHA:
`a7f1a47a627dea225b53c03276c2169cac966790f6ae113ac80948ab5c5e9d8e`.

The cases exercise every actual19 operation and18 fact schema, strict text
roundtrip and malformed text; scalar/reference/boolean/integer/float/Unicode/
empty values; role/name uniqueness and unavailable selections; detached immutable
inputs; every actual fact type expanded to its closed form; mixed interpretation
fields and repeated sources; original selector state; wrong nested/external/
sibling refs and strict JSON; saved-only validation with current factories
forbidden; changed literal/source/selector/roster/declaration detection even after
recomputing the outer fingerprint; and the explicit pure-consistency limitation.

The first direct run passed166 tests in2.85s. Subsequent review tightened the
malformed nonfinite fact-type JSON error to the declared metadata exception and
added its case. The final immutable167-test command above is authoritative;
these overlapping counts are not added.

ACTUAL_SCHEMA_EXAMPLES_003.json contains37 full actual pure information outcomes.
ACTUAL_FACT_FORM_EXAMPLES_003.json contains18 full actual compact/expanded/
declaration examples. The pinned worker freshly checks rendered-text and saved
form relationships. These are actual contract schemas and synthetic form
selections, not experimental findings, scientific measurements or model choices.

IMPLEMENTATION_003.patch reconstructs all four absent-before files exactly in an
isolated directory. snapshot_003, BEFORE_003, the10 preserved read-only baseline
files, terminal/worker receipts and MANIFEST_003 distinguish baseline, final
current bytes and the executed pin. No old proposal/pin/source receipt is edited.

## Required next stages remain

Root must review this pure stage before any shared-file transfer. Still needed:
the opt-in C7/profile/registry presentation boundary; original-host-schema marker
generation and strict simple/composed argument decoder wiring; authoritative
pending catalog/embedded-$id agreement; on-demand metadata handlers and full
recurring scientific TASK/curt STEERING; exact requested-information replay;
original compact/expanded declaration persistence and worker forwarding; actual
selected native work, C1/C4 admission and read-only reconstruction; final coherent
request measurements; and actual configured-model numerical paper extraction.

No Store/provider/runtime/episode/controller or scientific source was created
by this workload. No scientific truth, configured-provider acceptance, complete
A105/goal, exact paper routing, A101 correspondence or W05 credit is claimed.
Ten axis sheets remain, with A105 incomplete and routing implementation deferred.
