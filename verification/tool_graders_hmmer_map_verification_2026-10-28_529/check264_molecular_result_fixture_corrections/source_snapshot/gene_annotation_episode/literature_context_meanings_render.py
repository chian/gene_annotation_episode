"""Pure scientific presentation of received A108 requirement and route meanings."""
from collections.abc import Mapping


def render_meanings(parts, content, records, *, section, table, regions):
    requirements = content.get("requirement_definitions")
    if not isinstance(requirements, (tuple, list)) or not any(
            isinstance(row, Mapping) and "requirement_ref" in row for row in requirements):
        return False
    records = records or {}
    def label(reference):
        if reference is None:
            return "unknown"
        record = records.get(reference)
        if not isinstance(record, Mapping):
            return "meaning unavailable in the received scientific records"
        return record.get("label", record.get("name", "unknown"))
    requirement_names = {row["requirement_ref"]: "Requirement " + str(index + 1)
                         for index, row in enumerate(requirements)}
    section(parts, "Context operating requirements", table(
        ("Requirement", "Source-supported definition", "Entity or substance", "Property",
         "Biological setting", "Function relationship", "Unit basis", "Supported domain", "Incompatible domain"),
        ((requirement_names[row["requirement_ref"]],
          label(row["requirement_ref"]) if row.get("definition_reported") else "unknown",
          label(row.get("entity_ref")), label(row.get("property_ref")),
          label(row.get("biological_setting_ref")), label(row.get("function_relation_ref")),
          row.get("unit"), regions(row, "supported"), regions(row, "incompatible")) for row in requirements)))
    routes = content.get("route_definitions")
    if isinstance(routes, (tuple, list)):
        section(parts, "Alternative biological routes", table(
            ("Route", "Source-supported definition", "Required predicates", "Biological setting",
             "Function relationship", "Requirement set complete", "Joint operating support",
             "Membership source support", "Joint-scope source support"),
            (("Route " + str(index + 1), label(row.get("route_ref")) if row.get("definition_reported") else "unknown",
              ", ".join(requirement_names.get(ref, "unknown requirement") for ref in row.get("requirement_refs", ())) or "none declared",
              label(row.get("biological_setting_ref")), label(row.get("function_relation_ref")),
              row.get("requirements_complete"), row.get("joint_support"),
              label(row.get("membership_evidence_ref")), label(row.get("joint_scope_evidence_ref")))
             for index, row in enumerate(routes))))
    return True
