"""Private A103 resource goal."""
from __future__ import annotations

class ResourceGoal:

    def contract_information_profile(self, context):
        return None

    def instructions(self, context):
        responsibility = 'Investigate the selected actual environment, queue, staging and execution interfaces.'
        discovery = " Within the pending decision, request_context with view=composition_information, operation=episode.return_contract and arguments role/source describes the permitted child's exact frozen fact contract. Select a top-level form field with only $ref set to episode-fact:<source> to have the host expand and fill that type. Choose the facts needed for the job. If a usable handoff is still uncertain, retaining the original job_ref and receiving state allows later work to repair that job without submitting a replacement." if self.contract_information_profile(context) is not None else ''
        return responsibility + ' Revise later choices from actual outcomes. Ordinary operations are tools; iteration belongs to this shared Episode. Preserve the parent job, input versions, CPU, search and constraints. Capabilities and duration estimates inform your decisions, without selecting an approach or imposing an order. Unknown/authentication-required resources remain explicit. Return the original parent-defined typed form. Only the configured local controller governs continuation.' + discovery
