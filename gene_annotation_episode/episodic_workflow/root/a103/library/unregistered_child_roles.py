"""Shared original unregistered-parent improvement/job/entry child defaults."""
from __future__ import annotations

def _default_scientific_child_roles(self):
    return (*(() if self.gene_context_evidence_binding is not None else ('improvement',)), *(() if self.job_episodes is None else self.job_episodes.roles), *self.episode_bindings.entry_roles)
