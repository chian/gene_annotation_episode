# Synchronous form-reference reuse: inspected consumer trace

This is prospective integration preparation from the current production tree
containing the applied worker175 submitted-request repair. No production or
earlier candidate source was changed. The five source files in the delta are
byte-identical to the reviewed candidate001 source files.

## Ownership and complete changed paths

`communication.validate_form` opens a new synchronous frame and delegates to
the original validation body. Closed-schema, finite-number, value-shape,
literal-format and per-reference resolver checks are unchanged. The context
manager invalidates and empties its frame in `finally`, then restores the
previous context. Nested validation therefore receives a separate frame and
restores its outer frame; a copied context retains only an expired frame after
the creator exits.

`form_reference_validation._binding_key` accepts only the exact
`BindingContext` type for sharing. The key includes every field emitted by
`BindingContext.as_record()` (run, episode, role, path, scope, assignment and
request) plus `received_record_refs`. Unknown context types get distinct
keys. Each provider key also contains that provider instance and own/received
direction. Own-fact keys include the canonical exact requested schema.
The stored object and each returned value are detached copies. Failed factories
leave no value. Calls without an active frame call the original factory.

The complete `BVBRCAlignmentReturns` and `BVBRCGenomeAlignmentReturns` modules
were read, including current own facts, received context, original saved-value
validation, source possession, frozen forms, historical return checks, admission
and namespace resolution. Only `resolve_own` and `resolve_received` now obtain
their authenticated fact dictionaries through the helper. Each reference still
traverses the original fact schema and its existing possession branch. Neither
provider's value validator or admission method is replaced or memoized.

## Receiving and authentication consumers

The complete implementations of `BindingContext`, `EpisodeBindingRegistry`,
`EpisodeReturnRecords`, `AppServiceCustody`, `BVBRCAppServiceHost`,
`AppServicePublications`, `read_latest_adapter_result`, both saved projection
modules and both provider facade files were inspected. The following complete
functions in larger consumers were also read:

* `APIServiceExecution.__init__`, `_own_outcomes`, `facts`, `resolve`.
* `ExecutionEpisodes.received_report_sources`, `received_report_facts`,
  `resolve_received_reference`, `validate_received_report`, `fact_sources`,
  `_has_appservice`, `_appservice_sources`, `facts`, `received_form_references`,
  `resolve`, `validate_report` and their forwarding predicate.
* `Workflow.returned_request`, `next_return`, `binding_context`, `receive_form`,
  `_receive_form`, `validate_report`, `resolver`, `selected`, `save_attempt`,
  `redeliver`, `facts`, and the complete `TypedReportContract` class.

Public API/execution resolver methods still route by actual namespace and role.
Scientific parents consume received facts; results children consume their own
facts. `TypedReportContract.admit` finishes `validate_form` before invoking its
semantic validator, so the frame has expired before semantic admission. The
semantic validator still checks returned numerical values against the original
authenticated saved facts. Recorded immediate-child returns still validate the
original selected commission, requested schema, original frozen form/facts and
source possession. GenomeAlignment historical returns remain bound to their
named publication, not the latest publication.

`read_latest_adapter_result` still selects by actual action order and reads the
chosen publication. `AppServicePublications.read` still checks saved native
receipts, original request and selector, dependency inputs, content hashes and
lengths, adapter result, outcome and completion evidence. The source and content
authentication path was not changed. No parser, calculator or acquisition was
added to saved form validation.

## Dependency pins

`DEPENDENCY_AUDIT_001.json` records an AST traversal of actual package imports,
including function-local imports and local schema assets, before and after this
patch. Homology, phylogeny, MSA/MetaCATS and proteome scientific-provider import
closures do not gain a changed source. GenomeAlignment's closure grows from
43 to 45 files: `episode_bindings.py` and `form_reference_validation.py`.
Its explicit dependency list contains that exact resulting source/asset closure.
Tests independently traverse that closure and mutate every listed dependency
in memory to verify pin sensitivity.

The independent-execution implementation digest already walks all application
and method_loop Python sources. It therefore includes the added helper without
a change to its digest algorithm. Existing pinned histories are not rewritten.
No additional source consumer needs an edit for this patch. Proteome return
hooks belong to worker176 and are absent from this delta. Root directly
confirmed the helper and communication hashes match worker176's candidate.

## Verification scope and preserved limitations

The added public GenomeAlignment test uses the production selected-operation
executor, custody, publication and return providers with controlled transport
responses and retained native bytes. It exercises public execution-family/API
resolvers, both directions, independent later forms, direct calls, semantic
corruption and repeated source possession. It checks unchanged saved sheet,
components and runtime action/observation/return/receipt rows. The MSA counting
test uses the actual return provider/custody with an explicitly controlled
publication envelope. These are focused engineering checks, not a new Workflow
run, live BV-BRC execution or configured-model investigation.

The complete fixture006 source and its entire production diff were reviewed.
Its only existing-test changes select episode roles from actual context,
expect `task_result_manifest`, and scope temporary parser barriers so replay
barriers capture original functions and their aliases. Numerical expectations
are unchanged. Additional tests are confined to the owned new frame-test file.

The earlier candidate006 six-test controlled Workflow receipt remains earlier
candidate evidence. The original161 run remains one pass, one fixture failure
and four tests not run, as reported by root; this prospective patch does not
repair or relabel that historical receipt. Root owns the applied-checkout full
selected-tool/child/result/typed-return verification.

Presentation remains incomplete: some scripted contexts omit `action_yields`,
and some STEERING blocks are long and contain tracking details. This patch does
not edit prompts, invent yield-table data or establish that presentation
requirement. No numerical formulas, credit, scheduling, episode types or
method_loop files are changed.
