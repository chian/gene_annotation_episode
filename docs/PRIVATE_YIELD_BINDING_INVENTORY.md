# Episode credit and yield bindings for the combined genome run

Every child credit belongs to its original proposed annotation. A task's owner
selects its credit projector, yield estimator, and cutoff from the saved original
assignment or an owner declaration keyed to that task. A missing declaration is
an error. Each axis owner reprojects evidence actually returned to the root,
deduplicates its physical identities, and reports one credit per annotation and
axis. The root forecasts another whole axis invocation and takes the maximum
per-annotation sum as its own earned credit.

| Owner/task | Earned task credit | Yield estimator | Cutoff source |
|---|---|---|---|
| Root, each annotation/axis | Axis-owner progress reprojected from admitted evidence; A102/A104 use one native-quality point per distinct use, finding, or preparation artifact | Per-arm forecast of another whole axis invocation, then root selection across annotation/axis pairs | Root `root_task.cutoffs[axis]` |
| A101 sequence correspondence | Current assessed native quality for the commissioned annotation | Bounded native quality, maximum 1 | `scientific_yield_bindings` exact A101 task |
| A102 comparative structural discovery/comparison | Current assessed native quality for the commissioned annotation | Bounded native quality, maximum 1 | Exact A102 task |
| A102 functional feature geometry/contrast | Distinct resolved native results for the commissioned annotation, including measured zero | Open accumulation | Exact A102 task |
| A102 reference/trait/interface attribution | Distinct authenticated reference, trait, or contact uses linked to current assessment for the annotation | Open accumulation | Exact A102 task |
| A102 experimental and shared tasks | Typed findings for the commissioned annotation | Open accumulation | Each exact A102 task |
| A103 context tasks | Current assessed context quality for the commissioned annotation | Bounded native quality, maximum 1 | Each exact A103 task |
| A104 panel identity/alignment suitability | One authenticated frozen panel request or one complete validated alignment import for the commissioned annotation | Finite remaining preparation credit; observed yield before completion, exact zero after | Each exact A104 task |
| A104 robustness | Distinct resolved robustness results linked to current assessment for the annotation | Open accumulation | Exact A104 task |
| A104 evolutionary tasks | Current assessed evolutionary quality for the commissioned annotation | Bounded native quality, maximum 1 | Each exact A104 task |
| A105/A106/A108 scientific findings | Typed findings for the commissioned annotation | Open accumulation | Each exact whole-axis task |
| A107/A110 component tasks | Typed findings for the commissioned annotation | Open accumulation | Each exact component task |
| A105/A106/A108 verified source leads | New verified useful source leads for the original source question | Open accumulation | Literature owner declaration for each axis and lead task |
| A105/A106/A108 assessment and screening answers | Original requested answer | Finite remaining commissioned credit | Literature owner declaration for each axis and answer task |
| A105 measurement answer, experiments, assembly | Original requested measurement, distinct commissioned graded experiments, or assembly answer | Finite remaining commissioned credit | Literature owner declaration for each task |
| Ordinary launch | Distinct original eligible requests with usable handoffs; retries of one request earn no extra credit | Remaining request credit with exact zero at exhaustion; observed yield before then | Execution owner profile for the original request classes |
| Ordinary API/local/HPC launch | Authenticated handoff or satisfied original practical requirements | Observed yield until the verified endpoint, exact zero after | Execution owner profile for the selected service or practical task |
| Ordinary results | Requested byte-position coverage or typed result credit | Remaining coverage for finite requests; accumulation for open-ended paths; exact zero only with a proven finite endpoint | Execution owner profile for the original selector and resource kind |
| HPC parent/prediction/execution | Original commission obligation, model improvement, and validation credits applicable to each role | Pending-work-aware forecast while work is in flight, observed yield otherwise, exact zero after accepted completion | Each role's `yield_bindings` in the original HPC commission |
| Monitor | One information unit per newly informative received progress snapshot | Open information accumulation; repeated identities and read timestamps earn zero | Monitor owner's `monitor_yield_settings` |

The scientific owner recognizes A101, A102, A103, A104, A105, A106, A107,
A108, and A110. A111 is merged into A102. The combined scientific owner rejects
an assignment without `proposed_annotation_ref`; runtime passes the original
saved annotation to the credit projector.

## Calibration before the first genome

The new task-local units have no exact comparable historical run. The confirmed
A105 `0.075` cutoff belongs to the former broad finding credit and cannot be
claimed as a replay result for these tasks. Retained execution replays do show
necessary zero-credit preparation: one successful `launch_hpc` had 13 such
actions before a handoff, and the current immediate-yield upper forecast fell
to `0.0316707` at one point. HPC parent episodes kept higher forecasts when
pending obligations were registered. Those are different roles and cannot
share a cutoff. Positive task-specific cutoffs are still required before a
combined biological run. A positive A104 alignment preparation credit has no
small end-to-end importer fixture yet.
