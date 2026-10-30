# Required genome reference-frame test: unchanged baseline failure

The exact186 source manifest omits seven retained Mauve fixtures required by this existing test. Their source paths, hashes and byte counts are in supplemental_fixtures.json. They were copied without regeneration; source/test code was not changed.

- focused_001: 95 passed, 1 failed because FILLED_EXAMPLES_001.json was absent (exit 1).
- fixture_retry_001: failed because official_small.document.json was absent (exit 1).
- fixture_retry_002: after the fixture dependency closure was populated, failed in 43.19s during GenomeDriver.acquire_native -> AppServicePublications._grade -> build_genome_alignment_data -> validate_genome_alignment_data -> _links. Error: bvbrc_genome_alignment_provider_requirement_reference_unknown (exit 1).
- baseline_fixture_001: same test, an owned exact 1,045-path frozen186 clone with the same seven fixture hashes, failed at that identical scientific validation path and code in 42.64s (exit 1).

The failure occurs before the test's typed form traversal, so this case does not establish frame correctness in either candidate. No scientific calculator, parser, reference rule or test expectation has been altered to bypass it. The separate existing proteome frame tests and differential boundary tests passed in focused_001. The baseline failure remains explicit unfinished verification; it is not an implementation pass.
