"""Original vcf received values for supplied decision information."""
from __future__ import annotations
from .molecular_provenance_display import _molecular_literal
from .decision_prompt_text import _table


def _vcf_result_text(packet, number):
    """Render retained VCF values; do not parse bytes or calculate populations."""
    value = packet["value"]
    population, header = value["population"], value["header"]
    def token(item):
        return None if item is None else "[undecodable bytes]" if item["raw_token"] is None else item["raw_token"]
    selection = value["selection"]
    parts = ["Selected molecular result " + str(number), "",
        _table(("Result property", "Retained value"), [
            ("Callable result Source", packet["source_ref"]),
            ("Declared VCF version", header["fileformat"]), ("Decoder", header["decoder"]),
            ("Header state", header["state"]), ("Capture state", population["capture_state"]),
            ("Captured byte extent (exclusive)", value["input"]["capture"]["byte_end_0based_exclusive"]),
            ("Original size if supplied", value["input"]["capture"]["original_size_bytes"]),
            ("Record population complete", population["record_population_complete"])]), "",
        "Selected original ordinals and native field keys; null selects all, [] selects none", "",
        _table(("Selection", "Supplied value"), [(key, _molecular_literal(selection[key])) for key in
            ("record_ordinals", "sample_ordinals", "info_keys", "format_keys", "offset", "limit")]), "",
        "Retained populations; record slots, ALT tokens and sample cells have separate units", "",
        _table(("Population", "Literal count or state"), [(key, population[key]) for key in
            ("total_original_record_slots", "retained_record_slots", "selected_record_slots", "returned_record_slots",
             "omitted_by_window_record_slots", "selected_alt_tokens", "returned_alt_tokens", "selected_sample_cells",
             "returned_sample_cells", "selected_observed_sample_cells", "returned_observed_sample_cells",
             "selected_genotype_slots", "returned_genotype_slots", "has_more")]), "",
        _table(("Returned record fraction", "Numerator", "Denominator", "Unit", "Missing reason"), [
            tuple(population["returned_record_fraction"][key] for key in
                ("value", "numerator", "denominator", "unit", "missing_reason"))]), "",
        "Original sample columns", "",
        _table(("Sample ordinal", "Column ordinal", "Native name"), [
            (row["sample_ordinal_0based"], row["column_ordinal_0based"], token(row["name"])) for row in header["samples"]]), "",
        "Native field definitions; units and meanings remain as declared, otherwise unknown", "",
        _table(("Definition ordinal", "Namespace", "ID", "Number", "Type", "Description", "State"), [
            tuple(row[key] for key in ("definition_ordinal_0based", "namespace", "id", "number", "type", "description", "state"))
            for row in header["definitions"]]), "",
        "Returned original records; native POS retains VCF coordinates and any telomeric sentinel", "",
        _table(("Record ordinal", "Physical line", "State", "CHROM", "POS", "ID", "REF", "ALT", "QUAL (phred)", "FILTER", "Filter state"), [
            (row["record_ordinal_0based"], row["locator"]["line_start_1based"], row["state"], row["chrom"],
             row["pos_1based"], token(row["fixed"]["id"]), row["ref"], token(row["fixed"]["alt"]),
             token(row["fixed"]["qual"]), token(row["filter"]["token"]), row["filter"]["state"])
            for row in value["records"]])]
    fields, elements, genotypes, qualifiers = [], [], [], []
    def field_rows(record, sample, namespace, field):
        identity = (record, sample, namespace, field["field_ordinal_0based"], field["key"])
        card = field["cardinality"]
        fields.append((*identity, field["declared_type"], field["declared_number"], field["state"],
            token(field["value_token"]), field["flag"], card["observed"], card["expected"], card["state"],
            card["ploidy"], card["ploidy_basis"]))
        for element in field["values"]:
            elements.append((*identity, element["value_ordinal_0based"], token(element["token"]),
                element["decoded"]["kind"], element["decoded"]["value"], element["allele_index"],
                element["genotype_index_0based"], _molecular_literal(element["genotype_allele_indices"])))
        qualifiers.extend((record, sample, field["key"], issue["code"], issue["severity"])
            for issue in field["issues"])
    for record in value["records"]:
        ordinal = record["record_ordinal_0based"]
        for field in record["info"]:
            field_rows(ordinal, None, "INFO", field)
        for sample in record["samples"]:
            sample_ordinal = sample["sample_ordinal_0based"]
            for field in sample["fields"]:
                field_rows(ordinal, sample_ordinal, "FORMAT", field)
            genotype = sample["genotype"]
            if genotype is not None:
                for allele in genotype["alleles"]:
                    genotypes.append((ordinal, sample_ordinal, token(genotype["token"]), genotype["state"],
                        genotype["ploidy"], allele["allele_ordinal_0based"], token(allele["token"]),
                        allele["allele_index"], allele["state"]))
        qualifiers.extend((ordinal, None, None, issue["code"], issue["severity"]) for issue in record["issues"])
    parts.extend(["", "Selected native fields and declared cardinalities", "",
        _table(("Record", "Sample", "Namespace", "Field ordinal", "Key", "Type", "Number", "State", "Native value",
            "Flag", "Observed elements", "Expected elements", "Cardinality state", "GT slot count", "Ploidy basis"), fields), "",
        "Retained value elements and native allele/genotype associations", "",
        _table(("Record", "Sample", "Namespace", "Field ordinal", "Key", "Value ordinal", "Native token", "Decoded kind",
            "Decoded value", "Allele index", "Genotype index", "Genotype allele indices"), elements), "",
        "Literal GT slots; slot count is retained genotype syntax", "",
        _table(("Record", "Sample", "Native GT", "State", "GT slot count", "Slot ordinal", "Native allele", "Allele index", "Allele state"), genotypes), "",
        "Record and field qualifications", "",
        _table(("Record", "Sample", "Field", "Code", "Severity"), qualifiers), "",
        "Input and header qualifications", "",
        _table(("Code", "Path", "Severity"), [(issue["code"], issue["path"], issue["severity"])
            for issue in [*value["issues"], *header["issues"]]])])
    return "\n".join(parts)


