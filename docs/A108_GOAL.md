
Complete A108’s organism and sample compatibility workflow using the repository’s existing literature and database tools. Starting from supplied biological material and any legitimately supplied context, the episode must discover relevant evidence, assess whether a possible function’s requirements fit the actual biological setting, populate the existing A108 numerical sheets, and deliver the resulting subscore to its parent.

Completion requires demonstrated full episode behavior and final numerical delivery. Implemented readers, downloaded sources, populated worksheets or successful parent receipt alone are insufficient.

1. Keep the scientific responsibility fixed.

   A108 asks whether a possible function makes sense in the relevant organism, strain, clade, compartment, environment or sample, given source-supported biological requirements.

   Preserve the distinction between:
   - Organism capability: whether at least one permitted biological state supports the function.
   - Sample-context coverage: what fraction of a defined sample’s opportunities satisfies the requirements.

   Select the question from the biological claim before calculating its result. Preserve that choice and scope through the investigation; any revision must be explicit. Do not choose whichever interpretation produces a larger number.
2. Follow A105’s investigation structure while retaining A108’s scientific meaning.

   Use the same general progression: source discovery, source reading, evidence assessment, subscoring sheets and final axis output. Reuse existing episode infrastructure, provenance handling, readers, grading conventions and typed returns wherever applicable.

   Retain A108’s existing requirement_compatibility assessment and compatibility calculations. A105 activity measurements may support a functional requirement, but their reuse must preserve the original measurement identity and dependence.

   A108 consumes relevant findings from other axes when available. Building homology searches, phylogenetic analyses, partner-presence analyses or biochemical feasibility pipelines is outside this goal.
3. Use existing repository tools and keep processing limited to evidence interpretation.

   Inspect the repository’s actual callable tools, contracts and configuration. Use existing literature searches, database queries and source-reading operations. Do not search the web for additional tools or introduce external analysis packages or new database services.

   Necessary implementation work may expose existing operations to A108, repair their integration, and add readers or adapters for evidence returned by those operations.

   Permitted processing includes parsing source records, preserving table structure, identifying supported operands, justified unit conversion and existing deterministic compatibility calculations. Raw sequencing analysis, expression analysis and other new bioinformatics pipelines are outside scope.
4. Establish both the functional requirement and the observed context.

   For every assessed requirement, retain:
   - Its biological meaning, source and relationship to the possible function.
   - The relevant organism, strain, compartment, condition and time scope.
   - Supported, incompatible and unexamined states or values.
   - The corresponding context observation, units, uncertainty and limitations.

   An assay condition is not automatically a necessary condition, optimum or operating interval. A database annotation or taxon label is not automatically a measured trait. A bulk environmental measurement is not automatically local exposure.

   Preserve source-reported facts separately from the episode’s interpretation. Database records should provide identifiable evidence or useful discovery leads; their presence alone earns no score.
5. Preserve compatibility, incompatibility and uncertainty correctly.

   Missing evidence, an unsuccessful search, an unavailable source and a measured incompatible condition are different outcomes.

   Evidence for separate requirements does not establish that they hold together. Preserve actual pairing, shared observations, sample denominators and biological units. Do not multiply unpaired marginal frequencies or treat technical repeats as independent samples.

   A compatible witness establishes capability only within its supported scope. Failure to find such a witness does not establish impossibility while relevant states remain unexamined. Genuine alternative routes must retain their own requirements and source support.

   Keep logical bounds, measurement uncertainty and sampling uncertainty distinct. Do not turn reported SD into an admissible interval, nondetection into zero, or an unresolved interval into a point estimate.
6. Complete the numerical connection without inventing scoring policy.

   Trace the complete path:

   Source evidence → supported operands → requirement assessment → saved compatibility calculations → final A108 subscore → parent consumption.

   Use implemented and agreed numerical definitions. Retain units, conditions, formulas, bounds, missing reasons and source references throughout this path.

   Determine explicitly whether any missing connection is an implementation gap or an unresolved scientific definition. Implement missing wiring under existing definitions. Do not silently adopt a research proposal, invent a weighting rule, add an arbitrary threshold or substitute a verbal plausibility grade.

   If a necessary scientific definition is genuinely unresolved, present the exact decision and its consequences while completing independent authorized work. The goal remains incomplete until that requirement is resolved; it cannot be bypassed by renaming an intermediate calculation as the final subscore.
7. Give the episode a clear, positive scope.

   The prompt must explain A108’s question, its available operations, the evidence each operation can supply, the applicable assessment structure and the required return.

   The episode chooses searches, source selections, interpretations and further work itself. Prompts must not contain test-specific clues, expected conclusions or instructions that force particular resources.

   If the episode attempts work outside its supplied role and operations, retain the trace and diagnose the scope or interface failure. Do not conceal the failure by manually steering that evaluation or adding test-specific prohibitions.
8. Validate through full autonomous workflows.

   Select real microbial examples with independently established expectations accessible through existing tools. Record those expectations separately before evaluation.

   Include anonymous sequence-only discovery. Where a sample-context question requires supplied context, provide only legitimate task inputs, clearly separated from evaluator knowledge. Do not supply identifying sequence headers, expected publications, database accessions, answer-bearing hints, preloaded assessment sheets or scripted decisions.

   The full runs must collectively demonstrate:

   | Validation case | Required behavior |
   |---|---|
   | Supported compatibility | Independently recover evidence for the requirements and matching context; deliver the justified numerical result. |
   | Supported incompatibility | Identify an actual necessary exclusion and preserve its scope; distinguish it from missing evidence. |
   | Insufficient context | Retain useful findings while returning unresolved components and specific missing reasons. |
   | Sample-context coverage | Recover a defined frame, denominator and relevant context observations; calculate coverage under the existing rules. |
   | Multiple requirements or routes | Preserve joint support and genuine alternatives without assuming independence. |
   | Literature and database evidence | Demonstrate useful evidence from both, with repeated representations and shared measurements handled correctly. |

   One case may cover several criteria. Both capability and sample coverage must be exercised. At least one sufficiently supported case must deliver an actual final numerical point result; bounds and unresolved results must remain available where appropriate.

   Validate through complete episode runs and inspection of their sources, traces, sheets and final outputs. Do not substitute targeted checks, unit tests, scripted episodes or manually populated evidence for this validation.
9. Preserve run integrity and report status accurately.

   Do not introduce unapproved wall-clock, action-count or budget cutoffs. Do not terminate active runs because they are taking longer than expected. Leave unrelated running work undisturbed.

   Record the actual interpreter, configuration, source version, input and process identity for each run. Preserve failed attempts and explain repairs. Distinguish process launch, active investigation, operational failure and completed scoring.

   Keep disposable output, temporary files and caches under separate directories within runs/. Keep reusable code and required fixtures in their proper source and test locations. Preserve existing user work and unrelated axis behavior.
10. Deliver an auditable completion report.

Provide the final A108 prompt; the available tool and reader mapping; the implemented path into the final subscore; and a case-by-case comparison of expected versus observed behavior. Link the actual traces, source evidence, sheets and parent outputs.

Report every unmet criterion and material limitation explicitly. Declare completion only when the demonstrated behavior satisfies this goal—including final scoring—and the evidence supports that claim.