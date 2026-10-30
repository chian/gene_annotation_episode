from gene_annotation_episode.sequence_ops import align_pair, compare_sites, inspect_sequence, translate


def test_alphabet_does_not_invent_biological_input_identity():
    observation = inspect_sequence("ACGT")
    assert observation["compatible_alphabets"] == ["dna", "protein"]
    assert observation["gc_fraction"] == 0.5


def test_code_hypotheses_produce_distinct_products_without_changing_input():
    dna = "ATGTGAGGGTAA"
    assert translate(dna, code=11)["sequence"] == "M*G*"
    assert translate(dna, code=4)["sequence"] == "MWG*"
    assert translate(dna, code=25)["sequence"] == "MGG*"
    assert dna == "ATGTGAGGGTAA"


def test_reverse_frame_coordinates_map_back_to_original_molecule():
    # Reverse-complement of the interval is CATGAAATAA; frame one gives MK*.
    observation = translate("CCCTTATTTCATGGGG", code=11, strand="-", frame=1, start=3, end=13)
    assert observation["sequence"] == "MK*"
    assert observation["translated_interval"] == [3, 12]
    assert observation["input_interval"] == [3, 13]


def test_sites_distinguish_substitution_gap_and_unexamined_region():
    reference = "MKWVTFISLLFLFSSAYSRGVFRRDTHKSEIAHRFKDLGE"
    query = reference[5:20] + "A" + reference[21:35]
    alignment = align_pair(query, reference, molecule="protein", mode="local")
    sites = compare_sites(alignment, [0, 5, 20, 39])
    assert [site["relationship"] for site in sites] == ["outside_alignment", "identical", "substituted", "outside_alignment"]
    assert sites[2]["query_residue"] == "A"
    assert sites[2]["reference_residue"] == reference[20]
    from gene_annotation_episode.biopython_pairwise_grader import grade_biopython_pairwise
    assert grade_biopython_pairwise(alignment, molecule="protein")["scores"]["query_aligned_coverage"] == 1


def test_global_gap_site_does_not_become_a_residue_substitution():
    reference = "MKWVTFISLLFLFSSAYSRGVFRRDTHKSEIAHRFKDLGE"
    query = reference[:15] + reference[16:]
    alignment = align_pair(query, reference, molecule="protein", mode="global", gap_open=-2)
    site = compare_sites(alignment, [15])[0]
    assert site["relationship"] == "gap"
    assert site["query_position"] is None
