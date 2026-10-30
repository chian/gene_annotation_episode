# Isolated API timing identity clarification020

This new clarification resolves the ambiguous binding_ref name in scope016; it
changes no prior record, active application source or scientific workspace.

ApiTimingOrderBindingV1.binding_ref is the content-addressed identity of that
exact closed order marker: api_timing_order_binding_ followed by SHA256 of the
canonical marker before adding binding_ref. Intent, submission and witness
order_binding_ref fields name that same marker. The exact scope019 ledger
owner has the separate api_timing_binding_ identity of ledger.as_record().
These identities are not interchangeable. Marker use still revalidates the
committed original order, request, scope and exact Store/run/registry/binding.

No extra field is added to either closed record and no provider order, claim,
receipt, HTTP capture, timing unit or statistical contract changes. The shared
ledger remains custody information and cannot authorize provider work.

Transient optional timing-storage failure must not block otherwise selected
search work. A foreign immutable owner mismatch remains an error. Storage
unavailability does not permit custody writes or exports without successful
exact owner validation, condition recapture, retrospective eligibility or
substitution of an unspecified condition. The concrete implementation path is
being checked by the custody and integration owners; this clarification does
not assert that verification is complete.
