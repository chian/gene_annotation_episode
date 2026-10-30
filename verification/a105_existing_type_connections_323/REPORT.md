# Existing A105 experiment-type connections

The remaining categories were taken from the actual prior conversation roster in `verification/a105_sheet_reader_inventory_315/PRIOR_CONVERSATION_ROSTER.md`, then checked against existing reader schemas, calculations, projections and scientific TASK instructions. No new paper, chemical-specific grader, experiment category, or top-level evidence axis was added.

The seven remaining roster categories now use these connections:

- Enzyme kinetics and substrate specificity → the existing `activity_rate` grader, with actual kinetic parameter, parameter contrast, turnover or catalytic-efficiency meaning and kinetic-model applicability.
- Ligand binding and binding discrimination → `ligand_binding`, preserving fitted parameter definition, ligand/protein mapping, binding regime and controls. IC50 is not converted into Kd.
- Transport and substrate-response comparisons → `transport_response`, preserving uptake/saturation/electrical endpoint, membrane system, driving force and ion/substrate attribution. Charge equivalents remain distinct from identified-ion flux.
- NADH optical-rate assays → the existing `activity_rate` grader, retaining the NADH-depletion endpoint, optical conditions and covariance rather than relabeling it as an isolated catalytic reaction.
- Partner-removal/addback experiments → the existing `activity_rate` grader, with partner-specific contrast quantities and omission/addback control criteria.
- Reported protein-signal/band ratios → `protein_signal`, retaining scale, loading, detector, background, representation and ROI considerations. Gel display darkness is not molecular occupancy.
- Protein amount/preparation composition → `protein_amount`, retaining amount basis, same-stock or experimental-arm relationships, calibration and active-site stoichiometry. Mass fraction remains distinct from active fraction.

The four existing biochemical protocol groups remain intact. The executable interface now contains eight reusable protocol groups: those four plus binding, transport, signal and amount. Kinetics, optical and partner readers reuse the activity group; additional reader representations do not create further grader types. All groups populate the same nine numerical component fields and retain missing information explicitly.

## Native input connections

The grading adapter now accepts the existing binding parameter/model, binding interaction/model, transport response, electrical channel, ion-discrimination, reported signal, source-signal, gel, amount, active-site, optical, partner, kinetic-model and reported-curve typed outputs in addition to the previously connected readers. These are existing readers and numerical views, not newly implemented parsing tools.

Routing is based on assay type and measured quantity. For these added connections, a variance or an earlier evidence score cannot be passed as a measured effect. A binding parameter cannot masquerade as a conversion fraction. Graph/display units remain graph/display units. Native covariance status, source origin, physical measurement identity and qualifications are retained. Native unit spellings are normalized with explicit scale conversion; the original native row remains stored by the grading repository.

Reader reuse is explicit: a controlled gel-shift protocol can send its native display fraction to `ligand_binding`, with binding controls and experimental-regime criteria and no forced Kd/IC50 fit. The same gel reader also serves `protein_signal` questions. An actual kinetic Km can populate `transport_response` while retaining its concentration and fit meaning; a kcat from that reader cannot be relabeled a transport Km.

Observed source inequalities retain their thresholds and direction. Generic bounded ranges, ROI alternatives and confidence intervals are not promoted into censored observations. The grading-local lower-limit extension uses the existing authenticated scalar reader and its lexical boundary helpers; the shared scalar reader was left unchanged to preserve existing pinned native implementations.

## Binding-discrimination compatibility repair

An actual reader test exposed an existing dependency block: the binding-interaction repository did not admit the current rate-storage implementation. AST comparison with its retained original showed only one additional inherited-method change: redelivery aliases are expanded using the child's original frozen contract. The existing rate-specific changes remain overridden. The reviewed exact rate-storage hash was admitted; unknown implementations still fail. The previous complete writer dependency declaration is retained as a historical unit, without accepting arbitrary combinations of hashes.

## Verification and limits

`tests/test_literature_assay_existing_type_connections_323.py` executes the existing readers on explicit synthetic source reports and passes their actual typed outputs into the common input adapter and grader. It covers kinetics, binding parameters, binding discrimination, binding models, transport response, optical rates, partner contrasts, source-signal ratios, amount, active sites, channels and gels. It separately checks estimated binding-interaction variance and rejection of that variance as a measured effect. The gel fixture has explicitly constructed original runtime records; it is a custody test, not a live-model investigation.

Completed verification commands (counts overlap and are not added):

```text
/tmp/gene-annotation-literature-py314-20261029/bin/python -m pytest -q tests/test_literature_assay_existing_type_connections_323.py tests/test_a105_native_binding_dependency_142.py -x --tb=short
33 passed in 67.70s

/tmp/gene-annotation-literature-py314-20261029/bin/python -m pytest -q tests/test_literature_assay_grading_inputs.py -x --tb=short
28 passed in 22.12s

/tmp/gene-annotation-literature-py314-20261029/bin/python -m pytest -q tests/test_literature_assay_selection_guidance_320.py tests/test_literature_assay_grading_primary.py -x --tb=short
26 passed in 14.09s

/tmp/gene-annotation-literature-py314-20261029/bin/python -m pytest -q tests/test_literature_assay_existing_type_connections_323.py tests/test_literature_assay_grading.py tests/test_literature_assay_selection_guidance_320.py -x --tb=short
92 passed in 58.34s
```

The last command includes the final two shared-reader routes and 16 native connection tests. Scientific scoring inputs in those tests remain explicitly synthetic; no new paper is represented by that test count.

Native effects and supported precision remain useful when scientific applicability or predictions are unavailable. These engineering fixtures do not validate primary-paper scientific interpretations. Existing retained-paper tests and source-selection guidance tests were also run; no new primary measurements were acquired. The separate uncertainty work verifies the estimated-variance and observed-censoring score calculations, and the root verifies actual parent/child delivery, multiple experiment instances and aggregation.

No GOAL.md, goal text, amendment, A101/W05 implementation, or aggregation rule was changed by this connections work.
