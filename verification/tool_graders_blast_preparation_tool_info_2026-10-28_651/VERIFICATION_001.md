# Tool-information binding verification 651

Implementation evidence under 646/004. This record does not change the user-entered goal or establish complete native/episode support.

The assigned tool-information module now requires explicit new-mode variants and uses one capability schema for descriptors and `native_blast_utility_binding_accepts_job`. The port validates the full shared native job, then checks exact program, mode, software, molecule and variant membership. It performs no installation check, file access, acquisition or execution. Root owns the practical consumer and wired it to this port. No additional interface changes were required.

| Program | Mode | Legal variants checked |
| --- | --- | ---: |
| blastdb_aliastool | convert_gi_list | 1 |
| blastdb_aliastool | convert_seqid_list | 2 |
| blastdb_aliastool | inspect_seqid_list | 1 |
| blastdb_aliastool | create_subset_alias | 6 |
| blastdb_aliastool | aggregate_databases | 8 |
| blastdb_aliastool | aggregate_volumes | 1 |
| makembindex | create_megablast_index | 6 |
| makembindex | show_filters | 1 |
| makeprofiledb | create_profile_database | 6 |

All 32 legal variants are covered by explicit synthetic inputs and descriptor/runtime membership checks, including rejection of the other variants of each pair. The five original descriptors retain their exact information and schema construction. Shared restriction/parameter schemas supply the variant types. Invalid combinations, missing/duplicate/unknown binding fields, strict booleans, nonfinite values, exact software/molecule, local-only resources, empty v2 titles and purity are checked.

`check110_tool_info651`: 109 passed in 7.08 seconds; collected returncode 0, terminal and quiescent. `check110b_tool_info651_consumer`:one added test passed in 1.37 seconds; collected returncode 0, terminal and quiescent. The second attempt ran only the added actual practical-admission case, without repeating the successful 109 cases.

Concrete admission example: a valid RPS/text job is admitted by its exact binding. The same job is rejected under an RPS/binary-only binding despite equal program, mode, executable/version/digest and protein molecule. Both the descriptor schema and actual `LocalPracticalOperations.validate_assignment` agree.

Both checks used bounded 529 with 21474836480 bytes RAM, 4294967296 bytes scratch, zero swap and no wall-time cap, using check005/dependencies. All application checks stayed inside the bounded runner. Receipts report source/dependency/stdlib/binary unchanged; execution audits report no outside modules or unbound executable mappings, and unchanged native libraries and retained fixtures. Scratch enforcement is the existing monitored visible allocated-byte policy with possible overshoot and per-file hard limit; no filesystem sandbox is claimed.

Exact receipts:

- `verification/tool_graders_hmmer_map_verification_2026-10-28_529/check110_tool_info651/receipt.json`; SHA256 `fd39a0a1581c5754603ca149d93365714b95e95311bde3d3b6e7cdc7c96fde12`.
- `verification/tool_graders_hmmer_map_verification_2026-10-28_529/check110b_tool_info651_consumer/receipt.json`; SHA256 `4466d41b734c18daa8baa9f446783fd7bbcd0076355abac81809d4984f8e0598`.

Only the assigned production module, assigned test module and this verification directory were edited by 651. The current production module matches the successful snapshots. The added consumer test is pinned in the second snapshot. Retained pre-edit tool information provides regression evidence and is not executed at runtime.

Inspected complete shared utility/preparation contracts, native utility/materialization contracts, the tool-information implementation and complete affected execution/practical consumer methods. The original attachment, 646/001–004, applicable AGENTS.md, grader principles, relevant inventory rows, episode/time design and TASK/STEERING distinction were read.

Remaining outside this evidence: actual native formats for all variants, real VDB offline closure/deployment, full child-owned Workflow execution, requested result returns and saved replay. No native program was rerun, no scientific numerical authority was added, and no runtime prompt, continuation rule or resource binding was changed. The source descriptor and passing schema checks do not establish nine-mode completion.
