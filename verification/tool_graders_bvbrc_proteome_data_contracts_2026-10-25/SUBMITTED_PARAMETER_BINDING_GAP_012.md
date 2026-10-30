# Original submitted-parameter bytes: binding gap

Observed by provider worker173 and accepted by root, 2026-10-25. This is an
unfinished integration dependency, not a change to the scientific input index.

OriginalTask.submission_source_ref names the retained native submission source.
AppServiceRecords stores that source's exact request bytes in request_ref.
The AppService ContentBinding schema and the copies in the proteome native,
data and sheet schemas currently permit only artifact_ref, text_ref, stdout_ref
and stderr_ref as artifact_field. A submitted ParameterSource must retain the
original submission source identity; a receipt's different artifact source or
scheduler parameter echo cannot be substituted for it.

Until an explicit request_ref binding is implemented and verified through the
host's actual custody/content functions, the provider reports
proteome_parameter_source_unbound. Native numerical data remain usable when
independent of this missing input index. An explicitly supplied effective
parameter source is a distinct schema possibility, not evidence that the
current host supplies one.

The repair must extend the closed artifact-field alternatives where this actual
request content is permitted, preserve source possession and exact retained
bytes/digest/length, and verify the exact original request pointer against
OriginalTask.submitted_parameters. It must not mutate OriginalTask, add an
invented source alias, trust a hash without retained bytes, reacquire parameters,
or permit arbitrary artifact fields. Required checks include original submission
success, wrong source, wrong digest/length, wrong pointer/value, unrelated task,
and no hidden IO from the pure input-index construction. Shared source changes
must be staged while the original GenomeAlignment verification remains active.
