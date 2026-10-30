# Infernal receiving-model presentation verification

Owned files: `tests/test_infernal_decision_presentation.py` and this directory.
No production changes, scientific execution, model inference, or network work.

Input evidence: exact retained native cmsearch scientific contexts 6 and 8 under
`tests/fixtures/native_infernal_episode`, with recorded byte hashes. Scientific
choices in the source run were scripted. Root variants and a historical pending
decision journal are explicitly synthetic.

Receiving contract: remove only automatically inserted native Infernal
observations from `working_state.observations`, before hashing model frames.
Preserve requested typed child rows, all other record kinds, explicit own action
outcomes and lookup results. Keep durable observations, calculator inputs,
schemas, instructions, action counts and numerical credit unchanged.

Consumer trace read: `decision_context.model_snapshot`, `state_frame`,
`apply_state_frame`; complete provider session/dispatch/presentation path;
complete public scientific renderer; complete `DecisionSource.call`,
`exchange_decision`, durable exchange storage and Journal; numerical return
selector/projection contracts and immediate-child return authentication path.

Verification covers bootstrap/update reconstruction, legacy scientific text,
legacy root serialization, requested exact numerical returns, reference-only
returns, explicit own outcome/lookup preservation, and restoration of a pending
old full snapshot with an already answered lookup and interrupted dispatch.
Restoration invokes actual `DecisionSource.call`/`exchange_decision`, real Store,
Journal and provider presentation. It stops at the selected response: no selected
action is executed and no scientific integration or native deployment is claimed.

Resource policy: existing bounded runner, 20 GiB RAM, 4 GiB scratch, no wall cap.
Literature graders and W05 aggregation remain outside this work.
