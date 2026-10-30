# Additive native clarifications for the legacy reader

The sealed207 records and their historical limitations remain unchanged. These
are additional observations from the same retained SAMStat2.2.3 binary, SHA256
`14cd7ed136e6e52271d0bd16f02dc4978f1e5049f1d026f9aab55e80242def6c`.
They are local source-executed synthetic cases, not BV-BRC service output.

1. `NATIVE_RUN_RECEIPTS_002.json` records `--norm --plotend` on the retained
   missing-QUAL SAM input. The default quality series is absent. The optional
   end series reports mean41 at all four positions; the relative series reports
   mean41 at labels1,26,51,76 and zeros at other emitted positions. All associated
   SEM values are zero. This confirms the previously source-inspected missing
   quality guard limitation in `collect_stats_end_seqqual` and
   `collect_stats_norm_seqqual`. The parser preserves the native numbers under
   the agreed native mean/SEM fields, with
   `samstat_quality_coverage_unproven`; it does not infer quality-bearing sample
   size, repair the missing QUAL, or call the zeros Q0 evidence.
2. The new302-bp clustered-error fixture emits an empty final x label in five
   base series and the quality mean/SEM series. The linear cluster writer in
   `samstat_2_2_3/src/plot/plot_interval.c::get_plot_interval_lin` initializes
   textual range labels only when a cluster boundary is reached. Its final
   incomplete cluster can remain unlabeled. The parser keeps all seven numeric
   terminal values, the empty `native_label`, null coordinate bounds, and a
   `missing_requested_value` qualification with an x-field locator. Numeric
   observation remains available; no terminal coordinate interval is invented.
   Root explicitly confirmed this handling in the scoped task message.
3. `NATIVE_RUN_RECEIPTS_003.json` supplies a tiny unclustered counterpart with
   all five mismatch-base symbols and two-base insertion/deletion events. The
   native insertion/deletion arrays count one opening each. Together with the
   clustered case, all37 legacy metric names have populated native examples.

The first two new run attempts failed at shared-library loading (exit127), with
no HTML. `NATIVE_RUN_RECEIPTS_001.json` and `native_additional_001` retain those
failures. The additive successful runs use the same retained dependency path
as207 and keep output, input, temporary paths and logs under213. No installation
or source modification occurred.

`PYTEST_ATTEMPT_002.log` retains the initial failure on the producer's empty
cluster label. `PYTEST_ATTEMPT_004.log` retains a later test-only variable
shadowing failure. Neither log was overwritten. The final focused result is
`PYTEST_ATTEMPT_007.log`:57 passed.
