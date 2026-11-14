from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.root_literature_contracts import (Mapping, deepcopy, replace, hashlib, inspect, json, Path, ReportBoundaryError, plain, validate_form, CONTRACT_INFORMATION_PROFILE, ContractError, REF, identity, obj, source_location_inputs, validate_schema, reference_in_context, VERSION, ROLES, _REFERENCES, _REPRESENTATION, _NATURAL, _POSITIVE, _TEXT, _WINDOW, _TABLE, _PAGE, _CHILDREN, EXPERIMENT_DATABASE_TOOLS, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _A108_ACCESS_TOOLS, _A108_ACQUISITION_TOOLS, _A108_NAMESPACES, _READ_TOOLS, _ROLE_INSTRUCTIONS, _a108_population_catalog, _population_catalog)

class LiteraturePolicy:
    def _enabled(self, option, context=None):
        """Select this invocation's native capabilities from its original commission."""
        configured = getattr(self, option)
        if not self.axis_scoped_profiles or context is None or context.role == 'annotation':
            return configured
        axis = None
        if context.role == 'scientific_process':
            axis = context.assignment.get('selection', {}).get('evidence_axis', {}).get('option_id')
        else:
            from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef
            store = self.services.workflow.store
            for length in range(len(context.path) - 1, 0, -1):
                path = context.path[:length]
                if path[-1][0] != 'scientific_process':
                    continue
                identity = EpisodeRef(context.run_id, path).episode_id
                row = store.db.execute(
                    'SELECT request FROM runtime_episodes WHERE run_id=? AND episode_id=?',
                    (context.run_id, identity)).fetchone()
                if row is None:
                    raise ContractError('literature_original_axis_commission_required')
                axis = json.loads(row['request'])['message'].get('episode_assignment', {}).get(
                    'selection', {}).get('evidence_axis', {}).get('option_id')
                break
        if axis not in {'A101', 'A102', 'A103', 'A104', 'A105', 'A106', 'A107', 'A108', 'A110'}:
            raise ContractError('literature_original_axis_owner_required')
        return configured and axis == {
            'assay_grading_population': 'A105',
            'a106_intervention': 'A106',
            'a108_context_evidence': 'A108',
        }[option]

    def contract_information_configuration(self):
        return self._contract_information_profile

    def contract_information_profile(self, context):
        if (context.role in ROLES or context.role == 'annotation' and len(context.path) == 1
                and self.reference_parent_sources is not None):
            return self._contract_information_profile
        return None

    @staticmethod
    def _role(role):
        if role != 'literature_strategy':
            raise ValueError("unsupported_literature_role:" + str(role))
        return role

    def credit_kind(self, role):
        self._role(role)
        return "scientific"

    @property
    def supports_wait(self):
        """Only A106 binds waiting to its intervention/analysis work."""
        return self.a106_intervention and (self.axis_scoped_profiles or not self.a108_context_evidence)

    def permitted_common_actions(self, context):
        self._role(context.role)
        if self._enabled('a106_intervention', context) and not self._enabled('a108_context_evidence', context):
            return ("tool", "reason", "child", "wait", "redeliver_report")
        return ("tool", "reason", "child", "redeliver_report")

    def allowed_children(self, parent, caller_capabilities):
        self._role(parent.role)
        # These are available branches, never automatically instantiated work.
        return self.child_roles(parent.role, context=parent)

    def child_roles(self, role, *, context=None):
        self._role(role)
        self._enabled('a106_intervention', context)
        return ('literature_search',)

