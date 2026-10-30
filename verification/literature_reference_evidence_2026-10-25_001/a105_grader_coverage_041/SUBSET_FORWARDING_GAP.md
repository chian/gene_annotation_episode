# Nonoptical admitted-subset forwarding gap

This is a code/interface audit finding, independent of paper interpretation or future grader routing. No production fix is made here.

## Reproduced behavior

Owned `reproduce_subset_expansion.py` executed the real `LiteratureEpisodes.execute` route with a synthetic table, actual `WorkflowServices` repositories and actual Store in this directory. A literature_strategy child requested only `rate_difference`. Its selected operation saved the normal10-cell rate sheet; the closed child form held only `rate_difference=1umol/min`. Actual `validate_received_report` checked it and `received_form_references` recorded exactly that subset for the literature parent.

With source bytes, parser and rate calculator forbidden, the literature parent's actual `facts` → `_rate_facts` returned all10 saved cells, including unadmitted reference_rate=2,test_rate=1 and ratio=.5. The expanded rows also populated and validated the ordinary closed typed form. Thus exact saved-cell equality and valid JSON/schema do not establish that these cells were actually received by this parent.

For comparison, `received_report_facts` for a nonliterature/annotation receiver returned only the single admitted difference. The gap is a branch-specific scientific ownership violation, not source reacquisition or a model numerical hallucination.

`SUBSET_EXPANSION_RECEIPT.json` records the actual successful result. This was an isolated adapter/form repro with zero model calls, one selected population and one admitted subset. It did not run shared method_loop commissioning or create an actual runtime_report_attempts/typed_form receipt. It uses the existing trusted repository-receive API through the real binding. No inference about live024/030 state follows. The first owned attempt stopped on a synthetic BindingContext path/role mismatch after projection; second attempt corrected only that fixture context. Both owned stores remain.

## Exact path and affected namespaces

`LiteratureEpisodes._rate_facts` gathers sheet references from supplied committed refs when they also occur in `context.received_record_refs`; this tests whole-sheet record receipt. It then picks current assignment's requested components (or family defaults). Only optical calls `adapter.fact_cells(context, selected, components=...)`; every other route calls `adapter.project_cells(selected, permitted_record_refs=context.received_record_refs, components=...)`.

`project_cells` checks the saved selected sheet and allowed component names, not whether each component was admitted to this receiving episode. `validate_returned_values` then compares the expanded row with that same saved projection, so it does not recover the missing receive distinction. `receive_cells`/`received_cells` do store/forward the original admitted subset, but this literature-role own-fact path bypasses that subset.

The actual A105 namespaces/repository methods below were inspected. Only v1 rate was newly executed in the repro; extension to the others is a shared-branch/interface finding, not a claim that11 complete runtime scenarios were rerun.

| Typed namespace | Actual projection implementation | Current literature-parent branch |
|---|---|---|
| literature_rate_cells | LiteratureRateRepository.project_cells, exactv1 version | Unconditional saved-sheet component projection |
| literature_rate_source_cells | LiteratureRateSourceProjection inherits base projection, exactv2 version | Same; version distinctions remain intact |
| literature_assay_cells | LiteratureAssayRepository.project_cells → base, adds operand/meaning refs | Same; added scientific bindings do not enforce admitted subset |
| literature_quantity_cells | LiteratureQuantityRepository.project_cells → base, adds uncertainty kind | Same |
| literature_ratio_cells | LiteratureRatioRepository.project_cells → base, adds candidates/denominator/arrangement | Same |
| literature_binding_cells | LiteratureBindingRepository.project_cells | Same |
| literature_binding_model_cells | LiteratureBindingModelRepository.project_cells | Same; committed binding dependency does not supply parent receipt of every derived cell |
| literature_transport_cells | LiteratureTransportRepository.project_cells | Same; exact saved Km ownership is separate from returned subset ownership |
| literature_partner_cells | LiteraturePartnerRepository.project_cells | Same; both partner operations share this namespace |
| literature_amount_cells | LiteratureAmountRepository.project_cells | Same; amount renderer withholding does not prevent bound fact expansion |
| literature_figure_cells | LiteratureFigureRepository.project_cells | Same |
| literature_optical_cells | LiteratureOpticalRepository.fact_cells | Own original sheets may project; child sheets filter actual admitted cells |

The four other-axis namespaces also take the generic branch. This packet does not independently audit their family-specific internals or claim those axes fixed.

## Minimal follow-up ownership and typed-fact interface proposal

This is a prospective implementation contract, not a new scientific prompt or installed runtime policy.

1. Give every family a uniform context-aware `fact_cells(context, sheet_refs, *, components)` boundary. Existing `project_cells` remains the low-level authoritative saved-sheet validator/projector. The context-aware boundary authenticates original run/episode selected operation ownership before deciding which facts the episode possesses.
2. For a sheet actually created by this episode's original selected operation, permit projection of its owned saved cells subject to this assignment's requested subset. For a child-owned sheet, return only exact previously admitted `(sheet_ref,component,typed-view)` rows from this episode's received-subset receipts, filtered by current requested components. A shared run, global Store record, source ancestry or custody reference must not upgrade knowledge.
3. Preserve ratev1/v2 typed view identity separately despite common provider/operation table; avoid deriving native view from legacy metadata or accepting empty wrong-view output. Preserve partner's alternate readers as one namespace and all existing family qualifications/units/formulas/dependency refs.
4. Have the binding use this context-aware method uniformly for its own fact sources; `received_report_facts` continues forwarding exact admitted subsets. Parent-requested new information requires selected new work/scoped source access or a newly requested/admitted return, not expansion from a child's full private sheet.
5. Authenticate received subsets against the original runtime admitted form/contract/operation identity when invoked by runtime typed_form receipts. Distinguish the manual trusted repository API explicitly; a forged digest is not an original admission. Optical004's mechanism is a relevant concrete reference, not evidence the older families already satisfy it.
6. Saved reopening/forwarding must validate existing selection, immutable bindings and exact admitted rows without original scientific source reads, new calculations, model calls, credit changes or observations. Old closed histories and original expectation snapshots stay unchanged. If an old state lacks an authentic binding needed for new behavior, return a specific structured limitation; do not infer receipt from global presence.
7. Verify meaningful adversarial cases across families: child returns one of several distinct numerical cells; literature parent requests a broader/different set; nested forwarding and actual C4 admission expose only admitted cells; original owner retains its appropriate projection; unknown/source qualifiers remain; duplicate/forged receipts and wrong-view rate returns fail; saved-only reopen and old histories retain actual observations. The synthetic reproduction here is a starting regression target, not evidence these repairs exist.

No routing/classifier/scheduler/reviewer layer, additional model call, episode type, score rescaling or continuation change is required. This communication work is separate from broad case-grounded grader design and does not settle any experimental scoring formula.
