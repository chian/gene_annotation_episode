# Occurrence dependencies and page counts

Additive root clarification after reviewing G3a code, 2026-10-27. No record
fields, scientific calculations or access authority change.

An occurrence's span depends on that occurrence's supplied coordinates. If a
parent explicitly selects known A occurrences and requests only span_bp, missing
B/C input does not invalidate those spans or membership in that explicit list.
Do not return the unselected input's failure for this request. Partner counts,
covered bases, coverage fractions and pair identities require both comparison
inputs and the corresponding native result, so retain their relevant failures.

An all-occurrences request is different: missing source rows can leave its
intended occurrence population incomplete, even if the available page contains
only known A rows. Keep the source incompleteness qualification. Existing
row/result extents continue to report the retained comparison's scientific
extent; a known span value remains a known value under that qualification.

`page.total_rows` is the count of filtered rows available in the retained
component table before paging. It is not an estimate of missing input rows or
of a complete intended scientific population. `returned_rows` counts the actual
page. Scientific input denominators remain the separate nullable region_count
and other numerical fields. A partial/unavailable source must retain its extent;
known zero available rows does not become a scientific no-hit result. Later
model-facing text must describe this pagination count as available rows.

Preserve the original request order when collecting failures from multiple
inputs. A Python set's iteration order must not determine the serialized result.
