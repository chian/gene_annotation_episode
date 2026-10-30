# Root correction: unknown identity fields are not contradictions

Root's source review found that `_row_details` compared the assertion's entire
population identity dictionary to the selected database identity. A null release
or scope on only one side therefore became `population_identity_conflict`, while
the accepted pure qualifier correctly treats it as unavailable information.

Root added `tests/test_native_blast_population_unknown_identity_root.py` and
ran it through the existing bounded local-job path. The four one-sided null
cases failed before the correction; the two known-difference cases passed.
The run and its source pins remain in root_unknown_before_008.

Root changed only the population identity comparison within `_row_details`:
either missing release/scope gives the corresponding unavailable qualification;
a known unequal field still gives a conflict. Original records and both identities
remain unchanged. All other source, operand, manifest and census checks remain.
This uses the already accepted semantics, not a new formula or confidence score.

The first post-change run passed 54 cases and failed two new root cases because
the synthetic fixtures still asserted the old manifest digest after changing the
manifest. root_unknown_diagnostic_010 identified that additional real conflict.
Root corrected the fixtures' original synthetic assertion digests; production
validation was not weakened. Both runs are retained.

The final root_unknown_final_011 run passed all 56 cases: the six new root cases
and B's complete 50-case test module. It exercised production preparation,
population, source qualification, deterministic calculation and saved-sheet
validation with synthetic inputs. No scientific executable, network, HPC or
new episode run occurred. The exact command, receipt, stdout, stderr and source
pins are retained. Execution used 20 GiB RAM, 4 GiB scratch and no wall limit.

The changed production module SHA256 is
`f1fef5d3cb315f531f628b77ef3b5708ddc03f5f7200c3256e33fce20fc3b156`.
The final run's before/after pins identify the new root test and unchanged B test.
B's earlier AFTER_SHA256_001.txt and final_007 results remain historical records;
they have not been replaced. C365 received the new production pin before starting
its next worker run.

This closes the specific root finding. B's complete adapter/source-envelope
review and C's full receiving-episode verification are separate unfinished
acceptance work. No U06 or tool completion is claimed here.
