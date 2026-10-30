# A105 active-site amount implementation and independent review

The full persistent goal remains active and unchanged. A105 adequacy is not established, and expansion to A106 is not authorized by this increment. No GOAL.md, goal amendment, W05 wiring, credit formula or controller change was made.

The preceding goal turn only confirmed scope: it was no implementation progress. This turn made concrete progress by completing and independently checking the active-site amount implementation. Coding152 and independent numerical audit153 worked in their assigned files; root reviewed the assembled path and found further defects before verification.

## Scientific purpose and implemented scope

Protein mass does not itself establish functional enzyme amount. The optional `literature.active_site.populate` operation selects literal source mass concentration, assumed molecular weight with molecular basis, estimated active-site concentration and optional reported active fraction. It preserves source-backed preparation/assay linkage, nominal versus independently standardized titrant concentration, titrant-to-site interpretation, sites per monomer, normalization stage, source uncertainty kind, repetition basis and additional preparation changes.

Nine numerical cells include the native inputs, monomer concentration, active-site density, conditional one-site active fraction, conditional physical denominator factor and derived-minus-reported fraction. They are dependent numerical components populated by one reader path; they are not nine assay-specific graders. No additional complex bioinformatics software was introduced.

Canonical mass concentration is mg/mL and molecular weight is kDa: total monomer concentration in nM = mass/molecular_weight * 10^6. Density = active_sites/total_monomers; the denominator conversion is its reciprocal. Biological active fraction additionally requires the one-site-per-monomer interpretation. An already active-normalized rate must not receive the factor again. This path does not apply a factor to any rate.

Measured density is never clamped. A one-site fraction is explicitly conditional on its intersection with physical [0,1]. A strictly greater-than-one density leaves that biological interpretation unavailable. Source regression SD is not SEM, independent preparation variability, or full joint uncertainty. Full joint covariance propagation is unimplemented, explicitly distinguished from source omission. Per-dimer molecular-weight conversion remains unimplemented without a selected monomer coefficient; active concentration survives that unavailable conversion.

Root review caught three specific defects/coverage gaps: measured zero amount was initially unavailable (audit153); strict density >1 and crossing physical fraction bounds needed explicit handling (root); and original-paper nmol/L units needed exact native aliases rather than fabricated nM quotes (root). Renderer and recurring TASK now expose the physical fraction conditioning. Initial implementation/test failures and fixes remain in coding152's INITIAL_FAILURES.txt.

## Complete paths inspected

Root read the complete current five active-site modules and the inherited literature_rate_storage implementation, including original selection authentication, owner/admitted-subset checks, exact runtime form authentication, source-free validation and receipt forwarding. Root read the complete literature episode binding, experimental prompt renderer, reference-parent renderer and communication module, then inspected the exact four-file additive integration diff. The actual episode_composition factory and independent_execution saved literature factory forward saved configuration directly; no extra factory or EpisodeServices change was required. The newly reused product-fraction scalar parser was read completely. Descriptor tests verify genuine imported dependency hashing.

The new capability defaults to false. With it absent, the existing catalog and assignment remain unchanged. The flag, numerical request field, recurring TASK marker, selected operation, typed namespace, source receipt references, rendering and saved configuration connect through the existing LiteratureEpisodes and shared method_loop. Missing requested_active_site_components selects no return cells. No private agent loop or additional report composer was added.

## Independent verification

Root froze 2,258 project/test/necessary fixture files in pin_001 with no capture-time changes. ROOT_JOINED_001.xml records 104 tests passed, zero failures/errors/skips, 166.048 seconds. The runner returned zero after 166.269 seconds. All 261 inspected project/test imports came from the pin; no pinned file changed. All nine relevant live production files matched the tested snapshot at the recorded comparison.

The selected checks cover active-site arithmetic and source guards, the independent synthetic metrology audit, actual controlled child/parent selected execution and ordinary observation accounting, exact requested subsets and scientific meanings, existing partition/time mixed-family delivery, communication, parent/child prompts, amount integration and compact operation/return contracts. Root's three additional bound probes passed: density >1, density >=1, and density <1.6 with explicitly conditioned physical fraction. These are synthetic counterexamples, not experimental findings or extra independent assays.

ROOT_COLD_FACTORY_001.json records a further controlled runtime exercise, Store closure/reopening, and the actual compose_episode_bindings factory under PRAGMA query_only. The saved descriptor was preserved. Exactly sites_per_total_monomer and conditional_nominal_to_active_denominator_factor returned, with no expansion to unadmitted cells. Database changes: zero. Runtime observations remained three. Source artifact reading and scientific reader execution were forbidden. This is an additional reconstruction probe, not a claim of a fully read-only Workflow constructor or actual model science.

Coding152's separate 105-test group overlaps these tests and must not be added as unique coverage. Audit153's original three-case group likewise overlaps the frozen root run; root subsequently repaired and checked the bounded physical-fraction edge independently.

## Original paper and remaining source work

Root's prior complete original main-paper read, selected supplement read/visual inspection, own full post-paper reset and exact arithmetic remain recorded in ROOT_POST_PAPER_RESET_001.json and ROOT_CASE_ARITHMETIC_001.json. The paper is PMC11121168, DOI 10.1016/j.apsb.2024.03.001. Coding152 and audit153 used synthetic test material; neither independently read or endorsed the primary paper.

The new reader has not yet been populated from root's actual original-paper source selectors. The existing case arithmetic is not proof that the new selected-operation path has populated that paper. Finish this concrete source conversion, including the separately scoped tagged versus native titrations and distinct later kinetic dilution, before reporting this case as delivered. Preserve rounded reported fractions, nominal titrant calibration and fit SD separately. Do not read the next paper or interpret a newly reviewed packet without the required own full reset.

## Live configured investigation and next work

The same configured006 wrapper/session97191 remains in progress. Durable execution state now shows the first child admitted with its original return identity, followed by a separately parent-selected second child executing under PID3322001/start_ticks94068803. Root revalidated that exact live process identity. Public counters advanced to 3 episodes, 89 actions, 75 observations, 1 report attempt and 91 model-call rows at the final recorded poll. No provider requests/responses, private conversations or scientific payload were inspected in this turn. Scientific correctness of the admitted result remains unverified.

Continue that same execution; do not restart because observation timed out or its first child process exited after admission. Inspect the original typed scientific return and its source meaning with the required own packet reset. Complete the primary active-site conversion. Then assess actual assay/design coverage and numerical compilation against the full A105 requirements rather than adding readers or treating green engineering checks as adequacy. Complementary/dependent/contradictory evidence, scientific validity, comparability, effect isolation and functional specificity must be demonstrated in the scoring meanings. Keep the other literature axes in the unchanged full goal; A105 must be adequate first.
