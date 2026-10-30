"""Synthetic witness-publication reproduction; no paper or model is opened."""
import hashlib
import json
from pathlib import Path

from test_literature_kinetic_storage import setup
from test_literature_kinetic_inputs import Source
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.literature_kinetic_storage import LiteratureKineticRepository

OUT = Path(__file__).resolve().parent


def main():
    results = []
    for name, literal in (("long", "Condition: " + "x" * 600),
                          ("multiline", "Condition: first line\nsecond line")):
        store, context, selection = setup(OUT / ("synthetic_" + name + "_001"), extra=literal)
        try:
            raw = store.get_artifact(store.get(selection["source_ref"])["artifact_ref"]).decode()
            witness = Source(raw).witness(literal)
            witness["source_ref"] = selection["source_ref"]
            selection["numerator"]["context"]["conditions"] = witness
            repository = LiteratureKineticRepository(store, context.run_id)
            before = list(store.db.iterdump())
            try:
                repository.populate(context, selection, "legitimate-witness")
            except ContractError as error:
                failure = {"code": str(error), "detail": error.detail}
            else:
                raise AssertionError("Expected the current display-label contract failure")
            assert list(store.db.iterdump()) == before
            assert store.db.execute("SELECT count(*) FROM literature_kinetic_operations").fetchone()[0] == 0
            results.append({"case": name, "witness_characters": len(literal),
                "failure": failure, "no_saved_population": True, "whole_sql_unchanged": True})
        finally:
            store.close()
    import gene_annotation_episode.literature_kinetic_storage as implementation
    receipt = {"synthetic_only": True,
        "kinetic_storage_sha256": hashlib.sha256(Path(implementation.__file__).read_bytes()).hexdigest(),
        "cases": results,
        "scope": "Selected source-reader/storage witness boundary only; no source science, model execution or controller observations"}
    with (OUT / "BASELINE_LABEL_FAILURES_001.json").open("x") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"synthetic_reproductions": len(results), "failures": [r["failure"] for r in results],
                      "no_saved_populations": True, "whole_sql_unchanged": True}))


if __name__ == "__main__":
    main()
