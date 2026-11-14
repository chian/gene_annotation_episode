"""Select an existing private task by its actual commissioned structural path."""


class RootTaskSelection:
    def task_source_for_path(self, path):
        # The root annotation task has its own source and scientific callbacks.
        # Other roles must supply their actual private task through the binding
        # selected from the complete lineage. There is no shared task fallback.
        if len(path) == 1 and path[0][0] == 'annotation':
            from .episode import SignedRootEpisodeBinding
            binding = SignedRootEpisodeBinding
        elif path[-1][0] == 'improvement' and 'improvement' not in self.episode_bindings.roles:
            from .legacy_annotation.episode import LegacyAnnotationEpisodeBinding
            binding = LegacyAnnotationEpisodeBinding
        else:
            from .library.homology_episode_family import HomologyEpisodes
            if type(self.job_episodes) is HomologyEpisodes and path[-1][0] in self.job_episodes.roles:
                binding = self.job_episodes.implementation_for_path(path)
                task = getattr(binding, 'decision_source_type', None)
                if not isinstance(task, type):
                    raise LookupError('private_episode_task_not_bound:' + '/'.join(role for role, _ in path))
                return task
            if self.episode_bindings.private_owners:
                owner = self._binding_owner_for_path(path)
                binding = self.episode_bindings.for_path(path, owner=owner)
            else:
                binding = self.episode_bindings.for_path(path)
        task = getattr(binding, 'decision_source_type', None)
        if not isinstance(task, type):
            raise LookupError('private_episode_task_not_bound:' + '/'.join(role for role, _ in path))
        return task
