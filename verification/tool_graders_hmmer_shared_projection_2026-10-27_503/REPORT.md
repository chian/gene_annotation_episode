HMMER shared numerical projection repair, 2026-10-27

This packet records implementation and verification evidence for the delegated R1 HMMER repair. The original user attachment remains authoritative; this report does not amend the goal or account for broader completion. No progress counters were changed.

The API publisher now takes its existing coverage aliases from the exact retained shared domain score row. `acquisition.parse_hmmer` no longer divides endpoint spans by lengths. `ToolRegistry._publish_hmmer_domain` preserves native bitscore/evalue and its existing operand validation, calls the existing exact artifact/original-array join, and copies the available shared coverage cells. For phmmer, query/target coverage use model/sequence span coverage; hmmscan reverses those axes. Missing cells produce no numerical alias, and a numerical zero remains zero.

The parent-authorized native extension changes `HomologyResults.extract` and one reader import. Newly published native query/target coverage copy paired model/sequence coverage; identity copies actual sequence identity. All three independent publisher divisions are removed. Native scores and raw source counts remain available when grading fails. The source-only `numerical_projection_version=hmmer_shared_paired_aliases_v1` marker is outside the hashed measurement semantic. The original measurement key/cache lookup happens before a missing grade becomes the explicit `phmmer_shared_grading_unavailable` publication qualification. Existing observations and witnesses retain their recorded identity and values.

Parent review found that the first new missing-grade publication was partial but a cache replay dropped its qualification. The final cache path now checks the saved source marker and reads its retained grading artifact; it returns that recorded missing-grade failure without recalculation or new records. True historical ungraded sources have no new marker and preserve their previous completed result. The focused replay checks assert exact status and feedback equality for new missing-grade records, and unchanged records/cache/witness rows plus completed/no-feedback behavior for a synthetic historical fixture.

The numerical sheet and calculator are unchanged. `hmmer_graders.py` and `hmmer_search_grader.py` have the same bytes in all three frozen attempts and the final source; see `unchanged_shared_implementation_pins.json`. API span coverage and native paired coverage intentionally remain different measurements.

Concrete numerical evidence:

| Evidence | Shared quantity and published alias |
| --- | --- |
| Authentic retained API phmmer domain | Query span 89/253 and target span 90/283 equal the published aliases. The same retained score row has paired values 88/253 and 88/283, so substituting paired coverage would change meaning. |
| Explicit synthetic API alignment, both orientations | Five alignment columns contain three paired, one insertion and one deletion. Span fractions are 4/10 and 4/12; paired fractions are 3/10 and 3/12. hmmscan reverses the query/target alias orientation. |
| Actual bounded tiny native phmmer search | A 253-residue query matches a 256-residue target containing a triplet insertion. Target span coverage is 1; the native target alias equals shared paired coverage 253/256 = 0.98828125. |
| Explicit synthetic projection sentinels | Poisoned parser aliases and injected shared cells demonstrate direct projection, including unavailable and zero values. These injected cells are engineering fixtures, not native scientific measurements. |

API publication evidence includes both orientations, missing query/reference lengths, an explicitly joined supplied-query denominator, invalid original hit/domain siblings, exact original-array/artifact association, grading failures with native score preservation, saved-only recalculation, and parent-requested result references. The Workflow test executes launch → API child → results child → requested `execution_result_refs` → parent admission; the received observation IDs resolve to the published aliases and retained shared cells. Its closed replay preserves the recorded runtime actions and observations. Authentic captured phmmer bytes are reused; hmmscan transport and malformed cases are explicitly synthetic.

Native evidence includes retained 17-target/20-domain phmmer output, actual small local searches, missing/malformed/ambiguous inputs, saved-only recalculation, raw-score preservation on grading failure, indel-sensitive paired aliases, and projection sentinels. The existing real Workflow paths return saved observation IDs through the parent's `acquired` and `comparisons` forms and validate the shared alias equality on those exact returned records. Closed workflow replay adds no model/controller action and does not reprice history. The final additional focused checks cover the missing-grade cached qualification correction; the earlier full native suite was not rerun.

All attempts used the existing native lifecycle/local-jobs runner with 20 GiB memory, 4 GiB scratch, zero swap and no wall-time limit. Each retained its original handle through collection. Source, dependencies, interpreter and standard library were frozen and hashed before/after; native libraries were resolved and hashed; loaded modules/mappings were audited. Every receipt reports return code 0, terminal and quiescent, and unchanged source/dependency/stdlib/interpreter. Every execution audit reports no outside modules, no unbound mappings, and unchanged native closure.

| Attempt | Scope | Result | Native unit |
| --- | --- | --- | --- |
| `check001` | API publication, API typed returns, public-search parser tests | 42 passed in 319.77s | `gene-local-job-0d353d3a70ba4c48b18b242bc12d98bf.service` |
| `native001` | Native phmmer binding and typed returns, before the final cache qualification correction | 23 passed in 412.25s | `gene-local-job-9b99887bfb2b435fbc4ed41235950efb.service` |
| `replay001` | Two affected historical/missing-grade cache tests on the final code | 2 passed, 19 deselected in 36.62s | `gene-local-job-39b1f79a744c4af18aa4db68024771a0.service` |

These are separate runs, not a sum of unique tests. Each attempt directory retains `handle.json`, `selected_request.json`, `receipt.json`, `junit.xml`, stdout/stderr, code/dependency/runtime snapshots, before/after pins, and `execution_audit.json`.

Commands run from the repository root:

```sh
.venv/bin/python -B verification/tool_graders_hmmer_shared_projection_2026-10-27_503/run_checks.py launch check001 --mode check
.venv/bin/python -B verification/tool_graders_hmmer_shared_projection_2026-10-27_503/run_checks.py collect check001
.venv/bin/python -B verification/tool_graders_hmmer_shared_projection_2026-10-27_503/run_checks.py launch native001 --mode check --native-phmmer --test test_phmmer_grading_binding.py --test test_phmmer_grading_returns.py
.venv/bin/python -B verification/tool_graders_hmmer_shared_projection_2026-10-27_503/run_checks.py collect native001
.venv/bin/python -B verification/tool_graders_hmmer_shared_projection_2026-10-27_503/run_checks.py launch replay001 --mode check --native-phmmer --test test_phmmer_grading_binding.py --test-filter 'historical_snapshot_keeps_its_recorded_parser_semantics or preexisting_ungraded_observation_cache_and_witness_remain_unchanged'
.venv/bin/python -B verification/tool_graders_hmmer_shared_projection_2026-10-27_503/run_checks.py collect replay001
```

Final owned-function SHA256 values (exact AST source segment plus trailing newline):

| Function | SHA256 |
| --- | --- |
| `acquisition.parse_hmmer` | `58bdee0c72a21146369d7c369efdaad53f3ce40c144da08a722b5c7e116e7754` |
| `tools._publish_hmmer_domain` | `2b3f12e9d274252c6182ae7640e317a79b7629fa29476ac61badf5a97464931b` |
| `homology_results.HomologyResults.extract` | `a4c2a4b688d608123216dfcdf5b4788a3c9b81f0446daab9d595561d7beed93e` |

`function_pins.json` retains before/after owned-function hashes; `edit_pins_before.json` and `edit_pins_after.json` retain full-file hashes and capture provenance. `verification_function_pins.json` states exactly which frozen attempts match each final function: check001 matches the final API functions; native001 predates the final native cache correction; replay001 matches all final owned functions. The full-file tools.py hash also includes concurrent changes outside this worker's ownership. `changes.patch` therefore bounds the tools.py/acquisition.py changes to the owned functions, and the public-search test change to its owned test function. Other owned files have complete diffs. `before/` and `after/` retain the corresponding byte copies.

Capture qualification: the initial host snapshot command used an unavailable `python` executable. For acquisition.py, tools.py and the one public-search test, the pre-edit copies were reconstructed by reversing the exact scoped patch in copies only; this is explicitly labeled `reverse_exact_scoped_patch_in_copy` in the manifest. Other pre-edit files were captured directly before editing. No production file was restored or replaced wholesale.

No new live API, database BLAST, Aurora or HPC submission was made. The native tests ran actual small local phmmer jobs and bounded parsers. No prompts, resource ownership, continuation/credit policies, W05, literature, HMMER numerical calculator, or broader R2 presentation paths were changed. This packet supports review of the scoped API/native R1 publication repair; it does not establish broader HMMER resource/message or format completion.
