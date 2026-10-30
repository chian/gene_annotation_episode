# Read and verification record for bounded A104 review032

The following complete authorities were read from their actual files:

- `AGENTS.md` and `GOAL.md`.
- `docs/EPISODE_STRUCTURE.md`, `docs/TIME_AWARE_ESTIMATION.md`,
  `docs/TOOL_KNOWLEDGE.md` and `docs/TASK_AND_STEERING.md`.
- `docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md` and
  `docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md`.
- `research/slotted_process_library/publications/2026-10-23-002/VERBATIM_DIRECTION.md`
  and the complete `VERBATIM_RECOVERY_002.md` in that directory.
- `docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md`,
  including its additive corrections and preserved original wording.
- `verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md`.
- `research/experimental_scoring_review_2026-10-23/AGENTS.md`,
  `SOURCE_CORRECTIONS.md`, and `A105_REVIEW_ASSIGNMENTS_2026-10-23_001.md`.
- The actual goal attachment:
  `/home/chia/.codex/attachments/9a858f85-d1dc-4f59-b574-9988cc09dee2/pasted-text-1.txt`.

All paths above except the attachment are relative to
`/home/chia/repos/gene_annotation_episode`. There was no additional
`/home/chia/AGENTS.md`, `/home/chia/repos/AGENTS.md`, `research/AGENTS.md`, or
review032-local AGENTS file at inspection.

The first combined episode/tool-knowledge read was truncated. Those two
documents were reread completely. The time-aware document's omitted middle
was reread in lines 100–270 and its tail in lines 271–388, supplementing the
complete opening; no missing section was accepted as read. Other displayed
authority outputs were complete. The actual goal attachment and latest
`CURRENT_USER_STEERING_003.md` were reread immediately before writing the
task-specific review, with the delegated user/parent instructions still
controlling its scope.

The complete mathematical/interface paths inspected were, under
`research/experimental_scoring_review_2026-10-23/a104_clade_support_completion_025/`:

- `A104_CURRENT_NUMERICAL_PROPOSAL_004.md` (531 lines).
- `EXACT_READER_FIELDS_004.md` (175 lines).
- `PRINT_HANDOFF_004.md` (105 lines).
- `arithmetic_checks_005.py` (408 lines).
- `arithmetic_results_005.json` (all entries displayed as losslessly compacted JSON).
- `CURRENT_TWO_CONDITION_PROPOSAL_002.md`, including the exact three user
  definitions; its old formulas are treated as history.
- `CURRENT_USER_STEERING_003.md` (46 lines).

`READ_AND_VERIFICATION_004.md` was absent at both checks. No source paper or
paper-specific retained packet was opened. There is therefore no claimed
per-paper reset or fresh primary-source inspection in this review.

Actual execution:

1. Execute unchanged checker005 in memory, parse all its output, and compare
   with the entire saved receipt: equal. The original files were not written.
2. Reproduce score()'s null result for known-zero J with missing O, and the
   unrelated-polytomy membership ambiguity; enumerate its three refinements.
3. Run the new `arithmetic_review_001.py` to the new
   `arithmetic_review_results_001.json`: exit 0; all bounded assertions passed.
   Read the complete resulting receipt.

The new script checks the corrections described in CONTRACT_REVIEW_001.md.
The old 256-point product grid is not counted as 256 new biological or
independent reviews. It supplies no calibration or empirical annotation
evidence. No broad test suite or native phylogenetic software was run.

The shell has `python3`, not `python`; an initial read-size command using
`python` failed and was rerun with `python3`. A git-status probe established
that this workspace is not a git repository. Neither incidental failure
changed the review or any original file. All writes in this task are confined
to this newly owned directory.
