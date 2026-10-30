# Regression fixtures and the current retired-scoring contract

Original contracts and failed run evidence remain unchanged. The broader
check003 ran 102 tests: 93 passed, 9 failed. All 16 new derivation publication,
chained-coordinate and shared Workflow tests passed. Before/after hashes of
the captured sources were unchanged during this run.

Seven failures in test_sequence_views_integration.py occurred only at calls
to the already-retired categorical project_credit function. The actual sequence,
product, coordinate, replay and source assertions preceding those calls passed.
The corrected tests assert that no hypothesis or annotation was created and
that the retired scorer still reports AnnotationScoringUnavailable. They do
not manufacture a numerical zero for an unavailable annotation score. Root
changed the tests, not production annotation scoring or W05.

The other two failures were in test_tool_knowledge.py: one indexed the correctly
empty root execution-tool catalog; the other selected an ordinary root tool
and then expected a completed observation. Fresh workload283 owns only repairs
to those knowledge tests and its verification evidence. It must preserve root
tool removal, use a permitted child-owned read, and verify original frozen
instruction bytes and exact outcome/observation recovery. No runtime change is
authorized by this fixture repair.
