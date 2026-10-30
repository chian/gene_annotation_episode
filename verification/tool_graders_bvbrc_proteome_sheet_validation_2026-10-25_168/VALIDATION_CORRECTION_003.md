# Final saved-validator handoff and additive corrections 003

Earlier receipts, logs, source hashes, and design examples remain unchanged.
This addendum records the final shared validator version; it does not revise
the original goal or claim full GenomeComparison completion. The complete
authoritative objective and all sixteen principles were reread verbatim after
consumer inspection and again before this handoff. The current validation,
construction, calculation and correction contracts were reread in full.

The complete new B2 and B3 consumers were inspected, as were the earlier B4,
B1, B0 and A paths. B3's later scoped projection-failure correction was read
before handoff. Their source files remain separately owned. This workload
changes only its new validator, separate schema asset, own tests and receipts.

Five concrete corrections follow the retained receipt002 version:

1. A representation link with no row or association correspondence is
   incomplete_comparison, including when both supplied projections have zero
   rows. Source identity alone does not prove correspondence or independence.
   The known source row counts remain zero.
2. An admitted inventory binding must agree with any supplied executed_fasta
   content digest and byte count. A contradictory raw request remains retained
   when the affected binding is unbound. This still does not establish an
   execution witness, denominator or executed membership. An earlier own test
   incorrectly retained an admitted inventory and ID joins under that wrong
   locator; it now asserts the actual local rejection. The historical test
   results are preserved rather than retroactively described as covering this.
3. Invalid feature aa_sequence_md5 cannot support a joined metadata relation,
   even without a linked feature-sequence row. A malformed unrelated length
   still does not erase a sound identity relation. Rejecting the metadata
   relation retains native measurements such as the supplied 0.875 fraction.
4. TrackInputBinding.membership_complete=yes is inadmissible under the absent
   execution-witness interface for every relation, including
   original_supplied_fasta. Both standalone NativeJoins and embedded NativeSheet
   enforce this. Raw requested membership claims remain inspectable.
5. A genomic_metadata coordinate label requires a known, consistent supplied
   feature convention and agreeing native/feature start, end and strand cells.
   An unknown convention or mismatched/missing coordinate instead permits the
   unknown label while retaining native values, including the example end303.
   No coordinate conversion or length inference is performed.

These are checks of saved claims and their structural dependencies. Validation
does not construct a join, choose an alternative source, parse bytes, recalculate
a mean, authenticate custody, infer missing scientific data or select a resource.
Each saved A/B0 part is validated once per saved-sheet validation call. Tests
block source-file reads, network/process operations, parsers and calculators
during validation; the packaged static schema is loaded separately on import.

Actual checks performed here after receipt002:

| Log | Actual result | Scope and version qualification |
|---|---|---|
| pytest_003.log/xml | 243 passed in 21.41s | 117 own validator, 54 B4, 72 B3 tests. This preceded the final seven membership/coordinate tests and is not claimed as a final-source run. No complete source closure was captured for this intermediate run. |
| pytest_004.log/xml | 124 passed in 4.77s | Final own validator suite. Module/schema/test hashes were captured before and after the run and were unchanged. |

The final validator SHA256 is
9e20d25115871c862a5cb94fe4bf4b3b5f80219906a13b20896578e937ff2942.
The separate schema remains exactly the frozen proposal002 asset, SHA256
739ee63e0e6eea56398c8482a1143dec8b7f7f073041de3edfa4a06af654d9ae.
Own final tests have SHA256
05f506eecebd8961381b04cfbcbc257c64605628527a46ff68c6218c4e999755.
Root received these hashes before its final current-source composition run.
Root's separately performed integration checks are not counted as this worker's
execution evidence.

The public functions return detached copies: proteome_sheet_schema(name) and
validate_proteome_sheet_data(name, value). Entry points are NativeSheet,
NativeSheetResult, NativeCalculationParameters, NativeComponents,
NativeComponentsResult, NativeJoins and NativeJoinsResult. Errors retain the
existing ProteomeDataError fixed code/path boundary. Standalone NativeJoins
checks represented relationships only; absent native/input/metadata context is
checked only when embedded in NativeSheet. Standalone NativeComponents carries
a sheet digest but cannot authenticate an absent sheet or recalculate formulas.

Remaining full-goal dependencies are unchanged: a decoded authenticated
execution/occurrence witness contract; actual complete directional native
reports and their reader/binding; retained real service outputs/deployment
evidence; application publication and typed episode-return integration; and
live/whole-episode verification. None is supplied by synthetic passing fixtures.
No original verification process was stopped or restarted. No job, API call,
Store operation, registry/prompt change, annotation-score change, resource
decision or goal-completion call was made in this workload.
