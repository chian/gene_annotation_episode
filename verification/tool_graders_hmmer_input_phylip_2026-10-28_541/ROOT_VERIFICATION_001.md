# Root bounded parser verification

Root read the complete decoder, tests and handoff. The existing frozen 529
lifecycle ran check011_input_phylip: 26 tests and 61 unittest subtests passed in
0.19 seconds, return code 0. Counts distinguish test methods from subtests.

Original unit gene-local-job-683b19d295524972a863a26d30780218.service was observed
terminal and quiescent and collected. The job used 20 GiB memory, 4 GiB scratch,
zero swap and no imposed wall-time limit. Source, dependency, standard-library
and executable pins were unchanged; the audit has no outside imports or unbound
mappings, with native libraries and retained fixtures unchanged. Current decoder
and test hashes match the frozen verified snapshot:

- decoder: bc34e18bc4906b7fceaa5869e116e7bd0ba5a6dca5348c6ec5decf2d921b083e
- tests: 97faf5f595e93b677096c45b54af8f0a95a2fea5e973ce3caf58684c5a5d7aa3

Three original cmemit artifacts were read unchanged. Other cases are authored
source-contract cases, including failures and native-status/geometry differences.
This run did not invoke a native observer or the existing MAP calculator.
Native comparison, source-to-sheet integration, saved validation and requested
episode returns remain open; this is not a completed tool/resource claim.
