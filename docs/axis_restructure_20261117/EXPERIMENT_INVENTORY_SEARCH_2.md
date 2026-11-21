# Experiment-type inventory search 2 (read-only search of Codex transcripts)

Sessions (all under /home/chia/.codex/sessions/2026/10/):
- 25/rollout-2026-10-25T19-22-06-01a17595-...jsonl (398 MB). Referred to below as S1.
- 29/rollout-2026-10-29T17-25-26-01a189c4-...jsonl (1.3 MB, guides subagent). S2.
- 30/rollout-2026-10-30T17-36-06-01a18ef4-...jsonl (259 MB, ends 2026-11-10). S3.
Line numbers are line numbers of those files. Dates are UTC from the line timestamps.

## 1. Headline: the "real list" does not exist as one agreed document

No file or message was found that holds the roster of about 150 papers' worth of experiment types
(SPR, BLI, ITC, FP, FRET, MST, ELISA, EMSA, pull-down, DSF, CETSA, BRET, Y2H, PLA, proximity labeling),
each with its own grader. Searches for 'surface plasmon', 'isothermal titration', 'thermal shift',
'EMSA', 'interaction assay' in owner or Codex messages returned only paper text pasted in by
literature reads (S1 lines 4802, 6354, 8745) or a guides-search result (S2 line 202). The owner's
phrase 'List by types' exists but is a complaint (S1 line 85504), not a list.

The only "agreed" type roster that was recovered is a SIX-family list plus two supporting families,
produced by Codex and not confirmed as final by the owner (see 3). On 2026-10-29 21:53 Codex itself
said it could not recover the earlier agreed type list and asked the owner to paste it (S1 line 84421-84422).
So the list the owner remembers (a binding-technique roster with SPR, ITC, EMSA etc.) is NOT in
S1 before 2026-10-29 22:06, nor in S2, nor in the S3 owner messages searched. It may be in another
session (before 2026-10-26 or a different thread) or was never written down as a list.

## 2. Owner statements (owner said), latest word marked

All excerpts are owner messages. Quotes are verbatim, cut.

(a) Types, not cases. Owner said, 2026-10-29 21:42 (S1 line 84149): "List out the categories of
experiments that we listed out before together to work on. THOSE ARE THE TYPES. YOU ONLY HAVE THAT
MANY SUBSCORING SHEETS PERIOD UNTIL INSTRUCTED OTHERWISE ... how many parsers (readers) for
populating the fixed number of scoring sheets."
Earlier, 2026-10-26/27 01:09 (S1 line 33322): "grader families are not the same as graders. For
each family, there might be multiple assays. Even overlapping assays have value as extra
verification since each assay has an error rate."
Owner said 2026-10-29 21:5x (S1 line 83900): "EXPERIMENTS ARE CATEGORIZED BY TYPE. YOU DON'T NEED A
UNIQUE SCORING SHEET FOR EVERY SEPARATE PAPER."

(b) What a subscoring sheet is. Owner said, 2026-10-29 (S1 line 84441): "that is a subscoring sheet
because it stores things that will be used to score a sheet hierarchically above it later".
Owner said 22:09 (line 84925): "Each row in your table is a subscoring sheet - confirm". Owner said
22:11 (lines 84973-85001): there are not 36 rows; "every count within the row reports to the same
subscoring sheet" (the 36 implementation sheets were being counted wrongly; rows = types).
Result: the inventory (verification/a105_sheet_reader_inventory_315/REPORT.md) maps 36 sheets and
55 readers onto the eight types; the owner's rule is one subscoring sheet per type, not per grader.

(c) Why assays share a sheet: owner said 22:23 (S1 line 85104): "biochemical assays all involve
checking certain experimental design marks to see if they are valid. What is the sensitivity? What
were the kinetic parameters used? Did you have to heat things ... in vitro / in vivo? Were the chemical
conditions mimicking the real world ... If a messy experiment, did you get expected signal? Would that
chemistry have happened spontaneously anyway - was there a control?" This is the owner's own list of
shared per-type criteria: sensitivity, kinetic parameters, conditions (temperature, in vitro/vivo,
realism of chemistry), expected signal in messy samples, spontaneous-reaction control. It is stated
for biochemical assays only. No equivalent was found for SPR/ITC/EMSA/ELISA/pull-down/thermal shift.

(d) Grouping graders. Owner said 22:51 (line 85489): "group the ones that do not need separate
graders ... parent-depletion is very very narrow. Are you sure that's not a broader class of assays?
... You know you aren't supposed to be working out every single experiment separately". Owner said
22:51 (line 85503): the "experiments this addresses" column "is more like a list of examples then the
types of experiments addressed, which is what it should be. It should be a list by types".
Owner said 22:55 (line 85519): choose readers/graders "NOT SUPER SPECIFIC CASES ... These are assays.
Assay generally refers to a type of protocol that can be reapplied to anything."
Owner asked 22:25 (line 85116) for a guides subagent (S2 is that guides search) and a subagent that
reads all 14 biochemical graders (verification/biochemical_fourteen_graders_319 and
biochemical_assay_guides_318).

(e) Hierarchy. Owner said 22:57 (line 85598): "you need to have the ability to convert all 4 of
those lists of considerations and write something that will fill the A105 experimental evidence
scoring sheet. The schema is: A105 experimental evidence subscore --> subscoring grader -->
subscoring reader." Reading by owner: reader sits under grader, grader under sheet. (The "4 lists"
are Codex's guide output; their content was not confirmed in an owner message and is not recorded here.)
Owner said 23:35 (line 86444): one A105 experimental subscoring sheet per experiment analysed, so
the parent can store them all and build a holistic additive score.
Owner said 2026-10-26/27 (S1 line 33300): "approximately zero tools except reader tools like graph
readers ... in A105. There are no data analyses to run, just reports to extract information from".

(f) Variance, detection limit. Owner said 23:40-23:42 (lines 86571-86616): standard deviation and
variance "were recorded in the subscoring sheets (graders)"; "below detection should be recorded and
it's up to the grader --> A105 experiment subscore function to translate that to something useful".
When Codex described a gap, owner said it is "a bug with the common scoring sheet" (line 86616) and
sent a subagent to fix it (line 86641).

(g) Combining several experiments (owner confirmed as "good enough"), 2026-10-29 23:43-23:59:
- "Reliability is additive. Validity treat as additive." (line 86884)
- "Relevance should be a maximum of all relevances." (line 86884)
- "attribution should also be maximum" (line 86913)
- "and overall is sum." (line 86961)
- caveat: additivity works best if experiments are orthogonal or have orthogonal weaknesses; "for now,
  this is good enough" (line 86884).
These are the only owner-stated combination rules found. The words 'converter' and 'merger' (as
owner terms) were NOT found in S1 or S3 owner messages (only 'unit converter' in a tool output, S3 line 67845).
So "converter/merger" as two placements is not documented in these sessions.

(h) Grader and scoring sheet vocabulary, S3 (latest, overrides S1 where they differ):
- 2026-11-05 05:08 (S3 line 41786): "adapted the grading criteria means you either did 1 grader or that
  you did the main evidence scoring sheet (which we do not use the word grader or grading sheet for)".
  Owner said 04:37 (line 40996): "grading criteria means subscoring sheets need to change, and that's it".
- 2026-11-05 05:48 (line 42810): a "simple grader sheet ... goes up to some scoring principle for the axis. Good. Build it now."
- 2026-11-06 02:38-02:39 (lines 49541, 49567): "in that flow grader is not optional"; "why does it have an
  option to not select grader?" So selecting a grader is mandatory for experimental evidence.
- 2026-11-07 04:55 (line 80015): "if you need to choose a grader, then say choose a grader from this list
  and the list is a table with names and brief descriptions, yes?" (selection menu = name + short description).
- 2026-11-07 04:44 (line 79737): "why are the grader sheets not automatically updating all the scoring
  sheets?"; 17:12 (line 82485): "yes, make this deterministic from the grader or scoring sheets".
- 2026-11-07 05:02 (line 80241): objective reporting, no LLM-written reinterpretation: "report what was
  done and how much credit was earned ... NOT VIBE ... Don't make up something that requires numbers and
  IDs and requires the reader (the LLM) to do the replacements".
When the grader judges (as information arrives vs at the top): not settled by the owner in the text found;
the owner's "grader sheets update the scoring sheets automatically" (S3 line 79737/82485) implies at
each experiment as it is recorded, but this is an inference, not a statement.
What a grader produces: owner said it records the numbers (variance, SD, below-detection flags) in the
subscoring sheet (S1 lines 86571, 86595); the criterion-by-criterion status vs a single number was not
discussed by the owner in found text. Not settled.

## 3. The eight types (Codex's roster, owner reaction)

Source: verification/a105_sheet_reader_inventory_315/PRIOR_CONVERSATION_ROSTER.md (quotes S1 line 33284,
2026-10-27 01:07 UTC, Codex's answer to "how many experiment-types do you have graders for?").
Verbatim:
 Executable graders in 6 assay families:
 1. Biochemical activity/rate assays.
 2. Enzyme kinetics and substrate specificity.
 3. Ligand binding and binding discrimination.
 4. Transport/substrate-response comparisons.
 5. NADH optical-rate assays.
 6. Partner-removal/addback experiments.
 Also 2 supporting measurement families: (7) reported protein-signal/band ratios; (8) protein amount/preparation composition.
Owner reaction (S1 line 33322): "grader families are not the same as graders. For each family, there
might be multiple assays..." This corrects that the families are the sheets and each family has several
assay graders; the owner did not approve this list as the final roster. Codex later said it could not
confirm the roster (S1 line 84421). The inventory REPORT.md (315) nonetheless uses these eight and
states: 36 numerical subscoring sheets, 55 readers (39 direct), distribution biochemical 13/14,
kinetics 4/4, binding 4/4, transport 3/3, NADH 1/1, partner 1/1, band ratios 2/3, amount 2/2, shared 6/7.
It says explicitly these counts do not authorize 36 experiment types. Whether the eight changed: no
later owner message was found that changes the eight; the 2026-10-29 sanity request (S1 line 84149)
re-asserts a fixed number of types without naming it.

## 4. Per-technique criteria (SPR, ITC, EMSA, ELISA, pull-down, thermal shift, kinetics)

Not found as an owner or agreed statement. Only the biochemical shared-consideration questions in 2(c)
(owner's own words) and the 14-grader/guides audits (verification/biochemical_assay_guides_318,
biochemical_fourteen_graders_319), which are Codex output and which a verification audit found list reader
entrypoints, not graders. The code carries per-type sheets (SHEETS.tsv in the 315 folder) with
quantities, replicates and precision cells, but no owner-approved technique roster with controls/noise
/replicates/certainty per technique.

## 5. Reader definition

Owner said (S1 line 33300): reader tools (graph readers etc.) extract information from reports;
(line 84149) "parsers (readers) for populating the fixed number of scoring sheets"; hierarchy sheet --> grader --> reader (line 85598).
No owner statement defining "display types" was found. Agreed readers: none enumerated by the owner;
the 55 reader functions are in READERS.tsv (verification 315).

## 6. Per-experiment hand-building

Owner said the opposite of hand-built-per-case: do not write a grader per paper or per chemical
(S1 lines 83900, 85489, 85519). The owner's S1 instruction text (S1 lines 90085, 92149 inside a task
prompt) says "Group experiments by reusable protocol considerations; do not create a grader for each
paper or chemical example." One owner remark about "by hand" in S3 (line 29015) concerns A108 completion,
not graders.

## 7. Contradictions and latest word

- Codex 2026-10-27: "6 assay families" + 2 supporting (8). Codex 2026-10-29: could not verify; asked
  owner to supply the list. Owner never supplied one in found text. Latest owner word: types are fixed
  and sheets equal types; do not add graders per case (2026-10-29 21:42-22:55).
- Owner 2026-10-29: "main scoring sheet" versus "subscoring sheet" vocabulary (S3 2026-11-05 line 41786)
  consistent: graders/subscoring sheets feed the main evidence scoring sheet; do not call the main sheet a grader sheet.
- 2026-10-29 owner combining rules (additive reliability/validity, max relevance and attribution, overall = sum)
  are the only combination rules; later S3 text about combining was not searched exhaustively.
- Selection of grader: optional in an earlier Codex design; owner 2026-11-06 said it is not optional (latest).

## 8. Git search of /home/chia/repos/gene_annotation_episode

`git log --all -- docs/AMENDMENTS` returned only repository checkpoints; the file
docs/AMENDMENTS/A105_REPORT_READERS_AND_ASSAY_GRADERS_2026-10-26_001.md does not exist in commits
1019717c3, 5cafe5c43 or 07d8702b9 (the only commits found by pickaxe for its name). It was not located.
A long `git log --all -S` run was started in the background and may still be running (read-only).

## 9. What is still missing

1. The owner's technique list (SPR/BLI/ITC/FP/FRET/MST/ELISA/EMSA/pull-down/DSF/CETSA/BRET/Y2H/split
   reporters/PLA/proximity labeling) with per-technique criteria. Not in S1 before 22:06 on 10-29, not in
   S2, not in S3 owner messages. S1 is 398 MB and Codex's messages after 22:06 on 10-29 to 10-30 18:13 were
   only partly examined (lines 87328-90092 owner "goal" request at 87331: "generate a better set of goals
   and goal checkpoints" - the printed goal there may contain the list; worth reading next).
2. The 4 lists of considerations from the guides search (answer to S1 line 85117, ordinal ~85118-85490)
   and the 14-grader subagent report; owner approval of them was not tied to a message.
3. The converter/merger terms.
4. The A105 amendment file.
