# Scientific working-state receipt boundary found during H verification

This is an implementation finding under the original user-supplied goal. It
does not narrow that goal or declare the communication work complete.

The ordinary default entrypoint binds receipt-aware scientific progress:

1. `gene_annotation_episode/cli.py:132` invokes `run_workflow` without a custom
   `project_credit`.
2. `runtime.run_workflow` calls `bind_default_science` when `project_credit is
   None`. `default_scientific_binding.bind_default_science` constructs
   `ScientificFindingProgress` and uses it for both the root and, when no child
   override is supplied, scientific child credit.
3. `investigation_progress.ScientificFindingProgress` declares
   `requires_episode_receipts = True`. `assemble_workflow` and the `Workflow`
   constructor retain those supplied projector objects. The standard
   independent-execution restoration path also calls `bind_default_science`.
4. `Workflow.receipt_projection` chooses the appropriate supplied root/child
   projector and reads this flag. `Workflow.working_state` therefore passes
   `EpisodeReceipts.selection(episode_id)` to `Store.reasoning_view`.
   The resulting state declares `record_view: received_immutable_versions`.

The supported customization path does not guarantee this property:

- `run_workflow` accepts an explicit callable `project_credit`; this bypasses
  `bind_default_science`. An explicit `project_child_credit` also survives the
  default binder unchanged.
- `episode_record_receipts=True` creates receipt machinery, but does not make
  `Workflow.receipt_projection` true. A projector without the flag makes
  `working_state` omit the receipt selection and read globally scoped Store
  records instead.
- Before model dispatch, `DecisionSource` records those automatically visible
  records with receipt kind `decision_input` when receipt machinery exists but
  `receipt_projection` is false. This can deliver a results child's native
  source, sequence-bearing reference and sequence artifact independently of
  the child's selected form.

Check 060 exercised the real Workflow with the original zero-credit fixture
that lacked this flag. The four restrictive material-receipt assertions failed
after actual results/scientific-parent forms had been built and admitted.
This is evidence of the supported custom-projector communication defect, not
proof that witness fields themselves grant material. It remains work under
the original goal; H made no runtime, provider, scientific-credit or generic
context change to resolve it.

A temporary test declaration of `requires_episode_receipts=True` was proposed
to match the default production path. Root's review correctly requires the
supported custom-credit path to preserve received information independently of
its scientific projector. That temporary declaration was removed before the
next behavioral check. The test keeps `episode_record_receipts=True`, its custom
zero-credit callable without the flag, an assertion of
`received_immutable_versions` at each scientific decision, and every restrictive
source/reference/artifact receipt assertion. Root owns the runtime repair;
H does not change runtime or scientific credit. Scientific zero credit and
fixed scientific continuation are engineering fixtures, not a scoring policy
or evidence of annotation performance.

The trace used source inspection only. Root owns all application execution and
bounded test receipts. No database was read by this worker to infer the cause.
