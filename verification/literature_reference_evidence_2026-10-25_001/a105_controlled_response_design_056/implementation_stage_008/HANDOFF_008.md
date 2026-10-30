# Bounded text/JSON reader stage

This stage implements one controlled-response experimental component within A105.
It adds no axis sheet, paper classifier, router, experiment count or annotation
credit rule. The total axis-sheet design remains ten. A later literature search
can identify individual experiments/claims that feed several appropriate A105
components; routing is deferred.

## Exact API and contracts

The only production addition is
`gene_annotation_episode/literature_controlled_response_inputs.py`; its dedicated
new test file is `tests/test_literature_controlled_response_inputs.py`.

* `controlled_response_arguments_schema()` returns a detached exact007 selected
  JSON Schema, version `controlled_response_source_selection_v1`.
* `validate_controlled_response_selection(arguments)` validates closed nomination
  structure and dependent selectors, returning a detached copy. It does not read
  a source or accept model-authored scientific numerical operands/matrices.
* `read_controlled_response_inputs(arguments, *, read_source)` authenticates the
  original selected reference closure through the actual caller callback, then
  reads source text, units, uncertainty pieces and structured covariance. Its
  closed result version is `controlled_response_source_extraction_v1`.
* `validate_controlled_response_extraction(arguments, extraction)` checks detached
  saved consistency with no acquisition callback, source reader or image decoder.
  It does not grant original runtime custody. The caller still must bind the
  original authorized request, source, selected operation and actual outcome.

`API_PROOF_008.json` records actual signatures and every closed record's exact
fields. `SELECTION_SCHEMA_008.json`, `COVARIANCE_SOURCE_SCHEMA_008.json` and
`CLOSED_RESULT_INTERFACE_008.json` are byte-identical copies of sealed007. There
is no selected/result schema or enum delta. `CONTRACT_DELTA_008.md` records only
the three root-approved semantic clarifications: exact source alias reconciliation,
explicit callback availability errors and the unavailable-definition saved check.

The result retains selected meanings, actual authenticated witnesses, source
roster, image attribution, native literals/units, uncertainty pieces, source model,
effective model and parsed frozen006 inputs. The reader imports only the frozen
calculator's validator/constants; it never calls a sheet populator. Numerical
sheets in the reproduction artifact were calculated separately after reading.

## Source and partial semantics

All actual callback requests complete before frozen049 image construction. A
malformed callback success or source-scope authorization error propagates, as do
PermissionError, OSError with no errno, EINVAL/EBADF and provider programming
exceptions. Only explicit ENOENT/EIO/ETIMEDOUT or the documented EOFError signal
becomes a retained unavailable dependency. No missing artifact/hash is fabricated.
An unavailable numeric selection stays nominated with null authenticated locator,
raw expression, source observation and computation operand; other evidence survives.

Each literal is selected by exact authenticated text spans. Clipped/forged spans
are repairable selection failures. Complete unsupported source syntax is a reader
capability partial. Source-defined units retain their actual endpoint-bound
definitions and convert once. Unknown units retain the native literal and block
only affected dimensional operations. Registered native operands survive a
canonical display overflow, allowing the frozen calculator's exact cancellation.

Counts, SD, CI endpoints and confidence levels are independent source pieces.
They do not create covariance or a joint-normal model. The unchanged confidence
helper still cannot parse authentic `95%.`; that is an explicit reader-capability
partial, with the original punctuation retained. Incompatible spread units and
CI endpoint collapse retain their source information without publishing a false
numeric spread or zero-width interval.

Structured covariance uses actual source-variable indices and literal label-token
positions, with witnessed bindings to canonical physical owners and role meanings.
The source needs human labels, never future generated host IDs. Duplicate labels
are legal where actual positions identify them. One actual shared control index
can project into two roles only with supported owner identity. Equal numbers or
labels never prove identity or independence.

Full original C, exact lexemes, all variables and actual source model are retained.
The full original N-by-N rational matrix is checked for symmetry/PSD before role
projection; singular PSD is supported. Both covariance unit factors are applied.
The finite projected matrix is separately checked under the frozen calculator's
`Fraction(str(float))` meaning. Lost digits, numerical range loss or finite PSD
failure are reader-capability facts and do not relabel an exact valid source C
as nonPSD. Authentic invalid source C retains raw measurements and finite source
diagnostics, with effective C null, variance unknown and model none. Selected,
source and effective covariance/model meanings remain separate.

Known/estimated C stay distinct. Known-normal source-means support requires the
actual source and selected model/status to match, plus a usable projection; C
rounding disables that family. Approximate/censored/graph operands and positive
known V restrictions remain enforced by the frozen calculator. No raw spread is
turned into a likelihood. Cross-control alias readings are compared exactly with
both unit factors before float projection; a conflict blocks the cross effect
and covariance while preserving the individually clear candidates/local pairs.

Graph nominations authenticate images/crops/tick literal witnesses and retain
`graph_rate_reader_unimplemented` with null pixel result. Geometry attribution
does not assert OCR truth or measured ordinates. New063's independent wrapper is
not imported or tested here; graph numerical coverage remains unfinished.

## Concrete invented examples

`SYNTHETIC_EXAMPLES_008.json` preserves all five own fixture source byte strings,
hashes, original selections, actual extraction results and separately populated
calculator sheets. `NUMERICAL_TABLE_008.json` is their actual compact projection.
All fixtures are invented; none establishes coverage of a source paper.

| Fixture | e (umol/min/mg) | V ((umol/min/mg)^2) | Retained partial behavior |
| --- | ---: | ---: | --- |
| Four distinct observations | 0.006 | 1.7e-6 | d1=0.010, d0=0.004 |
| One actual reused control | 0.007 | 1.36e-6 | d1=0.010, d0=0.003 |
| Unavailable defined-unit witness | null | null | Independent d0=0.004; other control value2 retained |
| Two exact control readings collapse to same float | null | null | d1=0.0119 and d0=0.0049 survive |
| Invalid full source C | 0.006 | null | d1/d0 and magnitude survive |

The first example's native values are [12,2,5,1] nmol/min/mg: native e=6 and
V=1.7 (nmol/min/mg)^2. The actual positive common reference protein-mass basis for
the empty controls is stipulated by the invented source context. The shared case
has native e=7 and V=1.36. Conversion scales e by1e-3 and V by1e-6; it changes no
scientific agreement. These fixtures select model none, so S/B remain null.

## Verification and immutable generation

The final new reader suite passed69 cases. The fresh targeted execution pin ran
the reader, frozen006 calculator, rate-native and binding-visual suites:
**319 passed in3.62s, exit0**. `TERMINAL_008.json` records the exact command,
interpreter and cwd; terminal stdout/stderr are actual subprocess output.
`ACTUAL_IMPORTS_008.json` records actual imported code paths/hashes and confirms
all package imports came from the pin. `PIN_MANIFEST_008.json` binds copied code,
tests and own synthetic fixture bytes; `PIN_AFTER_008.json` verifies every pinned
file unchanged and no extra files. Bytecode/cache writes were disabled. External
pytest plugins were disabled. No model, source search, episode or runtime launch
was performed by this pin.

This pin intentionally excludes kinetic storage/count integration tests and
unrelated shared runtime consumers; independent count pieces are exercised by the
new reader cases. Earlier checkout terminals included a406-pass regression run
before the final bounded fixes; that history is not represented as the final pin.
One initial example-repro script failed on its own wrong source matrix key before
writing examples; its failed script and observed-failure record are retained.

`BEFORE_008.json` and full before snapshots record nine actually imported source
dependencies before editing. `DEPENDENCY_AFTER_008.json` additionally verifies
the accepted006/007 artifact manifests, the frozen calculator/test and all13
sealed007 dependency snapshots unchanged. It also binds the parent's immutable
preliminary generation to the final code. `PARENT_REVIEW_DELTA_008.patch` contains
that complete review delta; `NEW_FILES_008.patch` and `final_snapshot_008/` contain
both complete new files. One historical before dependency changed independently:
`domain.py`4f10c2→ccfacc70 adds a native BLAST database observation schema;
`SHARED_DOMAIN_CHANGE_008.patch` preserves the full diff. The actual test pin
already contains the current ccfacc70 version. REF/obj/identity/ContractError are
unchanged. The initial seal assertion that all before dependencies were unchanged
failed on this real shared delta; its script and observed failure are retained.
No existing file was edited to resolve it. Shared integration may be changing
elsewhere: this is only a pure source-reader coherence claim.

## Remaining work

Parent review of this complete reader/test generation is the next bounded step.
Graph measurement integration, native selected execution/catalog/storage, C4,
typed/admitted-subset/saved runtime reopening and an actual primary-source
scientific example remain required later. No new production binding, runtime
observation, grading axis, scientific episode or annotation-credit integration is
claimed. This stage does not finish A105 or the full controlled-response workload.
