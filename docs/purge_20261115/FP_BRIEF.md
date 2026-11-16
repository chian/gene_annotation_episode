# Brief: remove code that fingerprints the codebase itself (15 November 2026)

Repository: /home/chia/repos/gene_annotation_episode, branch first-full-draft-2026-11-10. Read `AGENTS.md` once and
`runs/claude_inputs/purge/BRIEF.md` sections "Rules that still hold" (launcher commands, isolation, no git, stay in
your area, handoffs) — those rules apply here unchanged, except: NO sub-agents, ONE launcher command at a time,
slot name = your task's slot.

## The owner's instruction
"DELETE ANY TEST THAT WAS TIED TO SPECIFIC INSTANCE OF THE CODEBASE", "remove the pin mechanism too", and, when asked
whether to keep the runtime-computed binding identity and the pins on tool source: "why is any of that waiting on
me? why is your suggestion to keep them? ... we haven't solidified the code yet". No backward compatibility is wanted
anywhere. So: nothing in product code or tests may identify, freeze or compare the state of this repository's source.

## What to remove in your area
A digest is in scope when the bytes hashed are Python source (or other program text) of this repository or of a
third-party tool's source, or when it is a hard-coded constant standing for such source.

1. **Runtime-computed binding identity.** Every `binding_record.py` / `as_record()` / `implementation_record()` /
   `implementation_sha256()` that reads `.py` files (`Path(__file__)...read_bytes()`, `rglob('*.py')`,
   `_binding_source_bytes`, `resource_implementation_bytes`, `SOURCE_PATHS` rosters, `_context_source_key` lists).
   The record keeps its other fields (`version`, `binding_id`, `configuration`, ...); the `implementation_sha256`
   field is removed from the record, from every schema/validator/`set(...) == {...}` field check, and from every
   stored-versus-current comparison (`identity_conflict` on `implementation_sha256`, substitutions such as
   `{**saved_binding, 'implementation_sha256': current[...]}`, `scientific_binding_compatible`-style tolerance).
   A helper that only existed to produce source bytes or the roster is deleted; a module left empty is deleted.
2. **Worker/job implementation manifests.** Request or manifest fields like `implementation: {files, manifest_sha256}`,
   `implementation_manifest_sha256`, `adapter_implementation_sha256`, `adapter_sha256`, `script_sha256`,
   `worker_fingerprint`, functions such as `*_implementation_identity`, `_implementation`, `_verify_implementation`,
   and the checks that compare them. Remove field, producer, schema entry and check together, on both the
   coordinator and the worker side, so current requests still validate.
3. **Pinned source constants.** `SOURCE_FILE_SHA256`, `SOURCE_FUNCTION_SHA256`, `SOURCE_SHA256`, `CALLABLE_SHA256`,
   `template_sha256`, `source_pins` and similar: the constant, the record fields that carry it (`module_sha256`,
   `callable_sha256`, `source_function_sha256`, `source_sha256`, `template_sha256`), schema entries, and comparisons
   (`*_source_function_mismatch` etc.).
4. **Tests and fixtures.** Delete tests whose point is the identity mechanism (hash mismatch is refused, record
   contains the implementation digest, digest changes when a file changes, "implementation unchanged" assertions).
   In other tests and stored fixtures, drop the removed fields so they match the current record form; do not delete
   a behavioural test just because its fixture carried a digest field. Error codes that can no longer be raised are
   removed from code tables.

## What stays (do not touch)
- Digests of DATA: inputs, requests, results, records, payloads, sequences, downloaded files, databases, library
  entries (`entry_sha256`, `library_id`, `file_sha256` of a frozen library snapshot), content addresses, canonical
  record digests, receipt chains.
- Digests or versions of an external executable or database observed at run time and merely recorded as
  provenance of a result (no pinned constant, nothing refused on mismatch with a constant).
- Third-party input-data sha256 checks in tests (data fixtures).
- `Path(__file__)` used to locate a file or set `PYTHONPATH` (not hashed).
- Record `version` strings: do not rename or bump them.

Inventory to start from (not exhaustive; grep yourself as well): `runs/claude_inputs/purge/h5_self_hashing.tsv`
(columns kind, file, line, function, text; filter on your area). Rows of kind `carries_identity_field` are mostly
pass-through sites that go away with the field. Useful greps: `implementation_sha256`, `implementation_record`,
`_binding_source_bytes`, `SOURCE_PATHS`, `manifest_sha256`, `_verify_implementation`, `adapter_sha256`,
`script_sha256`, `fingerprint`, `SOURCE_.*SHA256`, `CALLABLE_SHA256`, `template_sha256`,
`read_bytes()).hexdigest()` next to `__file__`.

## Method
- Many files are copies: group by content after replacing the arm name, edit once, apply to every copy in your area.
- If your task names a finished sibling area, start from it: for each file with the same relative path, three-way
  merge (`git merge-file ours base theirs`, base = `git show HEAD:<sibling file>`, theirs = sibling's working file,
  both with the sibling's arm name replaced by yours); resolve conflicts by hand; then do what is specific to your area.
- No new fallbacks, defaults, try/except, or "if field present" branches: the field is simply gone.
- If removing a check would change what scientific evidence is accepted, graded or credited (other than no longer
  refusing on code identity), do not guess: leave it, and list it under "left for decision" with file:line.
- Things used from another area: make the change, append a row to `runs/claude_inputs/purge/handoffs.tsv`
  (`from<TAB>to<TAB>file:line<TAB>what must change`), and apply rows addressed to your area before finishing.

## Gate (state measured results, not expectations)
1. 0 syntax errors; import check over ALL product modules of your area prints `{}`.
2. Every test file of your area run once, one file per launcher run, isolated form; 0 collection errors. Before
   launching, write down the expected total from the previous per-file results named in your task, and compare
   after. Compare per test with those previous results: list every test that passed before and fails now with its
   cause; fix those caused by your change. Pre-existing failures stay as they are (list the files).
3. Site counts before and after for each grep above.

## Output
`runs/claude_inputs/purge/<slot>.md` (what was removed per class 1-4 with counts, what was kept and why with
file:line, "left for decision", gate results, handoffs) and `runs/claude_inputs/purge/<slot>_deleted_tests.tsv`
(`file<TAB>test or (whole file)<TAB>reason`). If you are the first agent on this task, also write
`runs/claude_inputs/purge/fp_recipe.md`: one short entry per mechanism you met (name, files, how it was removed) so
agents on the sibling arms apply the same shape. Final reply at most 30 lines.
