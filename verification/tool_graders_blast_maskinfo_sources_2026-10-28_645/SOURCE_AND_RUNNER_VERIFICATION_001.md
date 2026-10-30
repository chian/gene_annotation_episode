# Mask-format source evidence and prospective runtime binding

All seven selected NCBI primary files were acquired once and retained with original URL/headers and byte identities. The acquisition test passed, but check103 returned4 because DNS dynamically loaded an unselected library. This qualification remains in its original receipt. The sources are upstream main reference evidence, not a verified installed-build source.

The bounded verification runner now accepts an explicitly selected native library, pins it before launch, verifies it before the test, and includes its dependencies in the original closure. Unselected mappings still fail. Check104 loaded the selected DNS library and passed its one test plus closure/immutability audit; no source download was repeated. Existing verification snapshots and receipts remain unchanged.

The inspected mask writer consolidates buffered per-sequence masks and serializes one maskinfo object with one mask list and false continuation. Binary decoding and its contract remain unfinished. No production episode, parser or scoring code was changed by this source/runner task.
