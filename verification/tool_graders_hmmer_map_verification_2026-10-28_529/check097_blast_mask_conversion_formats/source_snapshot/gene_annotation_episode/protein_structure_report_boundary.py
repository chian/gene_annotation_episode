"""Preserve authenticated typed custody without exposing it as model input.

Closed-schema, reference and semantic validation precede this boundary. The
exception concerns three internal custody fields, never scientific prose or
the inputs supplied to the parent's model.
"""
from collections.abc import Mapping
from dataclasses import dataclass, field

from method_loop.communication import ParentReport

from .communication import plain


_SOURCES = frozenset({"execution_protein_structure_projections",
    "execution_protein_structure_saved_sheets", "execution_protein_structure_sequences",
    "execution_protein_structure_failures"})
_CUSTODY_IDENTITIES = frozenset({"run_id", "result_episode_id", "result_operation_key"})


def recorded_protein_fields(schema):
    """Select only top-level fields already checked against exact D1 schemas."""
    return tuple(name for name, node in schema["properties"].items()
        if node.get("x-source") in _SOURCES)


@dataclass(frozen=True)
class ProteinStructureParentReport(ParentReport):
    _recorded_protein_fields: tuple[str, ...] = field(default=(), init=False, repr=False, compare=False)

    def exclude_audit_identifiers(self, identifiers, *, inputs=None):
        if inputs is not None:
            # The ordinary model-input restriction remains exact, even when a
            # caller mistakenly supplies a whole admitted custody descriptor.
            return super().exclude_audit_identifiers(identifiers, inputs=inputs)
        values = plain(self.values)
        for name in self._recorded_protein_fields:
            for row in values[name]:
                custody = row.get("custody")
                if isinstance(custody, Mapping):
                    row["custody"] = {key: value for key, value in custody.items()
                        if key not in _CUSTODY_IDENTITIES}
        return super().exclude_audit_identifiers(identifiers, inputs=values)


def admit_recorded_protein_report(contract, value, *, fields, audit_identifiers):
    """Called only after the typed contract's semantic validator succeeds."""
    report = ProteinStructureParentReport(contract, value)
    object.__setattr__(report, "_recorded_protein_fields", tuple(fields))
    report.exclude_audit_identifiers(audit_identifiers)
    object.__setattr__(report, "_audit_identifiers", audit_identifiers)
    return report
