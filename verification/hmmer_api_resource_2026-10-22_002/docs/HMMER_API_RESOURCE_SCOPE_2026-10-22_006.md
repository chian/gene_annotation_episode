# Selected results commissions retain their actual resource

Root and C traced the actual producer and consumer. Results assignments keep
their selected resource at `assignment.handoff.resource_selection`, but
`Workflow.commission_child` previously copied only the top-level
`assignment.resource_selection` into a new durable C1 commission. It therefore
saved None for results, despite the immutable original handoff being selected.

Root owns a bounded correction in the isolated runtime producer: for newly
selected `resource_results_assignment_v1`, persist the exact original handoff
selection in C1.resource_selection. Other assignment contracts keep their
existing top-level selection behavior. No resource choice, substitution or
allocation is made by this copy. Recovery reads original saved C1 records and
does not regenerate or rewrite them. The live source/run is unchanged.

For the newly introduced API provider at this new implementation, C validates
equality of the derived selected API resource and the durable commission's
selection for both launch and results. New results fixtures must represent the
corrected actual producer; an inconsistent non-null selection must be rejected.
Historical native providers/pins are not reinterpreted. This records the reason
for changing the producer before strengthening the new API consumer.

Verification must exercise the actual selected-results commission path, the
exact handoff/C1/child equality, original replay and rejection of mismatches.
This clarification adds no episode, status refresh, numerical policy or gate.
