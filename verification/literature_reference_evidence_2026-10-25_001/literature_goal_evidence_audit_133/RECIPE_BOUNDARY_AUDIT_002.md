# Focused native-recipe boundary review

Conclusion: the missing in-episode recipe writer is a real capability limit,
but it does not establish an additional required implementation blocker for the
fixed goal under the user's explicit deferral. The implemented A108/A110 native
routes have a legitimate, bounded input contract: a caller/upstream supplies a
retained source-selection recipe and the original sources; the selected reader
reads the nominated original values, validates their relationships and populates
the existing numerical sheet. Do not describe those two routes as autonomous
new-paper-to-recipe workflows.

This conclusion is narrower than saying the deferral explicitly waived recipe
authoring. It did not name recipe authoring. It deferred the exact link from a
searched paper to selected graders/sheets. The fixed goal still requires real
readers, numerical functions and selected LiteratureEpisodes execution; those
remain independently necessary and cannot be replaced with a future-routing
description. The native routes now do execute primary-source number extraction
from selected witnesses rather than accept model-authored scientific values.
The fixed goal does not independently require every reader to accept an inline
model-built recipe or require a generic source-write operation.

## Actual capability trace

| Boundary | Inspected implementation | What is established |
|---|---|---|
| Selected operation inputs | Complete current `context_population_schema` and `reaction_population_schema` in `literature_context_inputs.py` / `literature_reaction_inputs.py` | Both are closed objects containing `source_ref`, nullable reference-valued `data_source_ref`, `source_kind`, literal witnesses and interpretation witnesses. There is no inline `selection`/`recipe`/native-input object argument. |
| Recipe read | Complete current `_measurements` and `read_*_inputs` functions | Non-null `data_source_ref` is read as original source bytes and decoded as JSON. Its version selects the native reader. A recipe must already be a registered, received, scoped source. Null yields unavailable scientific inputs, not an invented recipe or extracted measurements. |
| Actual native extraction | Complete `read_native_selection` / `read_native_reaction_selection` implementations | The helpers accept a Python dictionary internally, then read nominated source numbers/units/spreads/counts through the authorized `_Sources` callback and normalize inputs to the unchanged calculators. They preserve recipe/source traces. Their Python signatures do not make them inline episode operations. A108 method settings/equal-unit weights and A110 named prediction/coefficient parameters remain distinct from selected source measurements. |
| Scoped source authorization | Current LiteratureEpisodes assignment/catalog/dispatch path and repository `_source`/population path inspected in audit001 | Both the recipe and its nominated sources must be actually available in the episode's received scope. Knowing an ID is not source delivery. A page's source-lineage constraints still apply. |
| Episode read/write capability | Actual `_ACCESS_TOOLS`, `_ACQUISITION_TOOLS`, catalog filter and operation schemas; actual ordinary reasoning schema in `domain.py` | Literature offers source reads/locates, acquisition and prescribed archive/PDF/XLSX derivatives plus the finite population operations. None is a general arbitrary-JSON source/artifact writer. Ordinary reasoning can commit typed contexts, subjects, observations, hypotheses and assessments, but cannot create source/artifact bytes. Reports and source-subject labels do not become recipe sources. |
| Caller preparation | Actual `State._caller_source` and `register_material(...,data=...)` paths | Host/caller code can retain JSON or input bytes as immutable sources and then supply their references through the ordinary received-source assignment. These are host APIs, not selected LiteratureEpisodes tools. No generic model-to-recipe persistence bridge was found. |
| After reader selection | Current repository persistence/typed receipt path; root's later final verification and handoff | The recipe's pre-existence does not bypass the executable source reader or calculator. The selected operation still reads source operands, commits its sheet/outcome and delivers constrained requested results. This audit did not rerun the parent's final23+6 checks. |

Consequently an ordinary episode starting with only an arbitrary new paper
cannot presently author/persist a new A108/A110 recipe using this catalog alone.
It can read the paper, interpret it through its ordinary actions and choose among
available received inputs, but no hidden conversion of its reasoning/report into
recipe bytes exists. The model-backed A105 direct-selector route is a separate,
functional route and does not prove A108/A110 recipe authoring.

## Exact user direction and its limit

The complete engineering direction record
`LITERATURE_GRADER_SELECTION_TARGET_040.md` was read. It preserves this user
message:

> So for clarity, the way you are working, a literature search would be launched and based on the paper, it would then be routed to one of the graders/scoring sheets, yes? It's not important to implement this exact link now, it's important bc you need to know what you are building for.

That explicitly leaves the searched-paper-to-grader connection deferred while
requiring designs suitable for that future choosing investigation. Requiring a
generic recipe-writing bridge now solely to make A108/A110 autonomously callable
after arbitrary new-paper reading would extend that deferred linkage. No separate
fixed-goal completion bullet specifically requires that bridge. Supplied selected
files/structured selections are within the fixed goal's input scope, and its
completion criteria ask for working readers, source examples, selected execution,
typed delivery and reconstruction rather than universal automatic routing.

The deferral would **not** excuse an absent numerical source reader, unavailable
ordinary population operation, numbers supplied only by a mock, an untested typed
return or a claim that arbitrary scientific prose is automatically understood.
Those are different requirements. Here the observed limit is preparation of the
reader's structured selection input, not absence of its measurement extraction or
calculation once selected.

Recommended final scope statement:

“A108 and A110 native readers execute within LiteratureEpisodes from supplied,
retained selector recipes and original sources. They read and validate the actual
source operands and preserve typed results/reconstruction. Creating and retaining
a new recipe from an arbitrary newly found paper within an episode is not yet
available; the automatic paper-to-grader connection remains deferred.”

No new feature, paper read, scientific packet, amendment, runtime gate or
production-file edit was made for this focused review. `RECIPE_BOUNDARY_002.json`
records the actual input-schema/catalog capability inspection. The audit does
not claim that every possible future upstream selector or routing process is
implemented or scientifically validated.
