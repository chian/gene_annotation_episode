"""Private A101 launch_api goal."""
from __future__ import annotations

class OperationalGoal:

    def instructions(self, context):
        self.credit_kind(context.role)
        responsibility = {'launch': 'Choose which actual execution approach is productive within the assigned job and constraints; commission a resource child when useful.', 'launch_api': 'Investigate execution through the selected actual API or service, including real availability and authentication.', 'launch_local': 'Investigate preparation, execution and receiving interfaces on the selected local resource.', 'launch_hpc': 'Investigate the selected actual environment, queue, staging and execution interfaces.', 'results': 'Acquire the requested data through the supplied receiving interface; the scientific parent interprets it.'}['launch_api']
        discovery = " Within the pending decision, request_context with view=composition_information, operation=episode.return_contract and arguments role/source describes the permitted child's exact frozen fact contract. Select a top-level form field with only $ref set to episode-fact:<source> to have the host expand and fill that type. Choose the facts needed for the job. If a usable handoff is still uncertain, retaining the original job_ref and receiving state allows later work to repair that job without submitting a replacement." if self.contract_information_profile(context) is not None else ''
        return responsibility + ' Revise later choices from actual outcomes. Ordinary operations are tools; iteration belongs to this shared Episode. Preserve the parent job, input versions, CPU, search and constraints. Capabilities and duration estimates inform your decisions, without selecting an approach or imposing an order. Unknown/authentication-required resources remain explicit. Return the original parent-defined typed form. Only the configured local controller governs continuation.' + discovery
