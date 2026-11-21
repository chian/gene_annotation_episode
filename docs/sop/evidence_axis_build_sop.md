# SOP: building an evidence axis the way A101 was built

For an agent who will build one of the other evidence axes, A102 to A110, in the paradigm A101 was built in first.
Written 2026-11-21 from the code and the design notes, not from memory. Where a rule is the owner's, the owner's words are
quoted exactly as the notes record them, with the note that holds them. Where a quote comes only from the order that
commissioned this SOP and is in no design note yet, it says so.

## 0. Read this first

Names used below (the same as in the A101 notes):

- HEAD = `gene_annotation_episode/episodic_workflow/root/a101/sequence_homology_evidence` (the A101 head episode).
- LIB = `gene_annotation_episode/episodic_workflow/episode_support` (the shared library).
- The system packages, at the top of the repository beside `gene_annotation_episode/`: `method_loop` (the episode
  contract is `method_loop/episode_type.py`), `episode_runtime` (the runner and its services) and `yield_control` (the
  stopping controllers). You do not edit them to fit your axis. If your axis needs a change there, stop and ask the owner.
- An axis lives at `gene_annotation_episode/episodic_workflow/root/a1xx/<axis>_evidence/` (A102 is
  `a102/structural_homology_evidence`, and so on). That folder holds only the episode bindings. Everything shared lives in LIB.

Read before you write anything: `AGENTS.md` in full (private episode bindings, the failure rules, controlled messaging,
removing unwanted code, local execution policy), then `docs/plan/designs/a101_tree.md` (the shape of the A101 tree and what
each piece is), then the notes named in each step below.

Rules that cut across every step:

- The owner's rule for a replaced rule: delete it. "the averaging rule can be deleted. that obviously will not work" (the
  owner, quoted in the order that commissioned this SOP). A document or a comment never says "superseded"; it is
  rewritten to say what the code does now. Run observations are history and stay; predictions and arithmetic that only made
  sense under a deleted rule go.
- Controlled messaging overrides everything: what passes between episodes is numbers, booleans, values of a fixed
  vocabulary and record references. Never free text, never a paragraph (`AGENTS.md`).
- A parent knows how to call its child. A wrong commission fails with its error: no fallback, no autofix, no cleanup
  (`AGENTS.md`, owner's rules of 2026-11-19).

---

## Step 1. The episode contract

**What to build.** One episode folder per node of your tree. Each folder holds exactly: `goal.py`, `task.py`, `credit.py`,
`yield_estimator.py`, `episode.py` (ties it together), `__init__.py`, and a `messages/` folder with `read_from_parent.py`,
`internal_summary.py`, `final_to_parent.py` and, only when the episode has children, `msg_to_child.py` and
`read_from_child.py`. Child episode folders sit inside their parent's folder. No `tests/` folder.

**The rule.** Every episode is `class X(EpisodeBinding)` and inherits from nothing else. It never inherits from, subclasses or
shares a behaviour module with another episode: copies of binding files are intended, shared code is library functions that the
episode calls explicitly (`AGENTS.md`, "Private episode bindings"). `episode.py` assigns each member from its file; the class
definition raises `TypeError` for a member in the wrong file or with the wrong arguments. What each file must supply
(`method_loop/episode_type.py`, `SUPPLIED_BY_FILE` and `SIGNATURES`):

| File | Member | Arguments |
|---|---|---|
| `goal.py` | `binding_path`, `goal`, `unit`, `result` | text |
| `task.py` | `child_slots` | `{slot: child binding path}` |
| `task.py` | `tools` | `{name: tool(arguments, ctx)}` |
| `task.py` | `services` | names of the services the episode reads |
| `task.py` | `decide` | `(summary, feedback, ctx)`: returns the model request |
| `task.py` | `offered_actions` | `(summary, ctx)`: the action types this decision offers (a tool name, a child slot, or `reason`) |
| `task.py` | `action` | `(response, summary, records, ctx)`: returns a `ToolCall` or a `ChildCall`, or raises `Rejected(feedback)` |
| `credit.py` | `credit` | `(summary, records)`: a finite number |
| `credit.py` | `ceiling` | `(summary, records, action_type, arguments, ctx)`: `UNBOUNDED` or a finite number >= 0 |
| `credit.py` | `best_arguments` (optional) | `(summary, records, action_type, ctx)`: the arguments that reach the ceiling asked with `arguments` None, or None |
| `credit.py` | `outcome_pending` (optional; required with a forecast controller and child slots) | `(summary, records, position)`: True when that unit's outcome is pending (a child returned parked), else False |
| `yield_estimator.py` | `yield_controller` | `(initial_credit, settings, parent_input)` |
| `messages/read_from_parent.py` | `assignment_form`, `read_from_parent` | `(assignment, message)`: the parent input |
| `messages/msg_to_child.py` | `msg_to_child` | `(slot, arguments, summary)`: a `ChildMessage` |
| `messages/read_from_child.py` | `read_from_child` | `(slot, result, summary, records)` |
| `messages/internal_summary.py` | `internal_summary` | `(view)` |
| `messages/final_to_parent.py` | `return_form`, `final_to_parent` | `return_form` must require `credit` and `finding`; `(summary, completion, selection)` |

The loop (the docstring of `method_loop/episode_type.py` is the full statement): `decide` asks the model; `action` turns the
answer into one `ToolCall` or one `ChildCall`, or rejects it before any unit exists; the unit runs; the credit is recomputed
from the summary; the episode's yield controller alone decides whether the episode stops. The task never ends its episode.
Library functions never write to the Store directly: they go through the custody store the system hands the episode.
`yield_estimator.py` reads what `read_from_parent` produced, never the raw assignment.

`ceiling` and `offered_actions` (the owner's words): "ceiling is a function that has to be how much max credit from this
current state" (`a101_conserved_sites.md`). After every `decide` the system asks `ceiling(summary, records, action_type,
None, ctx)` for each offered action type, the most the credit can rise if that action is the next unit; after `action` it
asks again with the chosen action's arguments; after the unit it compares the credit's rise with that ceiling and raises
`episode_ceiling_exceeded:...` when the rise is above it. There is no default: an episode answers for every action it offers.
`UNBOUNDED` is returned only for an action whose gain truly has no limit, and with a reason written beside it. The owner:
"UNBOUNDED filled in everywhere is bad; UNBOUNDED where truly unbounded is right" (`forecast_yield_controller.md`). A101 has
one `UNBOUNDED`: `execute_selected_tool`, because a selected registry tool can import a report of any size
(`HEAD/credit.py`, `ceiling`). Every other A101 action has a derived finite ceiling (Step 8).

**Where A101 does it.** `HEAD/episode.py`, `HEAD/goal.py`, `HEAD/task.py` (`CHILD_SLOTS`, `TOOLS`, `decide`, `offered_actions`,
`action`), `HEAD/credit.py`, `HEAD/yield_estimator.py`, `HEAD/messages/*`. A child with no children of its own, for the
smallest example: `HEAD/all_vs_all/`.

**How to check.** Import the episode through a real run (Step 11): the runner refuses a binding with a wrong member. Confirm
the journal (`report`) shows, per unit, the offered ceilings, the chosen ceiling and the rise. A rise above a ceiling is a bug
in `ceiling`, not in the run.

---

## Step 2. Tool or child episode

**What to build.** For each analysis your axis needs, decide whether it is a tool of an episode or a child episode.

**The rule.** The owner's rulings, as the notes record them (`a101_tree.md`):

- "There is no such thing as a code-decided episode. In every episode the model is the router: it chooses one defined
  action per decision, with controlled values, and code carries it out."
- "Children exist because they iterate, launch long jobs that detach (tools are tied to a turn), and let the communication of
  each be controlled separately."
- "Anything nested in the tree is a child episode. A leaf is a tool or a child episode."
- Grading is automatic: it is never an episode and never a choice the model makes. A tool that fetches a result grades it in
  the same unit.
- The owner, in the order that commissioned this SOP (not yet in a design note): "if we don't need iteration, then do it" as a
  tool. A job that ends within the turn has nothing to iterate, detach or monitor, so it is a tool of the episode that wants it
  (`pairwise_blast` and `hmmer_profile_scan` are tools of the A101 head). A job that runs on an outside service and takes
  minutes or hours is a child episode (`bvbrc_blast`, `bvbrc_msa`, `bvbrc_metacats`). An analysis that has several steps the
  model must choose among, with its own communication, is a child episode (`all_vs_all`, whose steps are tools of the child).
- Order of work (the owner, plan decision D27): one pattern in one branch first, then the repeats in parallel. Start local.
  No cluster work first.

**Where A101 does it.** The current tree, with each piece marked, is `docs/plan/designs/a101_tree.md`. Tools of the head:
`HEAD/task.py` (`PAIRWISE_TOOL`, `PROFILE_TOOL`, `TOOLS`). Children: `HEAD/task.py` `CHILD_SLOTS`.

**How to check.** For each node, say in one line which of the owner's three reasons makes it a child. If none applies, it is a
tool.

---

## Step 3. One-shot tools: the model fills out a JSON, code checks it, code runs it

**What to build.** For every tool, three things: the model's request schema (each field from a fixed set or a range), ONE
deterministic check function, and ONE library function that runs the job and grades it.

**The rule.** The owner: "have the head node fill out a json and then that json is deterministically run through a function that
checks it and either (returns things to fix) or runs the job" (`all_vs_all_episode.md`). So:

- The check runs in `action` before anything runs. If it finds problems, `action` raises `Rejected` with feedback listing each
  problem as a field and a code and what to choose from. No unit is created and nothing is recorded as an action.
- A request that passed the check must simply work. A failure after a passed check is a fault of the environment: reported once
  as `failed`, `retryable` false. The running function does not check inputs again.
- A tool offers only calls that can succeed. A tool whose offer allowed a call that cannot succeed was repeated 21 times in the
  first A101 real run (`a101_tree.md`, run `a101-patternA-1`). A repeat of work already held is refused by the check.
- Always give the model a valid answer so it is never stuck in refusals (`hold` in `all_vs_all`).
- A unit that runs is one library function: run, fetch the report, grade, keep the sheet through custody. The model never
  chooses "grade".

**Where A101 does it.** `pairwise_blast`: request in `HEAD/task.py` `pairwise_options`, check `check_pairwise_request` and run
`pairwise_blast_comparison` in `LIB/tools/similarity_search/sequence_homology_evidence/pairwise_blast_comparison.py`.
`hmmer_profile_scan`: `LIB/tools/similarity_search/sequence_homology_evidence/hmmer_profile_scan.py` (`check_profile_scan_request`,
`hmmer_profile_scan`). The three tools of the all-vs-all child: `HEAD/all_vs_all/task.py` with checks in
`LIB/tools/.../all_vs_all_run.py`.

**How to check.** Real run (Step 11): the model makes a correct request and the unit runs on the first call; then a later visit
in which a repeat is requested and rejected with its fix list (A101 run 5, `a101_tree.md`). A direct call of the check function
on made-up bad requests is allowed as a direct check but is not a real run and proves nothing about the model.

---

## Step 4. The job child: anything that runs on an outside service

**What to build.** One child per outside application, all built on one shared module. The shape is the owner's: "one child with 6
actions. make estimate/reason, [must be gated on having made an estimate] launch job, fix mistakes/reason, monitor/update
estimate, extract results" (`bvbrc_blast_episode.md`). The built actions are five: `estimate`, `launch`, `fix`, `monitor`,
`extract`. States: `no_estimate`, `estimated`, `launched`, `finished`, `extracted`, `failed`.

**The rule.**

- Estimate (gated): `launch` is refused until an estimate is held (`estimate_required`). Every job's estimate comes from the
  ledger: the basis and the seconds must equal `ledger_estimate` (`bvbrc_job_child`), which the estimate decision shows in
  `learned_durations`: `learned_from_earlier_jobs` with the size line's seconds for this job, else the median of the measured jobs;
  `no_earlier_measurement` with the fixed first figure (`FIRST_JOB_SECONDS`) when none is measured. Any other figure is refused
  with its field and `choose_from` the figure.
- Launch, then `fix` only after a failure, with a request that differs from the failed one in the fixed field. Monitor: a wait
  inside a stated range, one status request, a revised remaining time. Extract: fetch and grade in one unit.
- Until launched or extracted: the commission names `until`. With `launched` the child estimates, launches and returns at once
  (it is parked). With `extracted` it follows the job to its end; it is also how a parked job is resumed (same commission, the
  held handoff passed back, nothing resubmitted). The owner's words: "figure out how to "release" (dangerous word since it can be
  used multiple ways---find a better one) this child to run in background while other pieces of the episodic workflow can do other
  work (i.e., bounce a waiting notice/info back up to parent with about how long we expect to wait so parent can choose what to do
  next. it could just wait, it could send off another tool, it could go all the way back up to root with the same info)"
  (`bvbrc_blast_episode.md`). The word chosen is "park".
- The wait notice a parked child returns: `parked`, `seconds_since_launch`, `estimated_seconds`, `expected_remaining_seconds`
  (the estimate minus the seconds since launch, not below zero, or a later revised figure). The parent's model is shown the
  seconds since launch and the seconds still expected as of each of its own decisions. Facts only: never a deadline.
- One place in the library for the shared machinery: `bvbrc_job_child.py`. A child makes ONE `JobApplication(...)` and its five
  files call the module's functions. Do not copy the machinery into a child; write only what is specific to the application
  (`prepare`, `extract`, `describe_identity`, `field_problems`).
- The estimate ledger: `resources/estimate_ledger.sqlite3` (outside version control, outlasts every run). A launch writes ONE
  row for the job, with the job's facts (service, program, database or application, size). The owner's words: "create a global
  ledger that the estimator has access to so it can learn what to expect time-wise (that means across all runs ever and it needs
  some run info on size of job, what database was queried, and general time and so on) that can be turned into soem very short
  trend data (maybe even a numerical function at some point if we have enough initial data points) thereby making this more
  accurate as time goes on" (`a101_tree.md`). The duration written is the service's OWN task record (completion minus
  submission), with the seconds to the first status that showed the end kept beside it as `observed_seconds`. The estimate
  action is shown the kind's short trend (`LIB/jobs/duration_trend.py`).
- The child's own credit is bounded and counts each unit once: an estimate held, the job launched (once however many launches a
  fix needed), the job known ended, the graded result. Its yield controller is `CompletionYieldController` to the sum of the
  units the commission can obtain (`bounded_credit`, `completion_controller`).
- The job route: `LIB/jobs/bvbrc_job_route.py` has the table `APPLICATIONS` (`Homology`, `MSA`, `MetaCATS`). A new application on
  the same service is one more entry there plus its retained definition under `LIB/forms/application_service_specs/original/`,
  checked live before anything is built on it (Step 11).
- Credentials: never print or write a credential. The BV-BRC login is read from the environment variable the launcher command
  sets from the owner's token file, only inside that command (Step 11).

**Where A101 does it.** Shared module `LIB/tools/similarity_search/sequence_homology_evidence/bvbrc_job_child.py` (its top
docstring is the binding recipe). Children: `HEAD/bvbrc_blast`, `HEAD/bvbrc_msa`, `HEAD/bvbrc_metacats`, each bound to it
through `LIB/tools/.../bvbrc_blast_search.py`, `bvbrc_msa_alignment.py`, `bvbrc_metacats_search.py`. Notes: `bvbrc_blast_episode.md`
(the pattern and the ledger and parking runs), `bvbrc_msa_episode.md`, `bvbrc_metacats_episode.md`.

**How to check.** Real runs, in this order: one loop with `until extracted`; then a run that parks (`until launched`) and a
later commission that resumes it with `until extracted` (one job folder at the service, one ledger row, resolved). Read the
ledger row: the duration must be near the service's own task time, not the time of the status request that noticed the end.
Check the refusals by direct calls (labelled as such): launch without an estimate, a repeat commission, extract before finished.

---

## Step 5. Custody and returns

**What to build.** For every child: what it returns, and for every record it returns, everything that record names.

**The rule.** The owner: "head cannot read child directly. child has to offer it up and head takes what it takes."
(`a101_child_returns.md`). And, from the order that commissioned this SOP (not yet in a design note): "either the child intends
the head to use the file or not". The consequence, in the notes' words: what a child returns, it returns for the head to use, and
everything the returned records name is also returned (or already held by the head). Anything private stays inside the child and
is never named in what it returns. There is no sealed field.

- Holding is exact. A record is held only if it was passed in, returned, or produced by the unit. Holding a row does not hold the
  records the row names (`episode_runtime/store_scope.py`, `work_tables.py`).
- A head reads a job only from job ledger rows (their `detail` and `estimates`) and from records the child returned, never from
  an artifact a row or returned record only names. Anything the head needs about a job goes into the handoff row's `estimates` at
  launch (the MSA job `identity`).
- Every child's returned record lists are closed under naming: `LIB/jobs/job_records.returned_with_names(reader, refs)` returns
  the records the child chooses to return with everything they name, recursively. Each child's `internal_summary` builds its
  returned lists through it. The child's `final_to_parent` receives only the summary, so the closing happens where the records
  are read.
- Return a job's rows only when the head reads them: every file a returned row names comes with it. The BV-BRC children return
  their handoff, check and closure rows (the head reads a job's state from them and passes them back to resume a parked job);
  `all_vs_all` closes its jobs inside its units and returns only its labelled products and its graded clustering. The goal is
  that every result the head holds is a labelled data product; what A101's head still holds unlabelled, and why, is in
  `a101_child_returns.md`.
- The parent selects optional return fields in `msg_to_child`; a child declares every field it can return; credit and finding are
  always returned.

**The custody crashes A101 hit, and why** (`bvbrc_msa_episode.md`, `a101_child_returns.md`, `a101_child_returns_audit.md`):

1. The head's summary read an artifact named by a returned reference record (`sequence_ref`) that the head did not hold:
   `CustodyError record_not_held`. Fix: the reference records carry `sequence_ref` null.
2. The head read a job's identity by opening the job's `plan.json`, named by the handoff row's `input_refs`; the head held the row
   but not the artifact. Same error. Fix: the identity is kept in the row's `estimates` and read from there.
3. Two held sequence records had the same artifact (a hit with the target's own sequence), which broke a one-to-one reading
   (`ValueError`). Fix: match the query among `input_` records only.
4. A MetaCATS commission would pass the alignment row but not the alignment artifact the child reads. Found by the audit before
   a run reached it. Rule: whatever a later child must read is returned by the earlier one.
5. Not custody but found in the same place: text hashed where bytes are required in the MSA launch (`feature_group_bytes`).

**Where A101 does it.** `HEAD/messages/msg_to_child.py` (`_custody`, `REQUIRED_RETURN`), `HEAD/messages/read_from_child.py`,
each child's `messages/internal_summary.py`, `LIB/jobs/job_records.py`.

**How to check.** A real run in which the head summarises after every child returns with no `CustodyError`. Count check: every
record each returned list names is held by the head (equal count, none missing). Run the audit of `a101_child_returns_audit.md`
for your own child: list each head-side read that opens something by a reference taken from a field, and show the head holds it.

---

## Step 6. Grading, subscoring sheets, the scoring sheet, data products

**What to build.** For every tool or child result: a deterministic grader that fills a subscoring sheet, and a reading that turns
the sheet into measurements of candidate annotations.

**The rule.** The owner: "the graders should additively add to the subscoring sheets and then the subscoring sheets additively
add to the score" (`a101_child_returns.md`, `a101_differential_credit.md`). And the owner's older rule (plan decision D4): every
tool needs a deterministic grader; the grader fills slots of the tool's sheet from what the tool reported, and the sheet's
scorer computes from the filled slots. The same analysis uses the same sheet with a different parser per format or source (D5).

- One test is one graded source. A test is named `<kind>@<source reference>`, so two jobs of one method on different inputs are
  two tests and are never pooled as replicates. A candidate's value in a test is the mean of its replicates inside that test
  (for example the hits of one search that share a product).
- A subscoring sheet is a kind of test (the part of the name before `@`). A candidate's value on a sheet is the SUM of its values
  over the tests of that kind. A candidate's score is the SUM of its sheet values. The scoring sheet weighs the sheets into the
  score with stated weights, so each sheet's typical strong result counts about the same (`differential_credit.SHEET_WEIGHT`,
  one over the typical strong value of each sheet's family; the values are derived from stored real runs of one target and are
  to be re-derived as other targets accumulate). The owner's sentence for the additive rule is the one quoted above; "with stated
  weights" is how the order that commissioned this SOP puts it and is not yet quoted in a design note.
- Putting a measurement on the common scale. The multiple-sequence-alignment value is a count of NEW conserved distinguishing
  sites times a weight, W = 1 / E. The owner: "i think you have to add a weight factor to MSA scoring yes? that will fix it";
  "so if you expect 10 conserve sites per protein on average, you would make the weighting 0.1 -- now I don't know how many
  conserved regions there generally are, so you will have to figure that out" (`a101_conserved_sites.md`). E is derived from
  real data, not guessed: E = 7, the median number of distinguishing sites per candidate per alignment over the stored real
  alignments (23 values from 7 distinct alignments, all of one 70-residue target; median 7, mean 8.3). Re-derive it as alignments
  of other targets and lengths accumulate. The count x W is then weighted by the msa sheet's weight like every other sheet's values (its typical strong value is 12 new sites x W). Any new measurement of yours that is a count needs a weight derived the same way,
  from stored real results, with the derivation written beside the constant.
- The rule behind the count: "the residue conservation pattern in one group vs another helps differentiate function, yes? so in
  theory, the same residue pattern on the same conserved sites should not add anything... and so maybe that is what you should be
  recording, i.e., the number of conserved region matches". So evidence that is the same adds nothing; identify what is
  counted (here a site by target position, the group's residue and the candidate) so a repeat is recognised.
- Data products: a file a unit made or fetched that another unit may use again is labelled and kept for reuse, with its EDAM data
  type and EDAM format, its W3C PROV links (`generated_by`, `used`, `derived_from`), its other locations, and a `reuse_key`. A step
  that needs another step's output asks for its KIND with `require_product`, never a file name. The owner: "MetaCATS needs to have
  a requirement that it needs an input MSA, which means we need to start storing and labeling data and data products for reuse"
  (`bvbrc_msa_episode.md`). The reuse refusal lives only in the request checks (before anything runs).
- What a result is NOT: a test that gives no usable measurement gives no measurement. A p-value is not the measurement: the owner,
  "MetaCATS doesn't even help reach much of a conclusion with p values.... that's not the part that matters", and "It's wrong that
  it has no credit. i told you it gains credit by confirming conserved sites in comparison to a gene family." (2026-11-21). So
  MetaCATS is measured by the candidates' matched conserved sites of the analysed alignment whose columns it finds significant and
  no earlier report confirmed, x W, on the msa family (`a101_conserved_sites.md`).

**Where A101 does it.** Measurements and the test names: `LIB/grading/sequence_homology_evidence/candidate_measurements.py`.
Arithmetic: `LIB/grading/sequence_homology_evidence/differential_credit.py`. Sheets: `msa_alignment_sheet.py`, `cluster_sheet.py`,
the BLAST and HMMER graders under `LIB/grading/`. Data products: `LIB/records/data_products.py` (`KINDS`, `record_product`,
`find_reusable`, `require_product`). Retained gradings: `LIB/grading/sequence_homology_evidence/tool_grading_artifacts.py`.

**How to check.** Read the sheet of one real result by hand and recompute one measurement from it. For a count measurement, run
the same alignment twice and confirm the second adds nothing. A direct recomputation on a copy of stored records is a direct
check, labelled as one.

---

## Step 7. Credit

**What to build.** The episode's `credit(summary, records)`: a number that counts what was gained, computed from the records the
episode holds, counted the moment a graded sheet is held. No reasoning commit switches it on or off (owner ruling of 2026-11-20,
`a101_tree.md`).

**The rule.** The owner's differential credit (`a101_differential_credit.md`, verbatim):

- "(1) adding new possible annotations gets you a score (2) differentiating those scores (i.e., abs[S_A(t=i+1) - S_A(t=i)] vs
  abs[S_B(t=i+1) - S_B(t=1)] vs .... for all possibilities"
- "I mean that if S_A moves +0.5 and S_B only moves +0.1, then you have differentiated the lead candidates by 0.4"
- "i --> i+1 is related to the test in that turn, so they undergo the same test but credit differentiates, then that's added
  score. it encourages the same test to be applied clearly because that earns the differential credit and it encourages tests that
  differentiate results"
- "with only one candidate known there is no need to differentiate"
- "i resolved this by saying you need positive evidence to admit a possibility" and "so sometihgn random cannot be on the list at
  zero. i got rid of the possibity of zero basically"
- On a second candidate entering and earning the leader's score: "that's a little bit weird ... I think we shoudl fix that really
  ... adding a possiblity should be good in that we are searching and finding nsomething positive, but finding better
  possibilities is better, right?"

So: a candidate annotation is admitted on positive evidence (a first value above zero) and earns its own score once, at entry,
and only that. A test that two candidates already on the list both undergo earns the absolute difference of their moves.
Differentials count for tests after both candidates are listed. Credit is the sum of the entry scores and the differentials; it
never falls; a repeat earns nothing. Measurements of different targets are never compared.

Credit is NOT the annotation score. Credit is what the episode optimises (what was gained). The annotation score is a score per
possible annotation (a candidate's score, the sum of its sheet values); the head returns the candidates with their scores, the
leading one first, as the annotation prototype. Keep the two apart in every message and name.

Also: a child's credit is information in the parent's summary and is never added into the parent's credit.

**Where A101 does it.** `HEAD/credit.py` (`credit`, `A101DifferentialCredit` the definition record), `LIB/grading/.../differential_credit.py`
(`differential_credit`, `standing`), `candidate_measurements.candidate_table`.

**How to check.** For a stored run, recompute each unit's credit by hand from the scores before and after (entry plus differentials) and
compare with the journal's controller steps. Confirm a repeat of a unit adds exactly 0.

---

## Step 8. Ceilings

**What to build.** `ceiling` for every action the episode offers, derived from the current state (Step 1 states the contract).

**The rule.** "ceiling is a function that has to be how much max credit from this current state"; "you should know that a second MSA
is going to earn very very little. that's the point of tying to ceiling values. MSA can only add so much more now"
(`a101_conserved_sites.md`). So a ceiling is a PROVED maximum from what the episode holds now, not a forecast and not a constant
filled in everywhere:

- An action the request checks would refuse as a repeat has ceiling 0.
- A test that measures one listed candidate and admits none earns 0; a pair of listed candidates earns at most the family weight; a
  candidate the test admits earns at most its entry (`differential_credit.test_ceiling`).
- The alignment's ceiling is derived from the target positions not yet identified, with the proof written in the docstring of
  `differential_credit.msa_test_ceiling`.
- When an action's ceiling depends on its arguments, supply `best_arguments` (optional) so the row shown to the model is the
  ceiling of one named commission, and so a refusal can say what to choose.
- `UNBOUNDED` only where truly unbounded, with the reason in the docstring (A101: `execute_selected_tool`).

**Where A101 does it.** `HEAD/credit.py` `ceiling` (its docstring lists each action's derivation), `best_arguments`, `msa_best`;
`LIB/grading/.../differential_credit.py`.

**How to check.** The runner checks every ceiling against the real rise and journals both. In a real run, no unit may exceed its
ceiling (`episode_ceiling_exceeded`). Hand-derive the ceiling for one state and compare with the journal.

---

## Step 9. The forecast yield controller

**What to build.** The episode's `yield_estimator.py`: the forecast controller over the episode's ceilings, plus its declaration in
the run's continuation settings.

**The rule** (`forecast_yield_controller.md`, `yield_control/__init__.py`). The owner's words:

- "Refusing a test that can't differentiate is kind of like saying you can estimate how much potential credit can be earned ...
  humans act based on an expected outcome and just like our job launcher has an expected outcome in terms of how long it will
  take, maybe these should have to have an expected outcome worked out to launch ... if the model knew it wouldn't gain much, i.e.,
  it had a better yield estimator, then it would not do these things or the yield estimator woudl cut it off"
- "this way, you can't have the model estimate anything really. it's still a mathematical formula, yes?" (yes: the forecast is a
  formula, never the model's)
- "so this then is a 4th type of yield estimator yes? and I would like to make it generalizable to other episode structures, which
  means it needs some kind of generalized parameter set that can be plugged in and work with any other credit formulas"

The formula, for an offered action of kind `<binding path>:<action type>`:

- Forecast = learned share x ceiling. The learned share is the share of its ceiling that actions of that kind earned. The ledger's
  history of the kind and this run's own units of the kind each weigh one half: "count this current history always more. the ledger
  should count for equal weight with current history". With only one of them that one counts; with neither, one half. Inside this
  run's own units the latest counts most (weight 1, each earlier unit half the one after it): "the yield estimator must learn just
  like the accumulation estimator from past experience after the first round. So after nothing new is added a second time, the
  yield estimator should be very low for that". Ledger rows older than the forgetting policy count less and then drop.
- UNBOUNDED: the typical gain of the kind by the same rule; with no unit of the kind anywhere it is unknown, and an unknown
  forecast never stops the episode.
- Cost = expected seconds (measured unit seconds of the kind, from the previous unit's progress receipt to its own, so decision
  time is included; a ledger job duration when the action type is declared in `job_kinds`).
- The per-action gate: after `action` has chosen an action and its ceiling is asked with its arguments, the chosen action is
  refused (no unit, the model decides again) when its forecast does not exceed expected seconds x exchange rate, with feedback
  `action_forecast_not_worth_its_cost` (it carries the best commission's arguments when the episode supplies `best_arguments`).
- The stop rule: the episode stops when no offered action's forecast exceeds expected seconds x exchange rate. Only the controller
  stops an episode. No budget of time, tokens or turns exists; the cost is a forecast input.
- One exchange rate, set in the episode's `yield_bindings` entry (`kind: "forecast"`, parameters `exchange_rate`,
  `forget_old_rows`, `job_kinds`, plus the credit definition the declaration is checked against). A101's current value is
  0.0065 credit per second. It was chosen from the replay of the stored run `runs/a101_conserved_ws_C2` with the per-action gate and
  recency weighting: the one range that runs the first three units, refuses the repeated alignments and MetaCATS, and wastes at
  most one unit is 0.00641 to 0.00654 (below it a worthless unit runs, above it the one-pass history refuses a worthwhile one). The
  window is narrow and depends on the credit's units: when your credit's scale differs, re-derive the rate from a stored real run
  of your axis the same way and write the derivation beside it. Do not copy 0.0065.
- The model is shown the forecasts as facts (`action_forecasts`: ceiling, forecast gain, expected seconds, worth, and the best
  commission's arguments when the episode supplies `best_arguments`) and never sets one.

**Where A101 does it.** `HEAD/yield_estimator.py`, `yield_control` (`ForecastYieldController`), `episode_runtime/forecast_ledger.py`,
`method_loop/episode_type.py` (the gate and the ceilings handed to the controller), settings file of a run (the `yield_bindings`
entry).

**How to check.** Replay the journal of a stored real run through the controller (a direct check: it shows what the rule would have
done, not what the model would have done). Then a real run: the episode must stop within a few units of the last gain, and the gate
must refuse a repeated test. The old pattern where 19 units followed the last gain (accumulation controller, run H1,
`a101_differential_credit.md`) is the failure this replaces.

---

## Step 10. Wire a child into its parent

**What to build.** In the parent: the slot in `CHILD_SLOTS`, the commission (controlled fields the model fills, as a function of the
summary and the bound resources; `None` while the commission cannot be stated, so the slot is then not offered), ONE deterministic
check of the filled commission (`COMMISSION_CHECKS`), the description of the child the model reads, the objective and custody in
`msg_to_child`, the child's return in `read_from_child`, and the child's rows in `internal_summary` and `final_to_parent`.

**The rule.** The model writes no assignment, objective or message: it chooses the controlled fields; code builds the child's
assignment. A repeat commission is refused by the check. A description states facts the system enforces (for example that while a
child runs the parent does nothing else) and never recommends which action to take. A slot is offered only while its commission can be
stated from what the parent holds.

**Where A101 does it.** `HEAD/task.py` (`CHILD_SLOTS`, `COMMISSIONS`, `COMMISSION_CHECKS`, `CHILD_DESCRIPTIONS`, `SELECTABLE`),
`HEAD/messages/msg_to_child.py`.

**How to check.** A real run through the parent in which the model commissions the child from the controlled fields, the check
refuses a repeat with a fix list, and the parent summarises after the child returns.

---

## Step 11. How to test

**The rule.** The owner's decisions (plan decisions D1 and D25, `docs/plan/A101_blast_regions_plan.html`):

- "Test for real, not with pytest. Test each subtree leaf to root and make it work slowly: predict, run, inspect the evidence,
  learn, then decide the next change. Running a leaf is not a test; judge it against its intention."
- "Real runs only: a real run is a command-line run through episode_runtime. No pytest, no tests/ folders, no harness scripts in
  the repository. A leaf is tested with the input its real parent sends."

So:

- Never write pytest, never add a `tests/` folder, never a harness script in the repository.
- A real run is `python -m gene_annotation_episode run` with the real model and real services, started through the single-workflow
  launcher: `bash tools/one_workflow.sh --slot <lane> runs/<unique-run> -- <command>`. One workload per lane at a time. Everything
  disposable goes under `runs/`. The steps of a run: `init` and `add-material` (register the caller's material), `propose-annotation`,
  `freeze-libraries` (prints the axis selection the commission carries), write the commission, continuation and services JSON,
  `run`, then `report` (reads the journal back) and `resume` (replays; asks the model nothing). The design of the commands is
  `docs/plan/designs/real_entry.md`; a complete set of files is any workspace `runs/a101_final_ws_*`.
- Write the prediction BEFORE the run, in the note of the piece. After the run, state predicted against observed, point by point,
  with the run directory. Keep what the run showed even when it failed.
- Replays and direct calls on stored records are direct checks, labelled "not a real run". They never prove that a behaviour exists.
- A run loads a pinned git worktree (a checkout at a named commit), never the files agents are editing. The launcher takes its
  repository from its own location, so use the launcher of that worktree. A101 runs failed at link time or ran half-edited code
  because another agent's folder was mid-edit (`bvbrc_msa_episode.md`, run M1).
- Fix everything known before a round of runs. A run is spent on what you could not know, not on a defect you had already seen.
- Account limits on outside services are a hard cap. The BV-BRC account has per-step limits set by the owner (A101 used at most 1
  `Homology`, 3 `MSA` and 2 `MetaCATS` jobs at a time). Count requests that were refused too. Put a guard in the run that stops
  the unit before the commission that would exceed a limit. A101 once ran one over a limit of 3 because the retry loop only stopped
  on a parked search and not on one that ran to its result (`bvbrc_blast_episode.md`, run P2b).
- Never print or write a credential. The BV-BRC login is read from the owner's token file only inside the launcher's command
  (the `run.sh` pattern: the variable is set for that one command), never echoed, never in a services file, a journal or a note. After
  each run search the run's files for the signature pattern of the token and report the count; A101 did (`bvbrc_blast_episode.md`).
- Check a new outside application live once, outside a run, through the project's client, before building on it, and write down
  what was verified and how (`bvbrc_metacats_episode.md`, "What was verified against the live service").

---

## Step 12. How to work

- Break the work into pieces, one agent per file set. Each brief states the goal, the files it may edit and the files it must not.
- Commit by exact path: `git commit -m '<message>' -- <paths>`. Never `git add -A` and never `git commit -a`. Another agent's
  uncommitted work in the tree must not be swept into your commit.
- Before editing a document run `git status --short <path>`. If it has changes that are not yours, leave it and say so; edit it later
  only if it is clean.
- Read the owner's words literally. A replaced rule is deleted, not marked. "For now" is not the goal: build what the owner described
  and do not hold back for a smaller version. When two readings are possible, take the stricter one or ask.
- Step zero for every function: write down what already exists and is called, and what is new and why an existing one could not be
  used as is (the tables at the top of each `*_episode.md`).
- Report only what you verified, with run directories. Label what a direct check showed and what another agent relayed.
- Never search recursively over `runs/`; use `git grep` and `git ls-files`.
- When something is no longer wanted, delete it (`AGENTS.md`, "Removing unwanted code"): delete the old path before porting onto the
  new one, so hidden dependencies fail at once.

---

## Step 13. Pitfalls A101 hit, and what fixed each

1. One test pooled several jobs. Two alignments of different candidate sets were averaged as replicates of one test. Fixed: one test
   is one graded source, named `<kind>@<source>` (`f227c34a8`). The same change broke the head's MSA options, which matched a test by its
   old name, so no alignment was offered in run C1 (`a101_conserved_sites.md`); fixed in `2111b654f`. When a name changes, search for every
   place that builds or matches it.
2. The averaging rule. A candidate's score was a mean over its tests. The owner deleted it ("the averaging rule can be deleted. that
   obviously will not work") and the additive rule stands (Step 6). The mean was deleted, not marked superseded.
3. The MSA value as a fraction of new sites. In run R1 the head commissioned 4 alignments and 7 MetaCATS jobs and each earned credit though
   most repeated what earlier jobs had shown (`a101_conserved_sites.md`). Fixed: a count of NEW matched sites times W = 1/E, with E derived
   from real alignments (Step 6); a second alignment now earns very little and its ceiling says so.
4. Ledger durations measured at the wrong moment. The recorded duration was the wait until the status request that noticed the end, so
   estimates rose run after run (ten searches recorded 66 to 103 s while the service's task records said 26 to 58 s). Fixed: the
   service's own task record, with the observed seconds kept beside it (`afe878d1c`).
5. Custody reads of names (Step 5).
6. The refusal loop between the gate and the stop rule. The stop rule judges the offered row, whose ceiling is asked with no arguments (the
   most over every commission the episode can make), while the gate judges the commission the model chose, with its own lower ceiling. An
   action could stay offered as worth taking while the commissions the model named were refused. Fix: `best_arguments` names the commission
   that reaches the row's ceiling, the shown row carries it, and a refusal carries it as `choose_from`. Not verified in a real run at the
   time of writing (Step 14).
7. Agents exceeding job limits (Step 11).
8. Runs on files being edited (Step 11).
9. A tool offered a call that could not succeed and the model repeated it 21 times (first A101 run). Fix: offer only calls that can
   succeed and refuse a repeat in the check; and a job folder outside the run's directory made every job refuse; the services file keeps it
   inside (`a101_tree.md`, runs 1 to 3).
10. The credit moved with the model's own interpretation. A reasoning commit switched the credit on and off and the model kept revising
    it. Fixed: grading is automatic and the credit reads the graded sheets only.
11. A controller that did not stop. The accumulation controller let 19 units follow the last gain. Fixed: the forecast controller (Step 9).
12. A source of the wrong provider was refused by the Store. Read the Store's admission rules for a record type before shaping a record
    for it, or ask the owner to change them (`bvbrc_blast_episode.md`, run A defects).
13. A one-family set clusters as one cluster, so a clustering test is uninformative on it (`all_vs_all_episode.md`, direct checks). A
    measurement that cannot separate the candidates earns little and its ceiling should say so.

---

## Step 14. What is still open in A101 (so you do not copy something unfinished)

Read at the time of writing (2026-11-21), from the notes and the code:

- The final two-protein runs (E. coli CspA and RecA) are in progress by another agent; no note records their result.
- The best-commission fix of Pitfall 6 is committed (`best_arguments`, `choose_from`) but no real run has shown a refusal carrying it.
- The `all_vs_all` child is wired into the head's `CHILD_SLOTS` in the working tree; no note records a real run of it through the head.
  Its design note is being updated by the agent that wires it. Before copying it, read the code of `HEAD/all_vs_all/task.py`: the child
  runs `prepare_database`, `all_vs_all_blast`, `cluster` (a tuning try that grades nothing) and `commit_clustering` (the one clustering
  the head reads).
- The scoring sheet's weights (`SHEET_WEIGHT`, `TYPICAL_STRONG_VALUE`) and the head's credit record `a101_differential_credit_v5` are in
  the working tree and derive from a single target; they are to be re-derived and the continuation files of earlier runs name `v2`.
- The weight W = 1/E (E = 7) rests on seven alignments of one 70-residue target.
- A parked job resumed by a later head run, after the head itself ended while the job was parked, was not achieved (`bvbrc_blast_episode.md`,
  run P2b). The `fix` path, a failed launch and a search that keeps running until the controller winds the child down were not exercised
  in a real run.
- The profile-scan ceiling is the profile database's model count (53275 for Pfam-A), which is loose: with no history of the kind the
  forecast stays large (`forecast_yield_controller.md`).
- HMMER has only its tool (`hmmer_profile_scan`); there is no HMMER child episode (`HEAD/hmmer` holds only `__init__.py`).
- Cluster and HPC leaves are not built (the owner's order: local first). Functional regions and joint credit are deferred
  (`docs/plan/DEFERRED_functional_regions_joint_credit.md`).
- Reference-only `old_*` folders under HEAD are the old generic launch, monitor and results episodes. They are not for running and are
  not a pattern to copy.
- Two removed pieces are history, not patterns: `database_blast` (a hosted NCBI search child with four actions: submit, check,
  fetch_and_grade, hold) and `blast_database_preparation` (now the `prepare_database` tool of `all_vs_all`). Their notes keep their
  run observations only. The pattern for a job on an outside service is Step 4.

---

## Appendix: where each A101 note is

| Note (`docs/plan/designs/`) | What it holds |
|---|---|
| `a101_tree.md` | The current tree, tool or child for each node, the first patterns and their runs |
| `a101_differential_credit.md` | The owner's differential credit, the additive rule, the annotation prototype |
| `a101_conserved_sites.md` | The alignment measurement (count x W) and the MSA ceiling |
| `a101_child_returns.md`, `a101_child_returns_audit.md` | The return rule and the audit of head-side reads |
| `forecast_yield_controller.md` | The forecast controller, the gate, the exchange rate |
| `bvbrc_blast_episode.md`, `bvbrc_msa_episode.md`, `bvbrc_metacats_episode.md` | The job children |
| `all_vs_all_episode.md` | The all-vs-all child (tools, data products, the cluster test) |
| `real_entry.md` | The `run`, `resume`, `report` commands |
| `database_blast_episode.md`, `blast_database_preparation_episode.md` | Removed from the head on 2026-11-21; run observations kept |
