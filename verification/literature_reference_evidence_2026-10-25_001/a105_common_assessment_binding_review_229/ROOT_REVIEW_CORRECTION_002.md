# Exact file-count correction to root review001

`ROOT_REVIEW_001.md` says24 files when describing the original root220 closed-state preservation audit. That prose count is wrong: the actual baseline and `ROOT_CLOSED_PROOF_AUDIT_001.json` contain **25 state files:24 artifacts plus state.sqlite3**. The independent script verified every file in that baseline and passed. No state, test, script, result or original baseline was altered. Read the review's two references to24 old-state files as25 total files; all other scope and limits remain unchanged.
