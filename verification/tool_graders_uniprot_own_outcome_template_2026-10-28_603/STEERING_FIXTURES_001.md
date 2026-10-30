# Illustrative same-episode STEERING fixtures

These are invented **rendering fixtures**, not fetched API results, saved runs,
scientific observations or test results. Identifiers and numerical native values
below describe the fixtures only. No actual yields were read or computed;
angle-bracket yield slots mean “copy this exact existing input” and are not
literal runtime strings or fabricated measurements. Neither example is a
parent-facing template. Both follow the full recurring TASK in
`TASK_TEMPLATE_001.md`.

For these fixtures the original parent selection asks for all native records on
the assigned page; primary accession, taxon ID, observed sequence length, a
protein-name text window at offset 20/limit 40, sequence `[9,19)` aa, GO xrefs,
and exact entry features overlapping `[9,20)` aa. It requests no source or full
sequence grant. The selected GO/feature collections have no additional prose
properties or associated evidence in these small fixtures. Their complete
typed field/state relationships remain in the internal intermediate.

## A. Complete native response and completed publication

This is a conditional rendering example only. If this acquisition validates
the original practical endpoint, the existing controller closes the episode
without sending a next-decision prompt. The example must never add a final
model call merely to show completion.

--- BEGIN COMPLETE STEERING FIXTURE ---

STEERING

| Own action category | Completed | Total signed yield | Expected next yield | Uncertainty / unavailable reason | Uncompleted attempts |
| --- | --- | --- | --- | --- | --- |
| tool/api.uniprot.collect | <saved completed count> | <saved signed total> | <saved category estimate or unavailable> | <saved band or unavailable reason> | <saved uncompleted count> |

| Current continuation | Supplied value |
| --- | --- |
| Expected next gain; uncertainty; cost | <existing controller values, including exact zero only when actually validated> |

| Latest acquisition | Result |
| --- | --- |
| Status | Completed; complete JSON; parser complete |
| Native / parser-eligible / bound records | 1 / 1 / 1 |
| Requested records returned | 1 of 1 |
| Response extent | One selected page; whole query complete |
| Native response | Retained |

| Requested record | Requested fact | Value and qualification |
| --- | --- | --- |
| P00001 | Taxon ID; observed sequence length | 9606; 318 aa |
| P00001 | Protein-name characters [20,60) | `ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmn`; 80 native characters; omitted prefix 20, suffix 20 |
| P00001 | Entry sequence [9,19) aa | `MKTAYIAKQR`; 10 residues |
| P00001 | GO cross-references | GO:0000001 and GO:0000002; 2 matching, 0 indeterminate, 0 unavailable, 30 excluded |
| P00001 | Features overlapping [9,20) aa | Exact entry interval [9,15) aa; 1 matching, 0 indeterminate, 0 unavailable, 1 excluded |

--- END COMPLETE STEERING FIXTURE ---

## B. Partial native projection with valid requested data

Native JSON is fully retained; a malformed middle native record cannot be
published. Valid record positions remain 0 and 2. One selected field in position
2 is absent, not numerical zero. An indeterminate GO database field cannot be
silently excluded from an absence finding. No next cursor is printed because
it was not requested; the original assigned page stays fixed.

--- BEGIN PARTIAL STEERING FIXTURE ---

STEERING

| Own action category | Completed | Total signed yield | Expected next yield | Uncertainty / unavailable reason | Uncompleted attempts |
| --- | --- | --- | --- | --- | --- |
| tool/api.uniprot.collect | <saved completed count> | <saved signed total> | <saved category estimate or unavailable> | <saved band or unavailable reason> | <saved uncompleted count> |

| Current continuation | Supplied value |
| --- | --- |
| Expected next gain; uncertainty; cost | <existing controller values> |

| Latest acquisition | Result |
| --- | --- |
| Status | Partial; complete JSON; parser partial |
| Native / parser-eligible / bound records | 3 / 2 / 2 |
| Requested records returned | 2 bound of 3 requested; original positions 0 and 2 |
| Response extent | One selected page; another page indicated; whole query incomplete |
| Native response | Retained |

| Requested record | Requested fact | Value and qualification |
| --- | --- | --- |
| P00001, native position 0 | Taxon ID; observed sequence length | 9606; 318 aa |
| P00001, native position 0 | Protein-name characters [20,60) | `ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmn`; 10,000 native characters; omitted prefix 20, suffix 9,940; native text present |
| P00001, native position 0 | Entry sequence [9,19) aa | `MKTAYIAKQR`; 10 residues |
| P00001, native position 0 | GO cross-references | GO:0000001 and GO:0000002; 2 matching, 1 indeterminate, 0 unavailable, 29 excluded |
| P00001, native position 0 | Features overlapping [9,20) aa | Exact entry interval [9,15) aa; 1 matching, 1 indeterminate fuzzy feature, 0 unavailable, 0 excluded |
| Native position 1 | All selected fields | Unavailable: native record is not an object |
| P00002, native position 2 | Taxon ID; observed sequence length | Taxon ID absent; 200 aa |
| P00002, native position 2 | Protein-name characters [20,60) | Native field absent |
| P00002, native position 2 | Entry sequence [9,19) aa | `ACDEFGHIKL`; 10 residues |
| P00002, native position 2 | GO cross-references | Present empty collection: 0 matching, 0 indeterminate, 0 unavailable, 0 excluded |
| P00002, native position 2 | Features overlapping [9,20) aa | Present empty collection: 0 matching, 0 indeterminate, 0 unavailable, 0 excluded |

| Material qualification | Effect |
| --- | --- |
| Native position 1: record_not_object | Parser-unpublishable sibling; the two bound records remain usable |
| P00001 name: uniprot_legacy_label_unrepresentable | Selected native name window remains available; legacy label cannot represent the full value |
| P00001 GO collection: one database value invalid | Membership of that member is indeterminate |
| P00001 fuzzy feature | No exact entry interval supplied |

--- END PARTIAL STEERING FIXTURE ---

The rows use no host/source/witness ID, digest, raw native paragraph or complete
sequence. Present empty collections are positive facts about those selected
collections; they do not assert absence across the entire query. There is no
recommended next action, unrequested page selection, fabricated wait estimate,
copied parent yield or final model-composed return.

## Other states the same renderer must preserve

* Complete parser state with 3 parser-eligible records, 2 actual bindings and
  outer partial: show `complete / 3 / 2 / partial` without changing parser state.
  The selected omitted record gets its existing `binding_omitted` failure.
* Missing header observation: show “pagination unknown; whole query unknown”.
  It is not an absent next link, an empty page, or whole-query completion.
* No `uniprot_selected_returns` in the original contract: show the acquisition
  status/extent and page-wide material failure only. Do not select native values
  by convenience or replace the form with a latest-result summary.
* A known-primary-accession selector finding no definite match while a native
  identity is malformed: show the indeterminate-selection qualification. Do
  not print “accession absent”.
* A selected grant is unavailable: show that status and its existing reason,
  without inserting a full source/sequence or a new read into the message.

These are rendering requirements for later verification, not executed checks.
