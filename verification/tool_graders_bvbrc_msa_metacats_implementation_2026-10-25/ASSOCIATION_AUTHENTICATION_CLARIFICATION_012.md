# Original input authentication at the association boundary

Accepted additive clarification, 2026-10-25. The frozen association signatures
and original records remain unchanged by this clarification.

`extract_metacats_associations` receives analysis, documents, AssociationSet and
declarations. It receives no original InputBinding values. Its validation of
AutoGroupEntry covers exact known occurrence keys, binding identifiers, entry
indices/order, declared feature/group values and supplied member relationships.
It cannot authenticate a JSON pointer against original parameter content absent
from those operands. The adapter must check the original_parameter_pointer and
exact feature/group value against the actual original input before calling it.
Do not invent original content or claim the pure extractor checked absent data.

The common association declaration does not carry ReferenceBinding or Segment.
The association workload's reference/segment examples supply those separate
downstream operands using their accepted schemas, alongside actual associations.
They do not introduce hidden extra declaration fields.

This correction arose from coding worker142's inspection of the exact operands.
It adds no acquisition, runtime gate, model request or observation.
