"""Private A104 API instructions."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain

class APIInstructions:

    def instructions(self, context):
        assignment = self._validate_request(plain(context.assignment))
        service = assignment['service']
        return f'Carry out the assigned work through {service} using one selected operation each turn. Keep the original inputs, request, resource and parent constraints fixed. Choose useful preparation, service requests, observations or repair from the actual available operations and received outcomes. Distinguish an immediate returned response from a service job that continues remotely. Preserve the actual request or job identity and submission uncertainty; a missing reply does not establish that no job was created. Establish the requested usable monitoring/results handoff from recorded service facts. The configured controller governs continuation; verified original handoff completion gives exact zero future credit.'
