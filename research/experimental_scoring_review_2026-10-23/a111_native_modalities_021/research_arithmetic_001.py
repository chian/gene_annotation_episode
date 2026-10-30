"""Bounded research arithmetic, not a production A111 reader or scorer.

Uses only the four retained deposits and explicitly synthetic operands below.
Run from any directory: python3 /absolute/path/to/this/file.py
"""
from pathlib import Path
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / "sources"
CHECKS = []


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def near(name, actual, expected, tolerance=1e-12):
    check(name, math.isclose(actual, expected, rel_tol=tolerance, abs_tol=tolerance))


def mean(values):
    if not values:
        raise ValueError("invalid_denominator")
    return sum(values) / len(values)


def q_index(values):
    if not values:
        raise ValueError("invalid_denominator")
    for value in values:
        if value is not None and (not math.isfinite(value) or not -1 <= value <= 1):
            raise ValueError("invalid_range")
    known = [max(0, value) ** 2 for value in values if value is not None]
    if len(known) != len(values):
        return {"value": None, "lower": 0, "upper": min(known) if known else 1}
    result = min(known)
    return {"value": result, "lower": result, "upper": result}


def violation(distance, lower, upper):
    if not 0 <= lower <= upper or not math.isfinite(distance) or distance < 0:
        raise ValueError("invalid_range")
    return max(0, lower - distance, distance - upper)


def restraint_index(violations, tau=0.5):
    if not violations or not math.isfinite(tau) or tau <= 0:
        raise ValueError("invalid_denominator_or_scale")
    if any(v is not None and (not math.isfinite(v) or v < 0) for v in violations):
        raise ValueError("invalid_range")
    cells = [None if v is None else math.exp(-v * v / (2 * tau * tau)) for v in violations]
    lower = sum(v for v in cells if v is not None) / len(cells)
    upper = (sum(v for v in cells if v is not None) + cells.count(None)) / len(cells)
    return {"value": lower if None not in cells else None, "lower": lower, "upper": upper,
            "restraint_scores": cells, "fixed_restraint_count": len(cells), "tau_A": tau}


def atoms(path):
    selected = {}
    model = 1
    for line in path.read_text().splitlines():
        if line.startswith("MODEL"):
            model = int(line[10:14])
        if line.startswith(("ATOM  ", "HETATM")):
            key = (model, line[21], int(line[22:26]), line[26].strip(),
                   line[12:16].strip(), line[16].strip())
            if key in selected:
                raise ValueError("duplicate atom reference")
            selected[key] = tuple(float(line[start:start + 8]) for start in (30, 38, 46))
    return selected


def distance(selected, model, a_chain, a_residue, a_name, b_chain, b_residue, b_name):
    a = selected[(model, a_chain, a_residue, "", a_name, "")]
    b = selected[(model, b_chain, b_residue, "", b_name, "")]
    return math.dist(a, b)


def selected_restraint(path, line_number, expected_atoms):
    line = path.read_text().splitlines()[line_number - 1]
    match = re.fullmatch(
        r"assign\s+\(resid\s+(\d+)\s+and name\s+(\S+)\s*\)\s*"
        r"\(resid\s+(\d+)\s+and name\s+(\S+)\s*\)\s*"
        r"([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*", line)
    check(f"{path.name}:{line_number} parsed exact selected assignment", match is not None)
    a_res, a_name, b_res, b_name, target, lower_dev, upper_dev = match.groups()
    check(f"{path.name}:{line_number} atom identity",
          (int(a_res), a_name, int(b_res), b_name) == expected_atoms)
    target, lower_dev, upper_dev = map(float, (target, lower_dev, upper_dev))
    return {"source_file": path.name, "source_line": line_number, "native_line": line,
            "target_A": target, "lower_deviation_A": lower_dev, "upper_deviation_A": upper_dev,
            "lower_A": target - lower_dev, "upper_A": target + upper_dev}


def cryoem_native():
    rows = []
    for pdb, pairs, expected_mean in (
        ("3j5q", [("D", "E"), ("B", "G")], .1440505),
        ("3j5r", [("B", "C"), ("A", "D")], .106397),
    ):
        xml = ET.parse(SOURCES / f"{pdb}_validation.xml").getroot()
        coordinate = atoms(SOURCES / f"{pdb}.pdb")
        q_by_chain = {}
        for element in xml.iter("ModelledSubgroup"):
            a = element.attrib
            if a.get("resnum") == "643" and a.get("model") == "1":
                q_by_chain[a["chain"]] = float(a["Q_score"])
        copies = []
        for a, b in pairs:
            q_values = [q_by_chain[a], q_by_chain[b]]
            d = distance(coordinate, 1, a, 643, "O", b, 643, "O")
            copies.append({"author_chains": [a, b], "O_O_distance_A": d,
                           "Q_score_by_endpoint": q_values, "D": q_index(q_values)["value"],
                           "supports_ge_6_A": int(d >= 6)})
        d_mean = mean([c["D"] for c in copies])
        near(f"{pdb} copy-mean local Q index", d_mean, expected_mean)
        check(f"{pdb} all selected copies agree in event direction",
              len({c["supports_ge_6_A"] for c in copies}) == 1)
        rows.append({"pdb": pdb, "copies": copies, "copy_mean_D": d_mean,
                     "q_C_I": [1, 1, 1], "T": None,
                     "source_target_point": None,
                     "source_target_signed_bounds": [0, d_mean] if pdb == "3j5q" else [-d_mean, 0],
                     "point_scope": "conditional_model_calculation"})
    return rows


def nmr_native():
    rows = []
    for pdb, model, cross_res, internal_line, cross_line in (
        ("2n9z", 9, 28, 186, 569), ("2naj", 3, 26, 211, 39),
    ):
        xml = ET.parse(SOURCES / f"{pdb}.xml").getroot()
        entry = xml.find("Entry")
        check(f"{pdb} retained medoid", int(entry.attrib["medoid_model"]) == model)
        restraints = [
            selected_restraint(SOURCES / f"{pdb}.mr", internal_line, (11, "HA", 11, "HD1")),
            selected_restraint(SOURCES / f"{pdb}.mr", cross_line, (11, "HE1", cross_res, "HA")),
        ]
        coordinate = atoms(SOURCES / f"{pdb}.pdb")
        model_numbers = sorted({key[0] for key in coordinate})
        check(f"{pdb} exactly twenty deposited scenarios", model_numbers == list(range(1, 21)))
        scenarios = []
        for m in model_numbers:
            distances = [distance(coordinate, m, "A", 11, "HA", "A", 11, "HD1"),
                         distance(coordinate, m, "A", 11, "HE1", "A", cross_res, "HA")]
            violations = [violation(d, r["lower_A"], r["upper_A"])
                          for d, r in zip(distances, restraints)]
            d_index = restraint_index(violations)["value"]
            geometry = int(distances[1] <= 4)
            scenarios.append({"model": m, "distances_A": distances, "violations_A": violations,
                              "D": d_index, "G_crossloop_le_4_A": geometry,
                              "conditional_source_D_times_G": d_index * geometry})
        rep = next(s for s in scenarios if s["model"] == model)
        check(f"{pdb} representative geometry", rep["G_crossloop_le_4_A"] == 1)
        check(f"{pdb} ensemble straddles G boundary",
              {s["G_crossloop_le_4_A"] for s in scenarios} == {0, 1})
        rows.append({"pdb": pdb, "restraints": restraints, "representative_model": model,
                     "representative": rep, "scenarios": scenarios,
                     "D_ensemble_range": [min(s["D"] for s in scenarios), max(s["D"] for s in scenarios)],
                     "joint_D_G_range": [min(s["conditional_source_D_times_G"] for s in scenarios),
                                        max(s["conditional_source_D_times_G"] for s in scenarios)],
                     "T": None, "target_point": None,
                     "conditional_representative_target_bounds": [0, rep["D"]],
                     "experimental_dataset_count": 1, "model_scenario_count": 20})
    near("K1 medoid D", rows[0]["representative"]["D"], 1)
    near("K2 medoid D", rows[1]["representative"]["D"], .8986676009902625)
    return rows


def signed_reducer(cluster_signed_values):
    # Each entry already represents one unique canonical dataset/state after copy reduction.
    p = mean([mean([max(v, 0) for v in cluster]) for cluster in cluster_signed_values])
    o = mean([mean([max(-v, 0) for v in cluster]) for cluster in cluster_signed_values])
    return {"P": p, "O": o, "Z": p-o, "A": max(0, p-o),
            "cluster_count": len(cluster_signed_values), "alpha": 1, "beta": 1}


def synthetic_examples():
    # All measurements in this function are synthetic, not values from either paper.
    c = math.exp(-.5 ** 2 / (2 * 1 ** 2)) ** .5  # pH plus identical temperature
    shared = {"q": 60/80, "T": 3/4, "C": c, "I": 1-12/60}
    em_copies = []
    for qs, geometric in [([.80, .90], [2.8, 3.0, 3.2, 4.2]),
                          ([.70, .95], [2.8, 3.0, 3.2, 3.4])]:
        g = mean([int(2.5 <= d <= 3.5) for d in geometric])
        d = q_index(qs)["value"]
        w = math.prod([shared["q"], d, g, shared["T"], c, shared["I"]])
        em_copies.append({"Q": qs, "G_distances_A": geometric, "D": d, "G": g, "w": w})
    em_support = mean([copy["w"] for copy in em_copies])
    em_opposing = .5 * q_index([.6, .9])["value"] * 1 * .75 * 1 * 1
    em = {"scope": "synthetic", "shared_support_operands": shared, "support_copies": em_copies,
          "support_dataset_w": em_support, "opposing_operands": {
              "q": .5, "Q": [.6, .9], "D": .36, "G": 1, "T": .75, "C": 1, "I": 1},
          "opposing_dataset_w": em_opposing,
          "reducer": signed_reducer([[em_support], [-em_opposing]])}
    # A duplicate paper/rendering is the same observation and is not a new cluster.
    near("EM copy mean is applied to full products", em_support,
         mean([.75*.64*.75*.75*c*.8, .75*.49*1*.75*c*.8]))
    near("EM opposing chain", em_opposing, .135)

    nm_support_d = restraint_index([0, .5])["value"]
    nm_opp_d = restraint_index([.25, .75])["value"]
    nm_support = 1 * nm_support_d * .5 * (2/3) * 1 * 1
    nm_opp = 1 * nm_opp_d * 1 * (2/3) * 1 * 1
    nmr = {"scope": "synthetic_conditional_model", "q": 1, "C": 1, "I": 1, "T": 2/3,
           "tau_A": .5,
           "support": {"bounds_A": [[0, 4], [0, 5]], "distances_A": [4, 5.5],
                       "violations_A": [0, .5], "D": nm_support_d, "G": .5, "w": nm_support},
           "opposition": {"bounds_A": [[0, 5], [0, 6]], "distances_A": [5.25, 6.75],
                          "violations_A": [.25, .75], "D": nm_opp_d, "G": 1, "w": nm_opp},
           "reducer": signed_reducer([[nm_support], [-nm_opp]])}
    near("NMR support chain", nm_support, (1+math.exp(-.5))/6)
    near("NMR opposition chain", nm_opp, (math.exp(-.125)+math.exp(-1.125))/3)
    check("NMR signed opposition preserved when A is zero", nmr["reducer"]["Z"] < 0 and nmr["reducer"]["A"] == 0)

    missing_q = q_index([.8, None])
    missing_nmr = restraint_index([.5, None])
    near("missing Q upper uses known weaker endpoint", missing_q["upper"], .64)
    check("missing Q remains null", missing_q["value"] is None and missing_q["lower"] == 0)
    near("missing NMR restraint retains fixed lower denominator", missing_nmr["lower"], math.exp(-.5)/2)
    near("missing NMR restraint retains fixed upper denominator", missing_nmr["upper"], (math.exp(-.5)+1)/2)
    check("missing NMR point remains null", missing_nmr["value"] is None)
    near("negative valid local Q has proposed zero index", q_index([-.2, .8])["value"], 0)
    for invalid in [1.01, -1.01, math.nan]:
        try:
            q_index([invalid])
        except ValueError:
            CHECKS.append("invalid Q rejected: " + str(invalid))
        else:
            raise AssertionError("invalid native Q was accepted")
    for label, function in [("empty Q panel", lambda: q_index([])),
                            ("empty NMR panel", lambda: restraint_index([])),
                            ("zero NMR tolerance", lambda: restraint_index([.1], 0))]:
        try:
            function()
        except ValueError:
            CHECKS.append(label + " rejected")
        else:
            raise AssertionError(label)
    # Positive-part/same-denominator reducer behavior is preserved, not repaired here.
    diluted = signed_reducer([[em_support], [-em_opposing], [0]])
    near("zero transfer cluster dilutes original reducer", diluted["Z"], em["reducer"]["Z"]*2/3)
    # Exact defined optional group distances; selected native cases use single atoms.
    r6_mean = ((3**-6 + 10**-6)/2)**(-1/6)
    r6_sum = (3**-6 + 10**-6)**(-1/6)
    check("SUM group distance is below the shortest listed atom distance", r6_sum < 3)
    return {"cryoem": em, "nmr": nmr,
            "missingness_checks": {"Q_with_missing_endpoint": missing_q,
                                   "NMR_with_missing_restraint": missing_nmr},
            "original_reducer_zero_transfer_sensitivity": diluted,
            "group_distance_example_A": {"native_distances": [3, 10], "R_6_mean": r6_mean,
                                         "SUM_nmono_1": r6_sum}}


def main():
    results = {"status": "research_proposal_only", "cryoem_native": cryoem_native(),
               "nmr_native": nmr_native(), "synthetic": synthetic_examples()}
    results["checks"] = CHECKS
    results["checks_passed"] = len(CHECKS)
    results["source_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted(SOURCES.iterdir()) if p.is_file()}
    output = ROOT / "ARITHMETIC_RESULTS_001.json"
    output.write_text(json.dumps(results, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"checks_passed": len(CHECKS),
                      "cryoem_synthetic": results["synthetic"]["cryoem"]["reducer"],
                      "nmr_synthetic": results["synthetic"]["nmr"]["reducer"],
                      "nmr_native_representative_D": [r["representative"]["D"] for r in results["nmr_native"]],
                      "output": str(output)}, indent=2))


if __name__ == "__main__":
    main()
