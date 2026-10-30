# C: requested saved MinHash projection

Coding handoff, 2026-10-27. Runtime tests are **UNEXECUTED**. This packet does not
establish complete MinHash integration, source custody or live-service behavior.
The original user attachment remains authoritative; no GOAL.md or goal/scope
amendment file was read, created or changed.

## Owned changes

- `gene_annotation_episode/bvbrc_minhash_views.py` now accepts the exact v2
  publication envelope alongside the original v1 envelope. It uses A's pure
  `validate_minhash_publication_inputs` port with the service request, preserving
  the original shared sheet and component schemas.
- The existing match/count declarations and projected fields are unchanged.
  Legacy no-metadata requirements remain. Fraction validation now calls A's
  `calculate_minhash_shared_hash_fraction`; the returned fraction is still copied
  from the saved component. The view contains no division expression.
- The optional `bvbrc_minhash_calculations` family copies ordered saved numerical
  components and their four explicit metadata operands. Native parse status is
  based on the original native row, separately from calculation availability.
  Native genome labels outside the supported identifier grammar remain null in
  typed rows, retaining the existing qualification behavior.
- The optional `bvbrc_minhash_calculation_diagnostics` family copies the complete
  saved top-level diagnostics in their original order. The diagnostic code enum
  comes directly from the common grader; paths use the finalized indexed grammar.
  Unmatched metadata diagnostics are not assigned to a native result row.
- V2 validation checks exact pair joins, original input-list occurrences,
  duplicate candidate lists, native/component associations, the selected saved
  sheet, required null states, diagnostic associations and finite numerical
  shapes. It does not calculate distance, null-model quantities or p-values.
- `tests/test_bvbrc_minhash_metadata_views.py` adds 22 test functions, including
  parametrized cases. Existing `tests/test_bvbrc_minhash_views.py` is byte-for-byte
  unchanged.

`before/`, `after/`, `PATCH.diff` and `MANIFEST.json` retain exact file snapshots,
the owned diff, source hashes and the executed static-check facts. No service,
host, execution dispatch, common contract/grader, shared form registrar, prompt,
tool information, W05 or literature code was edited by this workload.

## Numerical cases authored, not executed

All new native-response and supplied-source fixtures are explicitly synthetic.
Fixture source IDs and artifact digests do not claim actual receipt custody.
The existing parser and calculator construct test scientific sheets; projection
copies their saved output and is tested with those full functions disabled.

The authored checks include:

- Original v1 output and its already saved null metadata/recalculations.
- Synthetic `2/3`, k=1, lengths 2/2, alphabet 2: distance
  `0.22314355131420976`, p-value `0.2592592592592592`; native strings remain
  `0.223144` and `0.259259` when those strings are supplied.
- Explicit saved-sheet k=2: distance `0.11157177565710488`, p-value
  `0.10400000000000001`, with original sheet and components unchanged.
- K-only, absent k, all-null and empty metadata; zero denominator versus actual
  numerical zero; no/full overlap; partial/malformed native cells and counts.
- Reordered metadata, duplicate native genome IDs, duplicate pair candidates,
  wrong index/ID, unmatched metadata and an empty native result.
- Copy equality, detached outputs, unsupported identifiers, malformed closed
  shapes, forged associations/availability, wrong field bindings and query
  mismatch. Invalid source custody itself remains a host test responsibility.
- Count-only and no-fact requests, finite diagnostic enum/path grammar,
  closed-form schema integration, shared fraction-helper use, and frozen replay
  with full parser/calculator, filesystem reads and network/process work disabled.

These numbers are assertions authored against the existing common calculator;
they are not newly executed numerical measurements or live resource evidence.

## Actual verification and inspected paths

Only shell text reads/searches and Python standard-library source editing,
hashing, `difflib` and `ast.parse` ran. All three owned Python files parsed;
the source scan found zero division AST nodes and zero calls to the full native
parser or full scientific calculator in the projector. No application/scientific
module import, pytest collection/test execution, native program or network call
ran in this workload.

The complete supplied goal, actual AGENTS.md, finalized 517 contract and root
clarification were read. Complete affected view, common grader, A's new pure
contracts module, MinHash service and host were inspected. The MinHash discovery,
forwarding and description consumers in execution modules were traced; the root
owns the wider execution path review. The complete relevant shared form schema,
validation and semantic traversal functions were inspected after identifying the
diagnostic schema dependency. The fixed similar-genome-finder row was read but
not changed; its pending labels do not erase existing implementations.

## Integration dependencies retained

1. B must authenticate actual selected metadata/saved inputs and produce the
   exact v2 envelope; pure view validation proves shape and relationships only.
   Saved distance/null-model/binomial values are trusted only after host artifact
   and publication authentication. Replay must return those original bytes.
2. B must register both new host fact families. Its received genome-reference
   resolver currently only considers matches and must also consider requested
   calculation rows so a calculation-only child return can be forwarded.
3. The generic shared form grammar rejects `pattern` and untyped strings. B has
   root-assigned ownership of a MinHash-only exact diagnostic schema registration
   in `communication.py`; C intentionally did not broaden the generic grammar.
   The authored closed-schema integration test requires that change. The exact
   supplied regex is used in schema declarations; projector validation uses
   `re.fullmatch`, which also rejects trailing newlines. Authentic saved-value
   equality remains required at the receiving host boundary.
4. Root must run the unchanged legacy and new projection tests in its frozen
   lifecycle environment after assembling A/B/C. D's real selected child path,
   onward returns, original acquisition identity, receipt/history preservation
   and committed replay checks remain separate unfinished verification.
5. Actual live MinHash output and deployed sketch-parameter equivalence remain
   unverified. `native_parameter_equivalence` stays `unestablished`.

Recommended root-owned invocation after integration is ready:
`pytest -q tests/test_bvbrc_minhash_views.py tests/test_bvbrc_minhash_metadata_views.py`.
It was not executed here.
