"""Required packaged runtime data; excludes generated records and ownership metadata."""
import hashlib
from pathlib import Path

_SHARED_ASSETS = (
    'library/literature_assay_grading_legacy_cells_v1.json',
    'library/retained_input_authority/bvbrc_appservice_schemas.json',
)
_PILOT_ASSET = 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/grading/literature_assay_grading_legacy_cells_v1.json'


def required_runtime_asset_fingerprints(*, include_pilot=False):
    """Fingerprint actual static loaders' inputs without touching saved records."""
    root = Path(__file__).parent
    paths = (*_SHARED_ASSETS, *((_PILOT_ASSET,) if include_pilot else ()))
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in paths}
