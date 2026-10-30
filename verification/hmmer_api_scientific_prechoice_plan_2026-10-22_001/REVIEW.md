# Read-only planning review

Status: UNADOPTED. Reviewer `/root/api_timing_episode_integration/prospective_callable_map_review` independently read the actual callable map, scientific freezer/retriever, assignment preparation and saved reconstruction paths in003. The reviewer made no source changes, application calls or tests.

Corrections applied before handoff:

1. The proposed nested arguments schema initially represented subject_ref with a generic reference annotation. Actual `public.hmmer.search` uses domain.REF's required persistent ID/alias pattern and description. SCHEMAS.json now copies that exact target schema through static AST evaluation; the equality assertion passed without instantiating a ToolRegistry. The proposal requires code to reuse the actual target schema rather than rebuilding it.
2. The actual ProviderJobOperations attribute is remote_searches, not remote. The owner check now explicitly compares ports.operations.remote_searches with the actual ToolRegistry.remote_searches.
3. Factory preparation creates ports/ledger A before freezing, while existing composition reopens equivalent B objects. Equal-descriptor attachment must validate B and replace the handle with B, rather than retaining A. The final registry planner, API adapter and timing reader must share B's actual ports/timing identity; frozen map bytes remain equal. The proposal includes the identity test.
4. The runtime API discriminator must match both nested version/target and the actual selected arguments/candidate/constraints/versions; a tagged arbitrary result is insufficient. Produced API arrays must win over prior context copying.
5. Ordinary ToolRegistry handling maps a plain ValueError to generic invalid_tool_input. The proposal now names ContractError invalid_api_execution_statistics and api_execution_proposal_conflict for specific malformed statistics/local proposal failures; it preserves existing candidate/version diagnoses at the new tool boundary.

Confirmed seams:

- Scientific full map freezing must follow actual registry attachment. Adding an entry only to Workflow's helper catalog would not make it available to the constructed scientific child.
- Existing process.tools validates full map equality and the semantic retriever receives the complete real callable contracts. The child still receives only its selected tools.
- The existing native-only execution.estimate consumer requires an explicit API discriminator. Literature's branch filter requires preserving anyOf with properties.tool.const.
- The worker compares base tool resources before the service factory; the planner must remain in explicit service/map/adapter identity rather than being added to that earlier base record.
- The exact helper uses the actual subject/symbols/FASTA builder and existing request normalizer; no fake Launch context or inferred proposal is needed.

This review is source inspection of a plan, not implementation or scientific evidence.
