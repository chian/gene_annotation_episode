# Original development outcomes

All existing outputs remain unchanged. Counts below describe individual runs,
not unique tools or a whole-repository result. Tests and development scripts use
the existing local_jobs policy of 20 GiB RAM, 4 GiB scratch and no wall cap,
with .venv/bin/python -B.

- check_20261026T213239251312Z contains the original source snapshot from the
  first wrapper invocation. local_jobs rejected its repository-root working
  directory at scratch preflight before the selected child script ran. There
  is no child result receipt. The runner was corrected to use its private check
  directory as cwd; original outputs were not regenerated.
- check_20261026T213300201152Z ran the new-module adaptation script successfully.
- check_20261026T213822608434Z installed the thirteen additive shared branches
  after preserving their before bytes and hashes. Exit 0.
- check_20261026T213943627171Z created the four standard test modules. Exit 0.
- check_20261026T213950339040Z: five full synthetic standard-program paths
  passed; the zero-hit fixture failed. Its report incorrectly combined
  program=blastp with version=PSIBLAST. The retained worker diagnostic reports
  standard_program_context_conflict. The fixture was corrected to BLASTP;
  the failed receipt, original report, generation and diagnostics remain.
- check_20261026T214107475073Z: five exact-query publication cases passed,
  one per standard program, in 101.58 seconds. These used R's earlier77-case
  source snapshot; later verification uses the final78-case correction.
- check_20261026T214337518592Z: 28 acquisition cases passed, then this
  development verification was explicitly interrupted to release the shared
  dependency window for R333's final malformed-HSP reported-length correction.
  Pytest reported KeyboardInterrupt, exit 2, in 97.13 seconds. This is not a
  completed suite pass. R was notified only after the process ended; no
  moving-source pass is claimed.

R333 subsequently froze its78-case source, with calculator SHA256
6e27b630bc8ab56cdc2254a450a2d5e216199ae6aed50ddfeb5b5202480885af,
views SHA256 521980e08f0ef8949a9971861560409d49362c980261dfa4b17b6075350f8b75,
and worker SHA256 1d114a609819900d0f3ba51a47dfa2a17f29469898f5b6d949d2e48d4298a994.
The subsequent E checks retain separate source snapshots and receipts.

No real native database BLAST, scientific API request, HPC access/submission,
software installation or database download occurred. Fake PBS plus a labelled
synthetic file emitter exercises the real producer/custody/worker/return path.
The retained294 paired range output is independently labelled paired-format
evidence; it is never relabelled as a database execution.
