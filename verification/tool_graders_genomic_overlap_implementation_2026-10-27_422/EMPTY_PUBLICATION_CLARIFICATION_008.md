# Mixed empty input and failed canonical publication

Additive correction, 2026-10-27. Root review and packet427 confirmed this case:
empty A has a complete parsed record and a published zero-byte canonical file;
B has a complete parsed record but canonical-file publication failed; C is
valid. The driver records AB and BC as native_unavailable, with the actual B
seal failure, and AC as analytic_empty. It preserves B's complete parsed record.

The prior batch validator incorrectly required analytic_empty for AB merely
because A's canonical file was empty. Root corrected its is_empty eligibility
check to require both canonical declarations present in addition to complete
parsed inputs and at least one zero-byte canonical. That admits the actual
failed-publication disposition without erasing B's parsed information or
claiming B's canonical file exists. Ordinary usable empty comparisons retain
their analytic behavior. G1 formulas and all original field meanings stay fixed.

Packet427 owns the concrete three-set regression. Root reruns the pure record
checks with the changed validator. Earlier verification receipts retain their
original source pins and are not evidence for this later change.
