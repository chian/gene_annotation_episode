# Original return provenance at closure

Additive clarification for workload435, 2026-10-27. This supplements014;
it does not change the scientific fields, scoring, or the user's goal.

## Construction before durable commissioning

Runtime construction freezes `EpisodeReceipts.bind` before calling the
specialist's `initialize`; it saves `runtime_episodes` afterward. The parent
commission is subsequently selected. This order is visible in runtime.py's
episode construction and `commission_child` implementations.

Only in this construction-only case, saved-sheet operand authentication may
use the authenticated unsaved BindingContext, exact assigned saved-sheet
identity, and the actual frozen `received_report_prefix`. There must be no
saved child, own action or frozen form. After construction, the original saved
commission is required. This is not permission to use later parent arrivals.

## Frozen forwarding origins

The existing `runtime_forms.facts` is the immutable original publication.
Its public scientific arrays alone do not distinguish identical saved-sheet
bytes received from different results episodes at different times. Reading
all current inner returns could incorrectly add a later origin to an older
forwarded form.

Add this return-authority port:

```python
facts_for_closure(context, schema) -> dict
```

For a scientific receiving episode it returns the selected public fact groups
and one private key, `genomic_overlap_received_report_prefix`. That key uses
the existing `frozen_received_report_prefix_v1` shape: version and the ordered
successful relevant immediate-child attempt witnesses, each with the original
decision index, delivery identity, child identity, contract digest and form
digest. Capture the prefix and corresponding public facts in one Store read
snapshot. Keep the existing `received_facts` API public-only.

Root will call this port from `ExecutionEpisodes.facts`. Ordinary runtime form
publication stores the private key in its existing facts record. Only the
three registered genomic-overlap x-sources are selectable into the return
form. The private provenance is not a model-prompt field, source-library entry,
new observation, or a separate journal.

Historical scientific forwarding must require and validate the recorded
prefix and recurse only through those exact original attempts. A missing
historical prefix is an explicit authority failure; never reconstruct it from
current arrivals. Adding an identical sheet from another origin later must
not change an old forwarded form's origins. Multiple genuine origins already
received at closure remain distinct and ordered. Construction-time inherited
prefixes and closure-time forwarding prefixes serve their respective existing
boundaries; neither replaces the other.

Verification must cover missing or altered witnesses, late same-byte origins,
pre-closure multiple origins, frozen historical values, and requested-only
public returns. Root still owns full runtime integration. This contract does
not establish a completed Workflow path or change the112/308 count.
