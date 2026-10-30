# Three-slot library curation scope

This work constructs source-grounded library content from the existing 142 distinct case groups. It does not implement episode construction, change runtime tools, adopt new credit axes/weights, or reinterpret saved credit.

## Stable work items

- [x] L1: Annotation-distinction options for slot 1, grounded in structured-credit representation.
- [x] L2: Iterative thought-pattern options for slot 2.
- [x] L3: Evidence-tool options for slot 3, with inputs, outputs and availability limits.
- [x] L4: Option-to-source inspection table and all-case coverage register.
- [x] L5: Worked compatible selections and specific incompatible combinations.
- [x] L6: Integrated consistency check and deliverable catalog.

The existing F01–F05 follow-up lanes keep their names/order. They remain research groupings, not an imposed episode hierarchy or already adopted scoring axes. New stable option IDs: A01… for annotation distinctions, P01… for thought patterns, T01… for tools. These are independent slot namespaces. Each option must expose its own contribution; avoid duplicating one fact in all slots or presenting tasks as thought patterns.

Completion evidence: L1=10 annotation entries; L2=19 thought entries; L3=13 tool contexts; L4=208 source links and all 142 groups; L5=23 selections and 6 specific mismatch examples; L6=validation.json plus current-catalog local-link and source-snapshot checks. Library content only; runtime construction remains outside this task.

## Handoff files and boundaries

Root owns this scope, case_records.json, sources/coverage integration, the composition table and the final rendered catalog. The slot curators each own only their assigned slot JSON. They can read all original research files. No repository implementation/design edits.

Each slot file has {slot, status, options:[...]}. Every option has id, name, description, evidence:[{case_group, case_id, source_url, source_locator, observation, limit}]. case_group/case_id must exist in case_records.json. source_url must be an existing primary-source URL/DOI from the record or its trace. A source_locator identifies a figure/table/section when the trace records it; otherwise say case-record observation with exact scope. Do not invent locators. The observation must state what made this option useful in this case. Preserve abstract-only status and author-reported versus actual research operations. A catalog option is not an independent observation or credit award.

Slot-specific fields:
- A: claim_scope, distinctions, example_structured_values (illustrative, not an adopted schema), not_established, follow_up_lane_ids. This describes the annotation property to represent using declared JSON fields/values, never discretionary credit judgment or proposed numerical weights. Do not label evidence modalities, tool outputs or all reasoning achievements as axes.
- P: use_when, live_alternatives, decision_guidance, outcome_contingencies, boundary. Define a reusable iterative thought pattern, not an ordered task list. Include concrete bioinformatics contrasts. Guidance narrows alternatives without choosing the episode's action or forcing one pattern for a whole investigation.
- T: capability_operations:[{operation, inputs, outputs}], availability, limits, observed_uses. Describe tools/tasks, not a covert scientific agent. Executable tool identities must be confirmed; otherwise label capability specification/candidate. Author-performed biological experiments are source evidence, not available execution capabilities. A tool option may contain a coherent small set of related primitive operations; it does not confer permissions or imply arbitrary tools mix freely.

Root integrates after all three independent catalogs are available. There is no coding dependency among these curation jobs. Compatibility examples depend on the final option IDs and semantics; rendering depends on evidence validation. Source mapping must account explicitly for all 142 groups, including groups not used to establish an option. No blanket claim that every group validates every option.
