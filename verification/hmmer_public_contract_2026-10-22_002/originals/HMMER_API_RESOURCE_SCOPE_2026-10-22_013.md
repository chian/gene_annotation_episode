# Optional result body clarification, generation002

This separate permanent clarification follows scope012; it does not replace it.
Current official HMMER OpenAPI ResultResponseSchema has required=['status'].
The result property is optional and nullable. A non-success response may omit it
entirely, as well as supply result=null. Therefore an omitted result on PENDING,
RECEIVED, STARTED, RETRY, FAILURE or REVOKED is not by itself invalid.

The coding worker must not require a result property before qualifying a valid
non-success state. Omitted and null non-success bodies use the same existing
result_not_ready or remote_job_failed failure mapping, with exact raw capture,
state, selection and replay retained. An explicitly present non-null body must
still be a dictionary and its present result.stats identities must match.
The successful acquisition contract remains stronger: SUCCESS still requires a
dictionary result, qualified identities and hits list before cache/publication.
This clarification adds no HTTP, new operation, retry, score or observation.

The exact fetched schema and pure checks are preserved under
/tmp/hmmer-public-api-contract-20261022-001. The independent documentation worker
reported this exact required array before implementation, correcting the proposed
test assumption that an omitted unfinished result must be invalid. No claim is
made that the public service actually emitted a pending/omitted response in this
session. Only official documentation and database metadata were requested.

