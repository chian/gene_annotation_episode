"""Prospective signatures for447; this file is not imported by production.

No implementation, compatibility layer or new authority store is supplied.
All dict arguments/results are the existing C1/441 records unless explicitly
identified as the existing runtime context, scope or source-group map.
"""
from typing import Callable, Protocol, TypeAlias, TypedDict
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords

class ResultOrigin(TypedDict):
    episode_id: str
    operation_key: str

FactGroups: TypeAlias = dict[str, list[dict]]  # Exactly the three FACT_SOURCES.
ReferenceAccess: TypeAlias = Callable[[BindingContext, str, str | None], bool | None]

# A owns chromatin_interaction_operands.py.
def validate_chromatin_job_inputs(
    store, context: BindingContext, assignment: dict, *, reference_access: ReferenceAccess
) -> list[str]: ...

# Required existing-owner property: owner.native_chromatin_interaction_results.
# The host owner implements this protocol; B does not implement it.
class ChromatinResultHost(Protocol):
    def applies(self, context: BindingContext) -> bool: ...
    def own_fact_groups(
        self, context: BindingContext, *, verify_artifacts: bool
    ) -> FactGroups: ...
    def completed_saved_bundle_origins(
        self, context: BindingContext, bundle: dict
    ) -> tuple[ResultOrigin, ...]: ...
    def owns_reference(self, reference: str) -> bool: ...
    def resolve_own(
        self, context: BindingContext, reference: str, namespace: str | None
    ) -> bool: ...
    def retained_target(
        self, context: BindingContext, assignment: dict, scope: dict
    ) -> dict | None: ...

# B owns chromatin_interaction_returns.py. These methods read authority;
# record_admission returns receipt candidates and does not insert them itself.
class ChromatinInteractionReturns(EpisodeReturnRecords):
    def __init__(self, owner) -> None: ...
    def authenticate(
        self, context: BindingContext, *, allow_unsaved: bool = False
    ) -> BindingContext: ...
    def facts(self, context: BindingContext, schema: dict) -> FactGroups: ...
    def facts_for_closure(self, context: BindingContext, schema: dict) -> dict: ...
    def validate_received_report(
        self, context: BindingContext, form: dict, schema: dict
    ) -> None: ...
    def record_admission(
        self, context: BindingContext, form: dict, schema: dict, operation_key: str
    ) -> list[str]: ...
    def resolve_received(
        self, context: BindingContext, reference: str, namespace: str | None
    ) -> bool: ...
    def authenticate_received_saved_bundle(
        self, context: BindingContext, bundle: dict
    ) -> tuple[ResultOrigin, ...]: ...

# A successful FactGroups has all requested exact source arrays. The host's
# own_fact_groups always returns all three. The closure method additionally
# returns private chromatin_received_report_prefix metadata using the existing
# frozen_received_report_prefix_v1 shape. It is not a registered fact source.
# Historical paths never call retained_native_file/get_artifact or read arrays.
