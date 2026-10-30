# ComparativeSystems calculator delivery

Scope: workload C in the assigned candidate only. This is not whole-tool or live-service completion.

## Delivered functions and boundaries

`bvbrc_comparative_systems_calculators.calculate_comparative_systems_components(sheet, *, parameters)` implements all 18 frozen QuantityV1 quantities. Scalar category/intersection/union counts and the five selected native formula discrepancies are included. Ratios retain operands, units, source references, named populations, full parameters and the canonical saved-sheet hash. Native reports remain in the unmodified sheet.

`bvbrc_comparative_systems_calculation_contracts.validate_calculation_parameters(value)` checks the closed request shape, quantity-specific applicable fields/nulls, unique component IDs and explicit finite nonnegative tolerances. `validate_components(value, *, sheet)` validates saved identity, units, selected view/entity/field relationships, population/reference IDs and resolvable dependencies. It does not invoke scientific calculations again. Host content/custody validation remains the host's responsibility.

The only runtime dependency outside these two C modules is N's shared data-only helper and its packaged schema. There is no parser, Data extractor, service, host, Store, model, process or acquisition import. No schema asset was forked. No production-root file, sibling file, fixed status row, prompt, episode/controller, evidence-axis, literature grader, BLAST implementation or annotation-credit calculation was edited.

## Actual terminal verification

Working directory: `candidate/` below this186 delivery directory. Environment: `PYTHONDONTWRITEBYTECODE=1`; `PYTHONPATH` is the absolute candidate path; interpreter is `/home/chia/repos/gene_annotation_episode/.venv/bin/python`.

Command:

```text
/home/chia/repos/gene_annotation_episode/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_bvbrc_comparative_systems_calculators.py
```

Final actual result: **53 passed in 8.23s**, exit0, retained in `pytest_003.log`. Earlier runs are retained: 46 passed in7.47s (`pytest_001.log`) and 51 passed in8.26s (`pytest_002.log`). Tests were polled on their original live terminal handles; none was stopped/restarted after a polling yield.

The tests cover all nine C verification families in185: native75% versus supplied44.444...%; family occurrence/population-SD calculations; density above1 and zero denominators; exact category sets; separate PL/PG sets and empty unions; exact duplicates, conflicts, partial IDs and incomplete populations; explicit reference contexts/missing/partial/empty sets; immutable recalculation under changed view/population/reference/tolerance parameters with acquisition/parsing/process/file operations forbidden; and all five native source formula discrepancies, including missing joined rows and changed original populations. Saved validation is tested with the calculator itself disabled. All six unavailable numerical states remain distinct from available zero. Tamper tests cover sheet hash, analysis, component identity, units, exact native field, source view, population, pointer, owner and ratio/output identity.

Initial smoke output `smoke_001.log` exposed a C mistake: NativeTableRow status is `ok`, not `valid`, so native components were incorrectly marked missing. That output is preserved. The correction is verified by `smoke_002.log` and all later tests. The smoke script did not assert values and therefore exited0; this is not represented as a failed pytest run.

Additional actual command:

```text
/home/chia/repos/gene_annotation_episode/.venv/bin/python /home/chia/repos/gene_annotation_episode/verification/tool_graders_bvbrc_comparative_systems_implementation_2026-10-25_186/evidence_c/verify_actual_builder_001.py
```

This reads N's actual saved builder outputs, invokes the actual C exports, and independently checks **27 numerical values**, exit0. Final terminal log: `native_builder_consumption_003.log`; source-file/content hashes and expected/actual numbers: `ACTUAL_BUILDER_CONSUMPTION_001.json`. Full generated component objects are the three `*_actual_builder_components_002.json` files. This verifies N-produced-sheet → C consumption over retained source-executed synthetic inputs. It is not a live native service result, a D extraction test, provider integration or episode communication.

## Filled numerical results

| Quantity | Actual result and operands |
| --- | --- |
| Native retained pathway occupancy | 100×3/(2×2)=75% |
| Separately supplied later pathway occupancy | 100×4/(3×3)=44.44444444444444% |
| Native retained subsystem role occupancy | 100×3/(2×2)=75% |
| Native retained feature density | 4/(2×2)=1; independent added-feature test gives9/4=2.25 without clipping |
| Supplied later pathway feature density | 5/(3×3)=0.5555555555555556 |
| Family returned occupancy | 2/3=0.6666666666666666 |
| Family accepted occurrences per positive genome | 3/2=1.5 |
| Family length CV | 81.64965809277261/200=0.4082482904638631; SD remains population SD, uncertainty remains null |
| Category counts | active0, likely1, inactive0; one conflicting-category genome remains in the sheet and qualifications |
| Explicit four-EC reference representation | native2/4=0.5; separately selected later records3/4=0.75 |
| Native formula discrepancies | all five source-witness formulas give0; altered native values give absolute discrepancies with explicit tolerance qualification |
| Hex overflow | raw10001,257 native occurrences, two positive genomes retained; occupancy1, mean128.5, per-genome encoded counts remain incompatible |

An empty new ratio is missing with retained zero operands and `empty_denominator`. A producer-reported zero sentinel remains a separate native field. Available counts of valid retained records can remain inspectable when incomplete data make the overall ratio unavailable. Unrelated missing represented-genome count does not erase available native mean/SD CV or the native occurrence/positive-genome ratio.

## Exact remaining consumers and limits

P must call C from its pure `consume_bundle` after N/D inputs are explicitly selected and the sheet is populated, preserve the returned sheet/components separately, and copy selected scalars/ratios through `project_comparative_systems_facts`. P's `validate_saved_comparative_systems_projection` should use `validate_components` and equality with stored selections, without recalculating. Native-only C requests do not require D.

I/root must bind the provider through `AppServicePublications._grade`, retain exact implementation/content pins, and deliver its requested facts through `BVBRCComparativeSystemsReturns` and the existing episode communication boundaries. Those integrated consumers, actual service execution, authenticated artifact acquisition, deployed producer/reference identities and real episode communication were not executed by C. Root owns packaging, integration, production application and fixed-row updates.

One contract wording gap was reported to root before any amendment: the initial numerical prose permits a different explicitly saved genome subset, while the closed population assignments describe full native-view populations and exact supplied query populations. C supports choosing among the explicitly saved compatible native/supplied view-population pairs and reference sets. It does not invent an arbitrary subset binding or substitute a requested-genome denominator for a retained view. Arbitrary subsets of one full saved view require an explicit additive source/subset relationship rule; no schema or semantics were silently changed for that purpose.

The authoritative objective and full16-principle block were read verbatim before implementation, after substantial contract/native examination and at handoff. The current numerical contract and additive parameter/population/component rules were reread at handoff. The original authority SHA256 remains `11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`; the packaged115-definition schema remains `b1310c2f3c7a464191f8c9eb5918d516ed2e6dd13f49bec024a2e9a8bde159f8`.

## Additive root clarification at delivery

Root explicitly closed the reported wording gap: use the closed contract, selecting among explicitly saved compatible population/view bindings and saved reference sets; native formula checks retain the native original population. The earlier subset wording does not define creating arbitrary subsets of a full view. Do not add a subset type or substitute a denominator without filtering and binding matching operands. The exact unsupported operation is creating an arbitrary genome subset of one existing full saved view without such a binding. Root will record this clarification separately;185 and the shared schema remain unchanged. The18 existing QuantityV1 quantities are the completed C deliverable under that boundary.
