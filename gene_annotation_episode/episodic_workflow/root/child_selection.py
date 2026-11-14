"""Root-owned child_selection.py"""
from __future__ import annotations
from .receiving_context import BindingContext
from collections.abc import Mapping
from .episode_journal import WorkflowError
from .task_values import _plain
from .composition_information import restricted_root

from .root_binding_selection import RootBindingSelection

class ChildSelection(RootBindingSelection):

    def specialist(self, source):
        path = getattr(source, 'path', ())
        if not path:
            return None
        role = path[-1][0]
        return self.episode_bindings.for_path(path) if role in self.episode_bindings.roles else None

    from .library.child_role_policy import _default_scientific_child_roles

    from .library.child_role_policy import declared_child_roles

    from .library.child_role_policy import available_child_roles

    from .library.child_role_policy import validate_child_choice

    def job_implementation(self, *, path=None, parent_path=None, role=None):
        from .library.homology_episode_family import HomologyEpisodes
        jobs = self.job_episodes
        if type(jobs) is not HomologyEpisodes:
            return jobs
        if path is not None:
            return jobs.implementation_for_path(path)
        if parent_path is not None:
            return jobs.implementation_for_path(parent_path, child_role=role)
        # An original parentless metadata/validation interface, not an actual
        # child selection or a claim of context-authenticated task credit.
        return jobs.implementation_for(role)

    def job_descriptions(self, source):
        from .library.homology_episode_family import HomologyEpisodes
        jobs = self.job_episodes
        if (type(jobs) is HomologyEpisodes and self.specialist(source) is None
                and source.path[-1][0] in ('annotation', 'improvement')):
            return jobs.describe(parent_path=source.path)
        # Preserve the original information-only query on specialist sources.
        return jobs.describe()

    def job_commission_schemas(self, source, scientific_child):
        from .library.homology_episode_family import HomologyEpisodes
        jobs = self.job_episodes
        if type(jobs) is HomologyEpisodes:
            return jobs.commission_schemas(scientific_child, parent_path=source.path)
        return jobs.commission_schemas(scientific_child)

    def job_episode_options(self, source):

        if self.job_episodes is None or self.is_job_source(source):
            return None
        if self.annotation_child_roles is None:
            return self.job_descriptions(source)
        permitted = set(self.available_child_roles(source))
        options = {role: value for role, value in self.job_descriptions(source).items() if role in permitted and self.specialist(source) is None}
        return options or None

    def binding_context(self, source):
        return BindingContext(self.run_id, source.episode_id, source.path[-1][0], source.path, source.scope, source.request.message.as_record().get('episode_assignment', {}), source.request.as_record(), received_record_refs=tuple(self.receipts.known(source.episode_id)) if self.receipts is not None else ())

    def is_scientific_source(self, source):
        binding = self.specialist(source)
        return binding.credit_kind(source.path[-1][0]) == 'scientific' if binding else not self.is_job_source(source)

    from .library.child_role_policy import permits_common_action

    def is_job_source(self, source):
        return self.job_episodes is not None and source.path[-1][0] in self.job_episodes.roles

    def child_credit_arguments(self, source):
        """Only the original commission, never another child's private history.

        Fresh JSON values keep a caller projector from mutating the assignment
        used by the runtime and communication guard. The scalar is projected
        from recorded contributions, not from newly generated reporting prose.
        """
        contract = source.request.report_contract
        message = source.request.message.as_record()
        selected = message.get('episode_assignment', {})
        if not isinstance(selected, Mapping):
            raise ValueError('original_child_episode_assignment_required')
        assignment = {'goal': source.request.goal.as_record(), 'scope': source.scope, 'purpose': contract.decision, 'schema': contract.schema, 'initial_report': message['initial_report']}
        assignment.update(_plain(selected))
        return {'assignment': _plain(assignment), 'episode_id': source.episode_id, 'run_id': self.run_id}
