"""Recognize the actual exposed BLAST job for this monitor's existing continuation rule."""
from __future__ import annotations
from collections.abc import Mapping

def is_blast_job(services, context):
    describe = getattr(services, 'describe_progress_target', None)
    if not callable(describe):
        return False
    target = describe(context.assignment['target_handle'], context.scope)
    return isinstance(target, Mapping) and target.get('resource_kind') == 'api' and (target.get('service_or_program') == 'ncbi_blast')
