# E336 source-pin release before339 public installation

E336 explicitly released the two public modules after its final-source runs
ended: 98 passed (393.50 s) and 15 passed (359.08 s). Its evidence and immutable
source copies are in
`../tool_graders_standard_blast_database_episode_binding_2026-10-26_336/HANDOFF_EVIDENCE_001.json`
and its corresponding sources directory. Those tests apply to the preceding
source bytes, not this later339 implementation.

E336's released hashes match339's retained before copies exactly:

- `blast_database_grader.py`: `b90dc143c78dadab206d2e536f43c6a443ce652a95e82bbb0bbdb47fadc27b01`.
- `blast_sequence_database.py`: `5542a9aff7f35b0a1828bc085891ad5992078dcea8aab4118ea23eb13809978a`.

339 compared both original files with its before copies before installing the
candidate changes. The exact installed hashes are in `installed.sha256`.
