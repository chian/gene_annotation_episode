# Additive precision correction to sensitivity report 001

2026-10-23. Preserve `RELEVANCE_SENSITIVITY_001.md` and its arithmetic unchanged.
Its statement “A general scalar cannot simultaneously ignore every missing
family and guarantee that losing an unfavorable observation never raises its
point” is too broad for arbitrary scalar functions. The precise statement is:

**A strictly increasing, idempotent averaging rule cannot both ignore missing
components and guarantee that removing a low observed component never raises
the conditional point.** For two observations x<y, such a mean has
`M(x,y)<M(y,y)=y`; with only y observed, idempotence gives `M(y)=y`.
Both the arithmetic and shifted harmonic means tested here have this behavior.
No universal impossibility claim about all scalar functions is needed.

For machine interpretation of the synthetic JSON, the scope-change diagnostic
`unknown_site_removed_from_declared_scope` uses the four-family order
`(sequence, structure, placement, system)` stated in its note and the report.
All other case vectors use the five-family order in the artifact. The fourth
entry of that one diagnostic is system similarity, not site correspondence.
Its arithmetic compares a deliberately different scope; it is not a legitimate
way to erase an applicable unknown site component.
