"""Actual shared unregistered same-axis improvement/job/entry-role default policy."""

def _default_scientific_child_roles(self):
    return (*(() if self.scientific_process_binding is not None else ('improvement',)), *(() if self.job_episodes is None else self.job_episodes.roles), *self.episode_bindings.entry_roles)
