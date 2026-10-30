# A105 scientific responsibility review: inspected code paths

This is bounded implementation evidence, not a complete scientific-coverage audit, goal authority or an assay-count claim. Root read the complete binding parameter reader/calculator/TASK, conditional binding model and model storage, plus the transport input/calculator/TASK/storage paths. Relevant shared saved-read/projection methods were inspected for prospective compatibility. No original experimental paper was opened for this code-only review.

## What these paths actually evaluate

| Inspected path | Implemented numerical question | Coverage limit |
|---|---|---|
| Binding parameter reader and descriptive contrast | Reported competition IC50 or reported Hill Kd, canonical nM, native test/reference ratio and log ratio; original spread and reporting limits retained | A fitted parameter contrast is not a direct-binding assay, intrinsic-affinity conversion, activation or catalytic-conversion grader. The selected path compares ligands within one declared subject, state and experiment. |
| Conditional binding model | Joint natural-log parameter covariance gives contrast variance Crr+Ctt-2*Crt; a declared known-normal model supports a conditional directed profile statistic | The code does not infer covariance from a fit spread or count, and its proposed signed index is not function probability. A reporting threshold needs a specified censoring mechanism. The native namespace's unimplemented model cells do not imply that this separate conditional model path is absent. |
| Transport response input/calculator/storage | Same-curve Michaelis–Menten test/reference substrate saturation, h=St*(Km+Sr)/(Sr*(Km+St)), plus conditional full-covariance propagation | This is a concentration-response correction. By itself it does not grade measured transport flux, channel current, leak/background, membrane insertion, active-molecule amount, directionality or ion selectivity. A module named transport is not evidence of those assay graders. |

The transport input reader consumes an already committed apparent-Km quantity and separately witnessed curve contexts; it does not fit a transport time course. Its instructions correctly distinguish accumulated tracer from initial flux, but that distinction in TASK alone does not implement flux extraction or scoring. Another existing path could supply some needed components; a complete claim of transport coverage requires the actual combined path and source examples to be inspected. It cannot be established from this filename or operation count.

Fresh research workload174 is examining one retained Fluc study and its formal correction to determine concrete needed transport/channel components. Root has requested metadata-only messages until its current calibration packet/reset is complete; this review does not borrow or interpret174's experimental findings.

## Reproduced missing-input semantics defects

MISSING_INPUT_SEMANTICS_PROBE_001.json uses clearly synthetic inputs and the unchanged binding/transport modules from root172's frozen runtime, independently matched byte-for-byte to current code. No literature or actual model content was read by the probes.

1. Calling the transport pure calculator with Km=None gives `concentration_inputs_unreported` for the response. The calculator observed only an omitted argument, not that a publication lacks Km. Other branches use the same unsupported publication-absence language for missing concentration, curve identity, covariance and measurement identity.
2. Calling the binding model with a valid synthetic reported-parameter sheet and model=None gives `binding_sampling_model_unreported`. Model storage also labels its absent model `model_kind=unreported`, despite distinguishing `not_supplied` for other model metadata. Again, no publication-level absence was established.

These are incomplete implementation semantics under the fixed goal's distinction between missing source facts and missing implementation/selected inputs. A green parser test does not remove the defect.

## Prospective repair boundary

Publish new calculator/saved-record versions for new selected work using input-specific reasons such as `concentration_inputs_not_supplied`, `primitive_covariance_not_supplied` and `binding_sampling_model_not_supplied`. The absent binding model's new metadata should say `not_supplied`. Keep the original source facts, mathematical meanings, valid numerical results, observation models, covariance requirements and source roles intact.

Old v1 saved records and their original projected typed rows must remain exact. Use explicit readable-version support and version-aware metadata where necessary, rather than relabelling historical results or recalculating them. Projection schemas can admit legacy and prospective reasons without weakening numerical validation. The shared rate repository already offers `readable_record_versions`; the transport subclass's own strict version check must also accept its authentic old payloads. Binding model reconstruction must preserve its original upstream binding-sheet relations.

The anticipated ownership is the two calculator modules and their two storage modules, plus focused new/necessary compatibility tests. No shared rate-storage rewrite, new namespace/episode, W05/controller change, task narrowing or new overall quality score is needed. A fresh coding owner must receive this bounded design before editing; this document itself does not claim that repair has occurred.

## What this does not complete

Common whole-A105 numerical section assembly, assay-specific scientific compilation, source-defined complementary/independent/dependent evidence and broader coverage remain unfinished. The pending162 audit never supplied a final result. A root interruption attempt returned previous_status=pending_init, but a fresh list still reports it pending_init; do not claim the slot or audit was successfully closed. Two attempts to reactivate169 for the source unit dependency were rejected with `agent thread limit reached`. Root explicitly expanded current fresh173 ownership only for that coupled unit dependency; it is not an unrecorded extra owner or a goal change.
