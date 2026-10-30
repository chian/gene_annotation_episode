# Validate selected identities before prepared data exists

Additive correction to013 and015's `input_domains` argument, before deployment.
Earlier selected PreparationRequest.output records do not contain an executed
Domain. Creating artificial unavailable/applied Domain records merely to satisfy
a validator would misrepresent the available data.

`validate_preparation_request(value, *, input_domains)` therefore takes an
ordered list of exactly `DomainIdentity = {key, source_key, sample_key}`. These
are nonempty identifiers using the common key rules. Select the list for the
request.input.kind and resolve its per-kind index. Project the three fields
from actual EventInput.domain or earlier PreparationRequest.output. Validate
output sample and identity collisions against these declarations.

Full actual parent Domain, state, channel mapping and event correspondence are
still required and checked by the preparation execution and outcome-validation
ports. This correction removes invented pre-execution state; it does not relax
the actual numerical input requirements or change PreparationRequest itself.
Report-binding and producer consumers use the same projection and topology.
