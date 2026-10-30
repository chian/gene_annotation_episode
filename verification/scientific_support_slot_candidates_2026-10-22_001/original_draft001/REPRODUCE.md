# Reproduce the review artifacts

Use PYTHONDONTWRITEBYTECODE=1 with /home/chia/repos/gene_annotation_episode/.venv/bin/python. Every script writes only within this /tmp directory. No active source is installed.

Run build_draft.py, build_additional_candidate.py, curate_transfer_followups.py, integrate_curation.py, validate_draft.py, then write_review_notes.py in that order. curation_system.json is the separately reviewed, immutable input from the system/physiology subtask. integrate_curation.py applies the explicitly documented OarX, Huc and XoxF source-use corrections and merges A111's separately reviewed sources. The initial build alone is not the final curated artifact.

validate_draft.py uses the existing schema validator and the public metadata-library round-trip in a temporary fixture removed on exit. It checks all original source identities and exact selected text, excerpts, pointers and URL memberships. It performs no scientific execution or score calculation. Revalidation rewrites validation.json and therefore requires resealing output_manifest.json if byte hashes are to describe that subsequent check.
