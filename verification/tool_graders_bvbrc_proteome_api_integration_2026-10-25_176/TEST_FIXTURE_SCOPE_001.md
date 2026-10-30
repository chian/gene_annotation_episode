# Additive test ownership, reviewed by root

After TEST_013 host exits naturally, tests/test_execution_episodes_family.py may change only the descriptor-reconstruction test call to initial_decision_context: use the existing context helper to create a real launch BindingContext for launch_assignment({"here": native_assignment(h.workspace)}), and retain all existing assertions.

This decision follows the traced actual runtime caller. It does not assert a documented historical removal of None support. No production initial-context behavior may change. Preserve TEST_013, then rerun the complete execution_episodes_family group with fresh candidate before/after hashes. Other passing core groups need not repeat absent a new concern.

INITIAL_CONTEXT_BOUNDARY_REVIEW_001.md and INITIAL_CONTEXT_CALLERS_001.txt contain the reviewed evidence. TEST_013_execution_family_source.py preserves the failed run's actual unchanged test source, SHA256 708b3caaa0f7dcf5139ef975621bbdce8ea593f372604a5e21c94a1a937b3f1f. The candidate test remains unchanged while TEST_013 is active.
