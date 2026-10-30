# Explicit numerical-summary nesting

This clarifies the ambiguous phrase "flat numerical summary" in CONTRACT_001;
the original contract remains unchanged.

Both grade_* functions return exactly `{sheet, scores}`. Both calculators return
a tool-specific object containing `schema`, `summary`, the tool-specific row
collections, `component_status`, `issues` and numerical definitions. `summary`
is one dictionary with every required numerical name from CONTRACT_001 mapped
directly to a finite number or null. Do not duplicate those names at the scores
top level. The declared component statuses carry missing/incompatible reasons.

Root's publication adapter calls `_grading_values(scores['summary'], names)`.
The actual publication/Workflow tests compare `scores['summary'][name]` with
the corresponding numeric observation measurement. No JSON object is itself
an LLM prompt; complete rows and definitions remain in the retained artifact.

All function arguments, owned files, scientific meanings and verification
requirements remain as declared in CONTRACT_001.
