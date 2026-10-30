# GeneTree provider verification history

These records distinguish original stdout files from messages reporting another
worker's tool transcript. No failed output has been rewritten as a passing run.

1. The shared-provider worker reported an initial actual GeneTree run with
   **32 passed, 2 failed**. Its original output survives in that worker's tool
   transcript, not a captured stdout file here. One failure identified omitted
   XML-root support observations in shared extraction; shared extraction now
   retains the native observation and support record, while edge calculation
   excludes the root because it has no parent edge. The other failure correctly
   rejected a fixture claiming `after_label='q_2'` while its actual parsed row
   still contained `q`. The fixture was corrected by parsing actual `q_2` FASTA
   bytes and updating both the supplied reader result and parsed document.

2. Own captured stdout receipts `TEST_RUN_001.txt` and `TEST_RUN_002.txt` each
   report **35 passed**. The second includes the tightened locus scope check:
   one locus's trim transformation cannot establish another locus's trim state.
   `TEST_RUN_003.txt` reports **44 passed**, including exact case-sensitive,
   gap-preserving output digests, original-member digests, multi-operand null
   scalars and explicit original-coordinate coverage.

3. After the shared alphabet-evidence correction, the shared worker reported
   **86 passed, 3 failed** for its S+G run. Again, only that actual tool transcript
   and the worker's message retain the initial output. The three GeneTree test
   fixtures removed observed alphabet settings but still supplied complete
   evidenced original protein members and row joins. Those original facts
   independently established protein; the test's expectation of unknown was
   wrong. The fixtures now remove that independent member evidence when testing
   unavailable alphabet context. A separate positive test verifies complete
   member evidence remains sufficient, while incomplete selected-member coverage
   leaves alphabet-dependent values unavailable. Own `TEST_RUN_004.txt` reports
   **49 passed**.

4. Own `TEST_RUN_005.txt` is the complete captured stdout for **49 passed,
   1 failed**. A newly added raw-tree-required XML test assumed every missing
   requirement forces extraction status `partial`. That extra rule is absent
   from the accepted contract: extraction can succeed with explicit unmet
   scientific requirements. The test now checks the actual requirement,
   preserved native observations and topology, and unavailable branch-derived
   quantities without introducing a status policy. The shared worker confirmed
   this interpretation. Own integrated `TEST_RUN_006.txt` reports **97 passed**.

The `TEST_RUN_*` receipts remain immutable historical outputs. Later receipts
and code-hashed example manifests identify subsequent shared implementation
changes; an earlier pass does not claim to verify a later revision.
