# Exact results-filename correction

The unchanged verification report docs/MODEL_CONTEXT_PRESENTATION_VERIFICATION_2026-10-22_001.md, SHA256 edde00e4964c3198b215f718853af857919ddb45f85f042967932de88a803e6d, incorrectly labels the final aggregate as "Root RESULTS.json" while giving SHA256 e06c80b7274ee7683cc398f8a4d98125e522a71bd58d872a1f5c56f99c75f499.

That exact hash belongs to verification/model_context_presentation_2026-10-22_001/evidence/root/RESULTS002.json. It selects the final dedicated-directory detached invocation, connected002, one pass in19.40s, alongside the67/21/28-case groups. The117 executions contain116 distinct cases across seven files, with one explicitly repeated existing WaitInputs case. The manifest98e73e6972dfaa087295abc4756d3d30974a7cf14fa3e9cc38461dad519e963a binds this correct final file and all underlying evidence.

The separately retained evidence/root/RESULTS.json is the earlier historical aggregate, SHA256 a8ae0a9c339cc4a6382cc42597763960ef70c8424b9fbae5b1e4d8bd453bed04. It selects the first detached invocation, connected001, one pass in20.78s. Its temporary pytest906 fixture was not preserved; it is not the raw fixture copied into the final capsule. The copied69-file fixture belongs to connected002 and its separate original preservation record.

This additive correction changes the filename label only. The original report, both aggregates, source134-file pin2c9dc895d0e7c6fa6f6d4df140cb9b88e1274894c8dc7213c46b4580dec68428, all tests, counts, hashes and capsule remain unchanged. Independent review identified the mismatch; no historical document or content address is replaced. Configured scientific execution and the full goal remain incomplete.
