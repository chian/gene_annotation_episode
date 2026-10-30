# Additive audit of startup order and later resets

New immutable audit note, 2026-10-23. No previous note is overwritten. The
parent requested a specific check because other workloads had printed several
unrelated paper-specific case records in their initial inventory before the
required per-paper resets. That specific failure was not found in this
workload's startup commands.

The audit inspected this agent's own session tool-call record, identified by
agent path `/root/template_a105_reactions`, without inspecting other agents'
research content. Relevant original commands were:

* At 22:31:22 UTC, a parallel inventory attempted `python` commands for document
  lengths and corpus type/keys, plus an `rg --files ... | sort` file listing.
  The `python` executable was unavailable. The file listing contained paths,
  not full case evidence.
* At 22:31:28 UTC, the corrected `python3` command printed document lengths,
  corpus container type, number of records and the first record's **keys**.
  It did not print the first record's values or bulk findings. The separately
  required SOURCE_CORRECTIONS.md was then read in full.
* At 22:31:46 UTC, the first substantive corpus extraction explicitly selected
  only `csiD_glutarate_hydroxylase` and
  `lhgO_electron_acceptor_correction`. A companion `rg` selected those same
  case identifiers in the retained evidence packet and reading notes. These
  two groups share the same 2018 primary paper, which the assignment says to
  count and review once. This was not an inventory of unrelated paper packets.

This conclusion is scoped to the startup sequence, not a blanket independent
certification of every later research action. Each paper note records the
authority rereads performed after that paper. Nine distinct primary papers
received targeted fresh Methods/Results reading, covering all ten assigned
case groups. One-paper notes do not imply that every paper cited by each
original case record was newly opened. In particular, the earlier CysQ,
FrsA, F420 and FolM associated source histories were not all freshly read.

The audit command also printed the first note's full original creation command,
exposing its retained paper-specific content again. I treated this as another
paper-specific reread: before writing a new scoring synthesis, I reloaded and
fully read all fourteen authority documents, with the complete local AGENTS.md
and complete assignment brief/current A106 correction last. This adds a reset,
not another paper or new experiment. No source content was interpreted for
scoring between that exposure and this reset.

The fourteen documents reread were AGENTS.md; GOAL.md;
docs/EPISODE_STRUCTURE.md; docs/TIME_AWARE_ESTIMATION.md;
docs/TOOL_KNOWLEDGE.md; docs/TASK_AND_STEERING.md;
docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md;
docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md;
research/slotted_process_library/publications/2026-10-23-002/VERBATIM_DIRECTION.md;
the adjacent VERBATIM_RECOVERY_002.md;
docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md;
verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md;
research/experimental_scoring_review_2026-10-23/AGENTS.md; and that directory's
A105_REVIEW_ASSIGNMENTS_2026-10-23_001.md. They were printed in four complete,
untruncated groups for this additional reset.

Initial and later output truncations identified during research were repaired
by reloading the missing/full documents before the corresponding scoring
interpretation. A later reread would not retroactively repair an ordering
violation; this audit makes no such claim. Three numerical transcription
errors in earlier notes were corrected in separate arithmetic addenda, which
remain required companions to those notes.

The parent reported a newer user task to remove categorical score pathways.
This research agent does not own or certify that code work. All research
formulae remain proposals. This workload wrote only new files in its assigned
directory, changed no production scorer, reader, prompt or run, and completed
no whole scoring sheet.
