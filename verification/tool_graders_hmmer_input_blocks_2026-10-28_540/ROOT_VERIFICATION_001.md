# Root bounded parser verification

Root read the complete decoder and tests and the handoff. The final revision
retains annotations in native append order and checks limitations against the
correct global or row annotation map. The existing frozen 529 lifecycle ran
check010_input_blocks: 110 tests passed in 0.29 seconds, return code 0.

Original unit gene-local-job-d8017e7506d0403a94c7ec33d8b1d8b2.service was observed
terminal and quiescent and collected. The job used 20 GiB memory, 4 GiB scratch,
zero swap and no imposed wall-time limit. Source, dependency, standard-library
and executable pins were unchanged; the audit has no outside imports or unbound
mappings, with native libraries and retained fixtures unchanged. Current decoder
and test hashes match the frozen verified snapshot:

- decoder: 13a15fd2dda16ea6d4320b79f2e2c4c5e9470bd67b648a068ba056b792c6ad52
- tests: c99fff47fee483ac2dc5adb2a7b907ecf919ab56fac96a59dc7e47670c47305d

The selected tests use genuine retained Clustal emissions, upstream Easel
fixtures and clearly identified authored edge cases. This run did not compile
or invoke a native oracle. Separate native comparison and sheet/episode
integration remain open. No new scoring definition or numerical policy was added.
