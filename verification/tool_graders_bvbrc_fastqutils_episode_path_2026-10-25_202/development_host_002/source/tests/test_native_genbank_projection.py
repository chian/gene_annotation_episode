"""Native representation and framing checks, not biological truth fixtures."""

import hashlib
import io
import json
from pathlib import Path

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqFeature import (
    AfterPosition,
    BeforePosition,
    BetweenPosition,
    CompoundLocation,
    ExactPosition,
    OneOfPosition,
    Reference,
    SeqFeature,
    SimpleLocation,
    UncertainPosition,
    UnknownPosition,
    WithinPosition,
)
from Bio.SeqRecord import SeqRecord
import pytest

from gene_annotation_episode.genbank_intake import (
    native_feature,
    native_record,
    native_value,
    records,
)


ACQUISITION = Path(__file__).resolve().parents[1] / "validation" / "acquisition"
SAVED_SHA256 = "e66323c92131da93a727aac08194f2dbf79c2b593779511387cfdbf064019105"


def genbank(*, identifier="NATIVEFIXTURE.1", sequence="ACGTACGTACGT", description=None):
    record = SeqRecord(
        Seq(sequence),
        id=identifier,
        name=identifier.split(".")[0],
        description=description or "synthetic native representation fixture",
    )
    record.annotations["molecule_type"] = "DNA"
    output = io.StringIO()
    SeqIO.write(record, output, "genbank")
    return output.getvalue().encode("utf-8")


def events(body):
    return list(records(io.BytesIO(body), molecule="dna", name="fixture"))


def native_entries(result, kind):
    return [event["native_entry"] for event in result if event.get("entry_kind") == kind]


def errors(result):
    return [event["error"] for event in result if "error" in event]


@pytest.mark.parametrize(
    "position,expected",
    [
        (ExactPosition(3), {"class": "ExactPosition", "nominal": 3, "text": "3", "attributes": {}}),
        (BeforePosition(3), {"class": "BeforePosition", "nominal": 3, "text": "<3", "attributes": {}}),
        (AfterPosition(3), {"class": "AfterPosition", "nominal": 3, "text": ">3", "attributes": {}}),
        (WithinPosition(3, 3, 5), {
            "class": "WithinPosition", "nominal": 3, "text": "(3.5)",
            "attributes": {"_left": 3, "_right": 5},
        }),
        (BetweenPosition(5, 3, 5), {
            "class": "BetweenPosition", "nominal": 5, "text": "(3^5)",
            "attributes": {"_left": 3, "_right": 5},
        }),
        (OneOfPosition(3, [ExactPosition(3), ExactPosition(5)]), {
            "class": "OneOfPosition", "nominal": 3, "text": "one-of(3,5)",
            "attributes": {"position_choices": [
                {"class": "ExactPosition", "nominal": 3, "text": "3", "attributes": {}},
                {"class": "ExactPosition", "nominal": 5, "text": "5", "attributes": {}},
            ]},
        }),
        (UnknownPosition(), {
            "class": "UnknownPosition", "nominal": None, "text": "UnknownPosition()", "attributes": {},
        }),
        (UncertainPosition(3), {
            "class": "UncertainPosition", "nominal": 3, "text": "3", "attributes": {},
        }),
    ],
    ids=["exact", "before", "after", "within", "between", "one_of", "unknown", "uncertain"],
)
def test_actual_position_classes_survive_json_without_becoming_plain_integers(position, expected):
    # json.dumps(position) silently writes only an integer for fuzzy int subclasses.
    actual = native_value({"position": position})
    assert json.loads(json.dumps(actual, allow_nan=False))["position"] == expected


def test_record_preserves_every_reference_field_and_nested_native_metadata():
    reference = Reference()
    reference.location = [SimpleLocation(0, 3), SimpleLocation(6, 12)]
    reference.authors = "Fixture author"
    reference.consrtm = "Fixture consortium"
    reference.title = "Synthetic reference metadata"
    reference.journal = "Fixture journal"
    reference.medline_id = "fixture-medline"
    reference.pubmed_id = "fixture-pubmed"
    reference.comment = "reference-local comment"
    record = SeqRecord(Seq("ACGTACGTACGT"), id="NATIVEFIXTURE.1", name="NATIVEFIXTURE",
                       description="synthetic metadata fixture", dbxrefs=["FixtureDB:1"])
    record.annotations = {
        "molecule_type": "DNA",
        "references": [reference],
        "structured_comment": {"Fixture-Data": {"Method": "native π metadata"}},
        "comment": "record comment\nsecond line",
    }
    record.letter_annotations = {"mask": tuple(range(12)), "labels": "abcdefghijkl"}
    record.features = [SeqFeature(SimpleLocation(0, 3), type="misc_feature")]
    actual = json.loads(json.dumps(native_record(record), allow_nan=False))
    assert actual["id"] == "NATIVEFIXTURE.1"
    assert actual["name"] == "NATIVEFIXTURE"
    assert actual["dbxrefs"] == ["FixtureDB:1"]
    assert actual["feature_count"] == 1
    saved = actual["annotations"]["references"][0]
    assert saved["class"] == "Reference"
    assert set(saved["attributes"]) == set(vars(reference))
    for key in ("authors", "consrtm", "title", "journal", "medline_id", "pubmed_id", "comment"):
        assert saved["attributes"][key] == getattr(reference, key)
    assert [(part["start"]["nominal"], part["end"]["nominal"])
            for part in saved["attributes"]["location"]] == [(0, 3), (6, 12)]
    assert actual["annotations"]["structured_comment"] == record.annotations["structured_comment"]
    assert actual["annotations"]["comment"] == record.annotations["comment"]
    assert actual["letter_annotations"] == {
        "mask": {"class": "tuple", "items": list(range(12))}, "labels": "abcdefghijkl",
    }


def test_feature_retains_order_remote_database_and_mixed_or_unlocated_strands():
    feature = SeqFeature(
        CompoundLocation([
            SimpleLocation(BeforePosition(8), AfterPosition(12), strand=-1, ref="REMOTE.2", ref_db="FixtureDB"),
            SimpleLocation(1, 3, strand=1),
        ], operator="order"),
        id="fixture-native-feature", type="misc_feature",
        qualifiers={"note": ["first", "second"], "transl_except": ["(pos:9..11,aa:Sec)"]},
    )
    actual = json.loads(json.dumps(native_feature(feature, 7), allow_nan=False))
    assert actual["native_feature_index"] == 7
    assert actual["id"] == "fixture-native-feature"
    assert actual["type"] == "misc_feature"
    assert actual["qualifiers"] == feature.qualifiers
    location = actual["location"]
    assert location["class"] == "CompoundLocation"
    assert location["operator"] == "order"
    assert location["strand"] is None
    assert [part["strand"] for part in location["parts"]] == [-1, 1]
    assert [part["start"]["nominal"] for part in location["parts"]] == [8, 1]
    assert location["parts"][0]["ref"] == "REMOTE.2"
    assert location["parts"][0]["ref_db"] == "FixtureDB"
    assert location["parts"][0]["start"]["class"] == "BeforePosition"
    assert location["parts"][0]["end"]["class"] == "AfterPosition"
    # Strand 0 and None have distinct native meanings; neither becomes a sign string.
    for strand in (0, None):
        uncertain = SeqFeature(SimpleLocation(UnknownPosition(), 8, strand=strand), type="misc_feature")
        saved = native_feature(uncertain, 0)["location"]
        assert saved["strand"] == strand
        assert saved["start"]["class"] == "UnknownPosition"
    assert native_feature(SeqFeature(None, type="misc_feature", qualifiers={"note": ["unlocated"]}), 0)["location"] is None


@pytest.mark.parametrize(
    "sequence,expected",
    [
        (Seq("NNNN"), {"length": 4, "defined": True, "defined_ranges": [[0, 4]]}),
        (Seq(None, 12), {"length": 12, "defined": False, "defined_ranges": [], "defined_fragments": []}),
        (Seq({3: "ACGT", 8: "TA"}, 12), {
            "length": 12, "defined": False, "defined_ranges": [[3, 7], [8, 10]],
            "defined_fragments": [{"start": 3, "end": 7, "sequence": "ACGT"},
                                  {"start": 8, "end": 10, "sequence": "TA"}],
        }),
        (Seq(None, 0), {"length": 0, "defined": True, "defined_ranges": []}),
    ],
    ids=["ambiguous_defined", "undefined", "partially_defined_class_fixture", "empty_defined"],
)
def test_sequence_metadata_preserves_known_fragments_without_inventing_unknown_bases(sequence, expected):
    # Partially defined Seq is a direct installed-class fixture; native GenBank
    # record_end currently returns either a fully defined or an undefined Seq.
    assert native_record(SeqRecord(sequence))["sequence"] == expected


def test_contig_record_keeps_native_assembly_string_and_metadata_without_sequence_projection():
    body = genbank()
    contig = "join(REMOTE.1:1..5,gap(2),REMOTE.2:1..5)"
    body = body[:body.index(b"ORIGIN")] + f"CONTIG      {contig}\n//\n".encode()
    result = events(body)
    entry = native_entries(result, "record")[0]
    assert entry["parse_failure"] is None
    assert entry["parser_warnings"] == []
    assert entry["record"]["annotations"]["contig"] == contig
    assert entry["record"]["sequence"] == {
        "length": 12, "defined": False, "defined_ranges": [], "defined_fragments": [],
    }
    assert not any("record" in event for event in result)
    assert [error["code"] for error in errors(result)] == ["genbank_record_sequence_unavailable"]


def test_missing_terminator_cannot_consume_next_locus_and_frame_offsets_count_utf8_bytes():
    first = genbank(identifier="FIRST.1", sequence="ACGT", description="synthetic π source")
    first = first[:first.rindex(b"//")]
    second = genbank(identifier="SECOND.1", sequence="TGCA")
    body = first + second
    result = events(body)
    entries = native_entries(result, "record")
    assert [entry["record"]["id"] for entry in entries] == ["FIRST.1", "SECOND.1"]
    assert [entry["record"]["sequence"]["length"] for entry in entries] == [4, 4]
    assert entries[0]["source_frame"] == {
        "start": 0, "end": len(first), "terminated": False,
        "coordinate_system": "parsed_input_source_byte_offsets",
    }
    assert entries[1]["source_frame"] == {
        "start": len(first), "end": len(body), "terminated": True,
        "coordinate_system": "parsed_input_source_byte_offsets",
    }
    assert len(first) > len(first.decode("utf-8"))
    assert entries[0]["parser_warnings"] == [{
        "category": "BiopythonParserWarning", "message": "Premature end of file in sequence data",
    }]
    assert entries[1]["parser_warnings"] == []
    sequence_rows = [event["record"] for event in result if "record" in event]
    assert [(row["name"], row["sequence"], row["source_byte_offset"]) for row in sequence_rows] == [
        ("FIRST.1", "ACGT", 0), ("SECOND.1", "TGCA", len(first)),
    ]
    assert {error["code"] for error in errors(result)} == {
        "genbank_native_parser_warning", "genbank_record_terminator_missing",
    }
    assert all(error["ordinal"] == 0 for error in errors(result))


def test_failed_frame_and_unframed_content_do_not_erase_later_valid_native_record():
    junk = b"unframed supplied bytes\n"
    broken = b"LOCUS       BROKEN\n//\n"
    valid = genbank(identifier="SURVIVES.1", sequence="ACGT")
    body = junk + broken + valid
    result = events(body)
    entries = native_entries(result, "record")
    assert len(entries) == 2
    assert entries[0]["record"] is None
    assert entries[0]["parse_failure"]["class"] == "ValueError"
    assert entries[0]["source_frame"]["start"] == len(junk)
    assert entries[0]["source_frame"]["end"] == len(junk + broken)
    assert entries[1]["record"]["id"] == "SURVIVES.1"
    assert [event["record"]["name"] for event in result if "record" in event] == ["SURVIVES.1"]
    codes = [error["code"] for error in errors(result)]
    assert "genbank_content_outside_record" in codes
    assert "genbank_record_parse_failed" in codes


def test_unterminated_origin_without_sequence_is_a_native_parse_failure_not_an_empty_success():
    body = genbank()
    body = body[:body.index(b"ORIGIN")] + b"ORIGIN\n"
    result = events(body)
    entry = native_entries(result, "record")[0]
    assert entry["record"] is None
    assert entry["parse_failure"] == {"class": "ValueError", "message": "Premature end of file"}
    assert not any("record" in event for event in result)
    assert {error["code"] for error in errors(result)} == {
        "genbank_record_terminator_missing", "genbank_record_parse_failed",
    }


def test_malformed_native_location_warns_but_retains_actual_feature_and_qualifiers():
    body = genbank().replace(
        b"FEATURES             Location/Qualifiers\n",
        b"FEATURES             Location/Qualifiers\n"
        b"     misc_feature    bogus\n"
        b"                     /note=\"native qualifier survives\"\n"
        b"                     /transl_except=(pos:1..3,aa:Sec)\n",
    )
    result = events(body)
    entry = native_entries(result, "record")[0]
    assert entry["record"]["feature_count"] == 1
    assert entry["parse_failure"] is None
    assert entry["parser_warnings"] == [{
        "category": "BiopythonParserWarning",
        "message": "Could not parse feature location 'bogus'; setting feature location to None.",
    }]
    saved = native_entries(result, "feature")[0]["feature"]
    assert saved["location"] is None
    assert saved["qualifiers"] == {
        "note": ["native qualifier survives"], "transl_except": ["(pos:1..3,aa:Sec)"],
    }
    frame = entry["source_frame"]
    assert body[frame["start"]:frame["end"]] == body
    assert b"misc_feature    bogus" in body[frame["start"]:frame["end"]]
    assert [error["code"] for error in errors(result)] == ["genbank_native_parser_warning"]
    assert len([event for event in result if "record" in event]) == 1


def test_indented_slash_slash_inside_quoted_qualifier_is_not_a_record_terminator():
    body = genbank().replace(
        b"FEATURES             Location/Qualifiers\n",
        b"FEATURES             Location/Qualifiers\n"
        b"     misc_feature    1..3\n"
        b"                     /note=\"leading\n"
        b"                     //\n"
        b"                     trailing\"\n",
    )
    # This literal continuation is accepted by the installed native parser.
    native = SeqIO.read(io.StringIO(body.decode("utf-8")), "genbank")
    assert native.features[0].qualifiers == {"note": ["leading // trailing"]}
    result = events(body)
    assert errors(result) == []
    entry = native_entries(result, "record")[0]
    assert entry["parse_failure"] is None
    assert entry["source_frame"]["end"] == len(body)
    assert native_entries(result, "feature")[0]["feature"]["qualifiers"] == native.features[0].qualifiers
    assert len([event for event in result if "record" in event]) == 1


def test_native_compound_order_and_qualifier_normalization_are_described_as_parser_outputs():
    body = genbank().replace(
        b"FEATURES             Location/Qualifiers\n",
        b"FEATURES             Location/Qualifiers\n"
        b"     CDS             complement(join(<1..3,REMOTE.2:7..>9))\n"
        b"                     /transl_except=(pos:complement(1..3),aa:Sec)\n"
        b"                     /transl_except=(pos:complement(7..9),aa:TERM)\n"
        b"                     /pseudo\n"
        b"                     /pseudo\n"
        b"                     /note=\"one\n"
        b"                     two\"\n"
        b"                     /translation=\"M K\n"
        b"                     L\"\n"
        b"     misc_feature    3^4\n",
    )
    result = events(body)
    assert errors(result) == []
    features = [entry["feature"] for entry in native_entries(result, "feature")]
    location = features[0]["location"]
    assert location["operator"] == "join"
    assert location["strand"] == -1
    assert [part["start"]["nominal"] for part in location["parts"]] == [6, 0]
    assert [part["ref"] for part in location["parts"]] == ["REMOTE.2", None]
    assert location["parts"][0]["end"]["class"] == "AfterPosition"
    assert location["parts"][1]["start"]["class"] == "BeforePosition"
    assert features[0]["qualifiers"] == {
        "transl_except": ["(pos:complement(1..3),aa:Sec)", "(pos:complement(7..9),aa:TERM)"],
        "pseudo": [""], "note": ["one two"], "translation": ["MKL"],
    }
    between = features[1]["location"]
    assert between["start"]["nominal"] == between["end"]["nominal"] == 3
    assert between["start"]["class"] == between["end"]["class"] == "ExactPosition"


def test_saved_acquisition_fixture_matches_original_custody_and_native_annotation_counts():
    body = (ACQUISITION / "AJ320226.1.genbank").read_bytes()
    provenance = json.loads((ACQUISITION / "acquisition-provenance.json").read_text())
    assert len(body) == 4368
    assert hashlib.sha256(body).hexdigest() == SAVED_SHA256
    assert provenance["raw_artifact"]["sha256"] == SAVED_SHA256
    assert provenance["source"]["id"] == "source_1180b2f3afd5b7d32000e699"
    assert provenance["request"]["request"] == {
        "db": "nuccore", "id": "AJ320226", "retmode": "text", "rettype": "gbwithparts",
        "tool": "gene-annotation-episode",
    }
    result = events(body)
    assert errors(result) == []
    entry = native_entries(result, "record")[0]
    native = entry["record"]
    assert native["id"] == "AJ320226.1"
    assert native["sequence"] == {"length": 1489, "defined": True, "defined_ranges": [[0, 1489]]}
    assert native["feature_count"] == 4
    assert len(native["annotations"]["references"]) == 2
    assert native["annotations"]["references"][0]["attributes"]["pubmed_id"] == "11773048"
    reference_location = native["annotations"]["references"][1]["attributes"]["location"][0]
    assert (reference_location["start"]["nominal"], reference_location["end"]["nominal"]) == (0, 1489)
    features = [row["feature"] for row in native_entries(result, "feature")]
    assert [feature["type"] for feature in features] == ["source", "gene", "CDS", "sig_peptide"]
    assert sum("experiment" in feature["qualifiers"] for feature in features) == 2
    assert all(row["meaning"] == "native_supplied_source_assertions_not_current_target_annotations"
               for row in [entry, *native_entries(result, "feature")])
    # These are preserved source claims, not performed experiments or current assignments.
    assert len([event for event in result if "record" in event]) == 1
