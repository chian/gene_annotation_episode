# Correction of assistant-authored instructions — 2026-10-23

This correction was requested by the user. The original record below is
preserved unchanged; the assistant's superseded interpretations are not current
requirements. No replacement scoring formula is adopted here.

The user's controlling instructions, verbatim:

> These individual scores need to be multipliers or sum in some way. WTF else would you do? Why do you keep trying to do somethign else. This is literally what I told you to do before with experimental reliablity

> THE PAPERS DO NOT OVERRIDE THE TEMPLATE. THEY GET CONVERTED THOUGHTFULLY

The papers supply measurements, experimental comparisons and limitations to
convert into the user's scoring template. They do not authorize replacing that
template with a new organization or with overall category grades. Individual
numerical components require their actual inputs and calculations, followed by
explicit sums/multipliers. Research examples must inform those calculations;
retaining measurements beside an overall grade does not accomplish this.

Specific corrections to assistant text in the preserved record:

- The five-level transfer scale is rejected, not still awaiting acceptance.
  Evidence relevance still requires component calculations and combination;
  the user did not restrict its evidence to sequence homology.
- The categorical experimental-relevance, measurement-validity and attribution
  scales, and the categorical signal fallback, have the same defect. Their
  labels and the surrounding formula are not accepted template definitions.
- The earlier prohibition on proposing weights/formulas under W04 must not
  prevent the explicitly requested component arithmetic. Defining and showing
  that arithmetic is required; production credit wiring remains separate work.
- The earlier three-responsibility table's candidate-annotation prerequisite
  and recordkeeping-only description of the sheet are superseded by the user's
  subsequent corrections already preserved below. Start from supplied material;
  produce actual numerical score components; readers populate those components.
- No completed general scoring sheet was delivered by these drafts. The user's
  current accounting is ten evidence axes, with zero completed scoring sheets.

<!-- PRESERVED ORIGINAL BELOW -->

# W04 — Fix the evidence-axis library: implementation instructions

Additive instruction record, 2026-10-23. This records the user's corrections
without replacing earlier permanent records. WORK_CHECKLIST.md tracks completion;
this document defines W04's deliverable. It does not adopt a scoring formula or
declare the current drafts correct.

## User's words

> there is what gets inserted into the prompt, there is the scoring rubric, and there is a separate grader/machine reading functions. that's it. it's one of those things or it's nothing

> Graders/readers are what POPULATE the scoring rubric

> Scoring rubric is not so much the formal rules as it is the scoring sheet, scoring format, scoring template. Yes?

> It must have formal entries it can be scored by and then it must be scorable by both literature findings and dataset analysis (let's say like a proteomics dataset from a specific experiment)

> This aspect that I am walking you through now, I need this for every single evidence axis.

## Scope and order

1. Follow W03's recovered decisions and the user's subsequent corrections.
   Preserve their exact wording and source locations. A105 is included; do not
   silently resolve the remaining A110 review, merge axes, or assume a final
   entry count. Unresolved decisions remain explicitly unresolved.
2. Keep the three construction slots `evidence_axis`, `thought_pattern`, and
   `child_tool_info` distinct. W04 supplies the evidence-axis library. An axis
   identifies evidence bearing on an annotation score; it is not an annotation
   identifier, a biological claim heading, a tool list, or an episode type.
3. Show the actual prompt insert, a filled scoring sheet, and the reader's
   concrete inputs/outputs for feedback before expanding the design across
   axes. The user's requested template feedback is an implementation step;
   do not add a runtime reviewer or approval mechanism.
4. Use a fresh coding subagent for each new workload, with a self-contained
   brief, explicit file ownership, inputs, outputs and dependencies. Do not
   resume an unrelated subagent thread. Parallel work must respect unresolved
   decisions and the checklist's top-to-bottom order.

## Exactly three responsibilities for each axis

| Piece | Required content and responsibility |
| --- | --- |
| Investigation prompt text | Direct instructions about the gene and candidate annotation: which evidence to investigate, what native measurements and qualifications matter, and what distinguishes relevant evidence from a misleading proxy. Supply substantive TASK instructions, separate from terse factual STEERING. |
| Scoring rubric: the scoring sheet/format/template | Formal typed cells for the actual evidence, with defined meanings, units, missing values and relationships. Include the actual assayed subject, conditions, controls and target/homolog correspondence where relevant. This is the format to be populated, not a point schedule or a JSON rule interpreter. |
| Separate grader/reader functions | Populate that sheet from actual findings or data. Use deterministic functions wherever the information can be parsed or calculated. Define any genuinely necessary non-numeric judgment explicitly; do not substitute an LLM judgment for an available measurement or calculation. |

Every field must have an identified input and populating function, or an explicit
unimplemented status. Unknown values remain unknown. A declared field without
a reader is not an implemented axis. Keep the sheet and its implementation out
of the investigation prompt, including library lookup responses; do not dump a
whole axis record into the model context. Host provenance and validation metadata
remain available to the implementation without becoming prompt bookkeeping.

## Measurements and evidence handling

- Use native sequence, structure, context, phylogenetic, expression, assay and
  other applicable measurements. Preserve units, bounds, reported uncertainty,
  conditions and controls. Do not replace existing numbers with invented
  confidence or blanket applicability weights.
- Literature findings and dataset analysis must populate compatible cells in
  the same axis sheet. This does not combine literature and bioinformatics
  episode structures or make one workflow a mandatory stage of the other.
- Preserve what was actually measured and on which subject. Evidence from a
  close homolog must retain the homolog's measurement separately from the
  correspondence that makes it relevant to the target annotation.
- Preserve source/experiment provenance, negative results and qualifications.
  Two representations of the same experiment do not become two independent
  contributions. Do not infer experiment identity merely from equal values.
- Link library options to the retained published cases for inspection. Label
  synthetic test fixtures explicitly; they are not scientific findings or
  evidence that an axis is complete.

## Handoff to W05 and completion evidence

For every retained axis, deliver the reviewed prompt text, formal scoring-sheet
format, and the functions that populate it. Demonstrate actual filled sheets
from both literature findings and dataset inputs for each axis, and meaningful
checks for native values, missing data, source/target correspondence and repeated
representations. Inspect the construction and lookup paths to establish that
only the intended prompt text reaches the investigation.

The populated sheet is W04's concrete handoff to W05. W05 connects it to the
deterministic annotation-credit function and verifies the complete consumer
path. Do not invent or adopt new weights, thresholds or a global formula under
W04, and do not report W05 complete because W04 produced files.

W04 remains unchecked until its required deliverables are implemented and
verified for the retained axes. Draft files, passing descriptor validation,
generic scoring interpreters and subagent completion messages do not establish
this. Report what was actually delivered, what was tested and what remains.

## Previous W04 wording retained for history

The following checklist text preceded this correction. Its draft-validation
statement is not evidence of delivery under the instructions above:

> - [ ] **W04 — Fix the evidence-axis library.** Native measurements, actual
>   bindings, firm criteria and typed outputs; exact source provenance. A101–A104
>   files validate. Remaining entry bodies, assembled index, construction and
>   complete publication verification are not finished. Highest priority.

## Subsequent target-material correction, 2026-10-23

Identify the annotation target from the material actually supplied: sequence,
selected file record or region, or snippets. Internal names may be labels only;
do not require a searchable public gene name or accession. Supply the actual
material or scoped access to it and preserve its boundaries, completeness and
known context. Do not infer a whole sequence from snippets or select an arbitrary
record from a multi-record file. This applies to evidence-axis prompt wording;
it does not change the scoring sheet or reader functions.

The verbatim user correction and revised A105 review text are preserved in
verification/a105_three_parts_review_2026-10-23_001/prompt_insert_002.md. Earlier
review text remains preserved; no production prompt change is claimed.

## Subsequent scoring-sheet correction, 2026-10-23

The user said, verbatim:

> For Your scoring sheet, I'm not sure I can use this to score shit. I mean that really. Basically you took words and tried to turn them into a table, not a scoring sheet. A scoring sheet involves actual scores you dipsit. Source claim is nice for record keeping, but IS NOT SCORING. Validity of source claim or number of citation or number of published papers from lab with similar assays or something else is a measurable entity. This is just record keeping and not at all a scoring sheet. So now it's not the wording, it's the concept you seem to not be getting. A scoring sheet is populated with things that can be used to compile a score. Freehand words are not it.

The original A105 review table was an evidence record, not the requested scoring
sheet. Treat it as rejected for that purpose. Formal types alone do not correct
this failure. A scoring sheet must contain actual numerical score components
that the annotation-credit function can use. For each component specify the
measured inputs, calculation or explicit grading criteria, numerical result,
units/range and its role in evaluating the evidence. A source claim or source
identifier is not itself a score.

Keep source records and conditions as supporting provenance, separate from the
numerical scoring cells. Native assay magnitude alone does not measure the
strength or specificity of evidence for an annotation. Include relevant
measurable experimental validity, controls, precision, independent replication
and specificity where available. Missing inputs leave a component unknown.
Do not manufacture a confidence number from prose or turn every metadata field
into a binary score. The user's citation/laboratory examples illustrate
measurable candidates; they do not authorize publication-reputation weights or
equating citations with independent experiments.

The replacement numerical A105 proposal is preserved in
verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md.
It is a proposal with new synthetic inputs and checked arithmetic, not completed
reader implementation, adopted scoring policy or full axis/credit wiring.

## Subsequent discovery-task correction, 2026-10-23

Do not require an initial candidate annotation. The starting assignment may
contain only a sequence, selected file contents or snippets. Investigation
gathers and evaluates evidence about what the target does; possible functions
can emerge and later be compared or revised. Earlier wording about investigating
the gene "and candidate annotation" must not become a candidate prerequisite or
make hypothesis testing the default task. A105 includes experimental evidence
on relevant homologs while preserving the actual assayed subject and the limits
of inference to the supplied target.

The verbatim user correction and revised A105 prompt are preserved in
verification/a105_three_parts_review_2026-10-23_001/prompt_insert_003.md.

The user subsequently said about point 2:

> On 2, that is spiritually much closer to where we need to be

This accepts the numerical scoring-component direction as closer to the intended
design. It does not settle the particular component list, weights, aggregation
or production implementation. Preserve the numerical example as a working
proposal for further feedback.

## Subsequent scoring scope and reader dependency, 2026-10-23

The user said, verbatim:

> 3 is not quite right, but I think it will make more sense to you after you settle down on 2 with an actual scoring sheet with scores in. The point of 3 is to then actually populate that scoring sheet. so 3 is very targetted to what you produce in 2.

> you would need to compile these into some kind of "experimental reliablity" score but they are individual components. That said they are too specific to one experiment

> So you need to think out your example for part 2 more carefully

> there can be many different types of experiments to validate function, right?

> and there are other aspects of scoring as well. experimental relatedness to claim, experimental validity (from the type of experiment), there are even experimental weaknesses which biologists typically use other experiments to complement, strength of signal, consistency, uncertainty, relation to system we are annotating, these all need to be thought out.

Part 2 must define the actual numerical scoring components and how they compile
before part 3's readers/graders are designed to populate those exact cells. Do
not design independent generic readers and retrofit their outputs as the sheet.
The latest numerical toy table is a directionally useful collection of assay
components, not the completed scoring sheet or an accepted common component list.

Work through different actual experimental designs before defining reusable
scoring components. Distinguish protocol-specific measurements from common
scoring meanings. Account for all aspects in the user's final quoted message;
do not collapse them into one generic quality average. Derive and show concrete
numerical rubric anchors and compilation behavior, with their limits, for the
user's feedback before treating part 2 as settled.

Score a measured outcome and its bearing on a particular functional inference,
not the source paper as a whole. A well-established binding result does not make
an activation claim equally reliable. A claim here can emerge from investigation;
this does not reinstate an initial-candidate requirement in part 1.

Trace named weaknesses to the additional experiment that addresses each one.
Complementary readouts are not automatically independent replication. Results
on different endpoints are not automatically inconsistent repeats. Keep
measurement uncertainty, missing information and system-transfer limitations
visible. These are scoring design responsibilities, not extra episode types,
mandatory experiment sequences, runtime gates or adopted credit weights.

## Subsequent case-based research direction, 2026-10-23

The user said, verbatim:

> Perhaps, like your 142 case reports, you ought to use a similar approach of going through literature and assays and learning what the different aspects are that are worthwhile to score and report on

The scoped research plan is
research/experimental_scoring_review_2026-10-23/RESEARCH_SCOPE.md. It preserves
the original 142-group/149-record corpus, assigns every group exactly once to
three fresh parallel research workloads, and distinguishes corpus reanalysis
from new primary Methods/Results reading. Common outputs trace measured results,
supported inferences, weaknesses and complementary experiments to sources and
candidate numerical scoring components. New follow-up lanes are maintained in
that research directory's EMERGING_LANES.md, not silently adopted as axes.

The research must lead to worked numerical sheet and compilation proposals for
conversation feedback. Collection counts or named dimensions do not complete
part 2; part 3 and production scoring changes remain held during this research.

## Subsequent evidence-transfer clarification, 2026-10-23

The user said, verbatim:

> what is the proposed generic transfer weight. what is native homology? these are words i'm not familiar with. if you mean sequence homology, i did not mean to restrict transfer of evidence to only the basis of sequence homology. There are other ways of knowing two things are the same thing.

Evidence transfer is not restricted to sequence homology. Establish which
relationship makes the actual experimental finding informative about the
supplied target. Identity of the assayed molecule and target, evolutionary
relationships, structural comparisons, genomic context, relevant molecular
features and experimental demonstrations of functional interchangeability are
possible sources of information; they are not interchangeable conclusions or
a mandatory list. A shared function need not mean two molecules are identical.

Use available measurements where they answer that relationship question; make
any additional judgment explicit. The previous instruction against replacing
measurements with blanket applicability weights does not prohibit a scored
assessment of transfer. Neither a sequence-only restriction nor removal of the
transfer component was instructed. The five-level T scale in the research
draft is an unadopted proposal whose grade spacing and multiplicative role still
need review. "Native homology" was the assistant's unclear wording: it meant
original comparison measurements/scores, not a type of homology. Use the actual
measurement's name instead. Preserve the drafts as research history, with this
clarification governing their interpretation.
