module Minhash
{
    authentication optional;

    funcdef compute_genome_distance_for_genome(string genome_id,
				    float max_pvalue,
				    float max_distance,
				    int max_hits,
				    int include_reference,
				    int include_representative)
	returns (list<tuple<string genome_id,
		 	    float distance,
		 	    float pvalue,
		 	    string counts>>);

    funcdef compute_genome_distance_for_fasta(string ws_fasta_path,
					      float max_pvalue,
					      float max_distance,
					      int max_hits,
					      int include_reference,
					      int include_representative)
	returns (list<tuple<string genome_id,
		 float distance,
		 float pvalue,
		 string counts>>);

    funcdef compute_genome_distance_for_genome2(string genome_id,
				    float max_pvalue,
				    float max_distance,
				    int max_hits,
				    int include_reference,
				    int include_representative,
				    int bacterial,
				    int viral)
	returns (list<tuple<string genome_id,
		 	    float distance,
		 	    float pvalue,
		 	    string counts>>);

    funcdef compute_genome_distance_for_fasta2(string ws_fasta_path,
					      float max_pvalue,
					      float max_distance,
					      int max_hits,
					      int include_reference,
					      int include_representative,
					      int bacterial,
					      int viral)
	returns (list<tuple<string genome_id,
		 float distance,
		 float pvalue,
		 string counts>>);

    /*
     * Compute genome distance for the read data in the given SRA run,
     * experiment, or project accession (SRR/SRX/SRP or the DDBJ/ENA
     * equivalents DRR/DRX/DRP/ERR/ERX/ERP). The reads are downloaded via
     * p3_sra and sketched with mash before being compared to the reference
     * sketch collections.
     */
    funcdef compute_genome_distance_for_sra(string sra_id,
					      float max_pvalue,
					      float max_distance,
					      int max_hits,
					      int include_reference,
					      int include_representative)
	returns (list<tuple<string genome_id,
		 float distance,
		 float pvalue,
		 string counts>>);

    funcdef compute_genome_distance_for_sra2(string sra_id,
					      float max_pvalue,
					      float max_distance,
					      int max_hits,
					      int include_reference,
					      int include_representative,
					      int bacterial,
					      int viral)
	returns (list<tuple<string genome_id,
		 float distance,
		 float pvalue,
		 string counts>>);

};
