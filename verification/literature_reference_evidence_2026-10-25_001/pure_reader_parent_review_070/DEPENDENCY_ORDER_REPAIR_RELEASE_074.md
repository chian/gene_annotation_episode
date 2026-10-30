# Continue070: fix actual canonical-JSON dependency replay

Root reproduced a real public-API failure after final017. See
probe_dependency_order_001.py and DEPENDENCY_ORDER_COUNTEREXAMPLE_001.json:
synthetic JATS plus subject/genotype witnesses on distinct sources reads and
validates successfully, then json.dumps(sort_keys=True)/json.loads makes its
own saved extraction fail saved_relationship_mismatch at sources.roster.

Cause: _dependencies traverses object insertion order while canonical durable
JSON sorts object fields. This is a reconstruction defect, not missing scientific
information. All earlier tests/pins/source identities remain preserved; their
coverage did not establish this multiple-source canonical replay case.

Continue the SAME070 workload, owning only its three existing newly created
production modules and three owned tests. New artifacts go ONLY to NEW sibling
a105_visual_signal_reader_repair_074/ and descendants. Original sealed070
directory, manifests, pins and examples remain untouched/no extras. No other
production/test/shared/native/history file is authorized. No new paper/model/
workflow/credit/controller or observations.

Define dependency order independently of object insertion order: unique source
pairs sorted by (source_ref,representation), unique view refs sorted lexically.
Preserve original ARRAY order for scientific representations/candidates/reading
alternatives and keep exact008 schemas/meaning. Prefetch each actual declared
dependency once before helpers. Dependency traversal/order must agree before
and after canonical JSON, selection/extraction detachment and saved validation.
Do not hide mismatch by sorting only at validation or silently rewriting saved
scientific arrays. Current prototypes are pre-acceptance; old generations remain
readable under their original pins, with no in-place receipt migration.

Add meaningful public API tests: multiple independent generic sources,
multiple selected views, shared aliases and array ordering; canonical-JSON round
trip must preserve valid values, meanings and source/view rosters, with no
source/view callbacks or decoders during saved checks. Reordered object keys
must not change validation or actual output; reordered scientific arrays retain
their actual array meaning. Preserve the original root counterexample as failing
evidence, then execute a fresh corrected probe instead of overwriting it.

Coordinate071's actual repository canonical read/replay and first fresh source-
free requested-subset proof on this case. No API/schema simplification, skipped
operand, fake successful validation or numerical expected-output replacement.
Run affected focused pure/legacy checks, freeze actual coherent code/helper/
tests/contracts/environment, execute from the new pin and prove imports.
Give root exact patch since017, new identities, actual reproduced+repaired
outputs and precise limits. Full experimental/native/model/C1/C4 work remains.
