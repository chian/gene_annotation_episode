# Precision and origin handoff examples002

These additive controlled Workflows exercise the expanded typed precision
contract in REACTION_PRECISION_HANDOFF_003.md and the explicit
literature_reaction_record_v2 storage version. The old runner and examples001
remain byte-preserved. No current-code replay compatibility for oldv1 records
is claimed.

The new wrapper imports the unchanged old runner's ordinary Workflow and
saved-authority replay functions, and adds precision assertions during actual
parent receipt and saved reconstruction. The root-reviewed primary retained
CsiD ratio keeps independentn, reportedSD and derivedSD unknown, ratio_origin
reported and budget_origin unknown. Both synthetic examples have actualn2,
derived descriptiveSDsqrt(.02), ratio_origin synthetic and budget_origin
synthetic. All typed rows and selected outcomes retain
uncertainty_interpretation=descriptive_not_confidence_interval.

Each case's RECEIPT.json holds the full immutable payload, selected outcome,
exact frozen child form and schema, admitted five-cell parent subset, complete
three-action/observation histories and original/text source hashes. Fresh
--reopen disables parsing/calculation/identity functions and imported aliases,
allows only saved result/request artifacts and sets SQLite query_only. It
checks outcomes, forms, admitted subsets and histories without reopening source
or measurement bytes or recalculating the components.

EXAMPLES_RECEIPT.json and REOPEN_RECEIPT.json additionally record precision
checks, all protected001 file hashes and runtime/runner source hashes before
and after each command. These runs use scripted decisions and fixture
controllers in isolated ATGGCT Stores; they do not establish configured-model
interpretation, live host restart, measurement corrections, completeA110,
target correspondence or annotation credit.
