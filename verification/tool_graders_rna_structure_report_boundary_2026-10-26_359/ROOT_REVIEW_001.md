# Root review of registered RNA return schemas

Root read the complete communication validator, the affected RNA schema
factory, actual TypedReportContract construction/admission and existing
communication tests before changing the validator. The change admits only
exact registered RNA fact schemas at the original permitted top-level field.
It does not widen generic prose, units, reference access or nested schemas.

check001 passed 172 tests in 1.32 seconds, including the new RNA boundary tests
and existing communication/structure-selector suites. The actual local_jobs
receipt reports exit 0 and unchanged source pins during the run, with 20 GiB
memory, 4 GiB scratch and no wall cap. Root inspected that receipt and stdout.

Tests cover all seven registered facts, malformed or extended schemas, nesting,
strict scalar-schema identity, nullable failure-source reference validation and
generic unregistered/freeform rejection. Recorded facts remain distinct from
model interpretations. Existing reference validation remains authoritative.

This verifies schema recognition only. It does not establish the complete
358/360 execution-to-parent path or new structure/comparison/scan projections.
No prompt wording or grader completion count changes follow from this work.
