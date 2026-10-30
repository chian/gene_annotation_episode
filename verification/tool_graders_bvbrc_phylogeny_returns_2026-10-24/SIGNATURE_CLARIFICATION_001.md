# Saved identity proof dependency

Root clarification on 2026-10-24, additive to RETURN_WORKLOAD_001.md:

`project_phylogeny_facts(body, *, requested_sources, sheet_set)` receives the
authenticated saved `PhylogenySheetSet` as an explicit supplied value, or `None`
when the original publication has no sheet. The pure projection performs no I/O.
The return host reads only the original publication's `sheet_content` through
the existing authenticated publication content reader and supplies that value.

The saved sheet validates original slot, tree, alignment, split and scoped
integer identities. Returned numerical values remain exact copies of original
`AdapterResult.facts`; no parser, provider, calculator, new projection, new
acquisition or observation is invoked. The full sheet never enters an episode
form, model prompt or forwarded context. This is identity authentication, not
permission to expose unrequested quantities through a source reference.

The eight outer row payload keys confirmed with the bundle owner are `value`,
`branches`, `sites`, `members`, `functions`, `comparisons`, `requirements`, and
`qualifications`, in the order listed in RETURN_WORKLOAD_001.md. Canonical
references use the bundle contracts codec and saved analysis-local identities.
Requirement rows retain original C4 values; qualification requirement references
use the codec. Current scalar names include `literal_sum_squared_frequency` and
`literal_mean_squared_frequency`; original catalog 001 remains historical.
