ROW_FIELDS = {"model": frozenset({"kind", "record_key", "locator", "format",
    "writer_version", "model_type", "name", "accession", "description", "alphabet",
    "content_validation", "fields", "flags", "null_background", "calibration",
    "efp7gf", "filter_hmm", "topology", "source_fields"})}
FIELD_UNITS = {"CLEN": "nt", "W": "nt", "NSEQ": "count", "EFFN": "count",
    "STATES": "count", "NODES": "count", "CKSUM": "dimensionless",
    "GA": "bit", "TC": "bit", "NC": "bit"}
HMM_UNITS = {"LENG": "nt", "MAXL": "nt", "NSEQ": "count", "EFFN": "count", "CKSUM": "dimensionless"}
CALIBRATION_ALGORITHMS = {"ECMLC": "cm_local_cyk", "ECMGC": "cm_glocal_cyk",
    "ECMLI": "cm_local_inside", "ECMGI": "cm_glocal_inside"}
TOPOLOGY_FIELDS = ("base_pair_nodes", "bifurcation_nodes", "total_nodes", "total_states")

