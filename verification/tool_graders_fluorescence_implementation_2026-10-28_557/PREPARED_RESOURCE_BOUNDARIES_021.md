# Prepared fluorescence resource and input-version boundaries

Additive implementation contract, 2026-10-28; no goal or scope change.
Root source review after018/019 found two specific remaining consumers.

`LocalPracticalOperations.validate_assignment` currently matches operation,
mode, software and parser subsets but never checks v2 preparation methods or
report profiles. Catalog JSON Schema correctly limits each binding, yet direct
practical commissioning can accept undeclared v2 capabilities. Separately,
`validate_execution_input_versions` adds fluorescence event/support inputs to
its authenticated selected-file map but omits report_inputs, although019's
operand validator already validates their original received custody.

## Ownership and required corrections

The fresh worker owns the fluorescence-specific branches only in
`gene_annotation_episode/practical_execution_operations.py` and
`gene_annotation_episode/execution_input_versions.py`, plus new
`tests/test_fluorescence_prepared_resource_boundaries.py`. Do not edit producer,
result worker, scorer, receipts, other tools' branches or existing test files.
Read complete affected functions and callers before changing behavior; read
EPISODE_STRUCTURE, TIME_AWARE_ESTIMATION and practical execution directions.

For a selected v2 job, one actual configured binding must jointly match the
operation, mode, exact software, v2 binding version, all selected input parsers,
all selected preparation methods and all selected report profiles. Never union
capabilities across alternatives. Accept subsets, including empty methods or
reports, when that same binding permits them. Retain existing v1 behavior and
existing parser/operation failure meanings; add a specific capability failure
for the new mismatch. Do not infer a capability from installed files, select a
different resource or rewrite the requested job.

Input-version validation must include each exact report_inputs file in the same
selected-file map as event/support files, after `_fluorescence_inputs` has
established custody. Check expected hash and size using existing Store metadata;
do not read report scientific bytes on the host or broaden generic artifact
scope. A matching raw report cannot confer access to unreceived derived results.
No new acquisition, observation, credit or receipt is created by validation.

## Verification

Test both operations with declared synthetic software shapes for the pure
capability check: allowed complete subset; unbound preparation; unbound report;
v1 configuration cannot authorize v2 additions; methods/profiles/parsers split
across same-software rows cannot jointly authorize a job; a single complete row
can; unchanged legacy v1 cases remain valid. Do not execute native jobs here.

Test received report input versions through actual Store custody/metadata and
the existing owner input-validation boundary where practical. Explicitly reject
unreceived reports, wrong hash/size, protected derived result substitutions and
undeclared artifacts. Full Workflow020 separately exercises valid report input
versions across actual commission/launch/return. No mocked report identities may
be presented as full native execution evidence.

Root runs the bounded529 runner with actual591 dependencies. No application
imports/tests/computation on the host; source/AST/JSON inspection only. Provide
exact changed files/hashes and selectors. Read the original user attachment goal
first; reread objective and all operating principles verbatim after substantive
source work and this contract before handoff. Never read GOAL.md or create a
goal/scope-amendment file. Do not claim inventory completion from these checks.
