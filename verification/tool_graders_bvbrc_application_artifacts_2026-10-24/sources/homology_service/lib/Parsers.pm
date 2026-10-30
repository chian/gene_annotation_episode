package Parsers;
use strict;
use Log::Message::Simple;
my $verbose = 1;



### Adapters
sub parse_gene_calls {
  my ($defline, $gene_caller) = @_;
  
  if ($gene_caller =~ /prodigal/i) {
    return parse_glimmer_protein($defline);
  }

  else {
    die "undefined gene caller: $gene_caller";
  }
}

sub parse_assembly {
  my ($defline, $assembler) = @_;

  if ($assembler =~ /megahit/i) {
    return parse_megahit_assembly($_);
  }

  else {
    die "undefined assembler: $assembler";
  }
}


### Actual Parsers

# Protein Translations

# The protein translation file consists of all the proteins from all
# the sequences in multiple FASTA format. The FASTA header begins with
# a text id consisting of the first word of the original FASTA
# sequence header followed by an underscore followed by the ordinal ID
# of the protein. This text id is not guaranteed to be unique (it
# depends on the FASTA headers supplied by the user), which is why we
# recommend using the "ID" field in the final semicolon-delimited
# string instead.

# An example header for the 4th protein in the E. coli genome with id
# NC_000913:

# >NC_000913_4 # 3734 # 5020 # 1 #
# >ID=1_4;partial=00;start_type=ATG;rbs_motif=GGA/GAG/AGG;rbs_spacer=5-10bp;gc_cont=0.528

# The next three fields in the header, delimited by "#" signs, are the
# leftmost coordinate in the genome, the rightmost coordinate, and the
# strand (1 for forward strand genes, -1 for reverse strand genes).
# Following the coordinate information is a semicolon-delimited string
# identical to the one described in the gene coordinates file (see the
# list there for field definitions), using only the following fields:
# ID, partial, start_type, stop_type, rbs_motif, rbs_spacer, gc_cont,
# and gc_skew, and conf. The header does not contain any of the
# scoring information about that gene except for the conf field.

sub parse_glimmer_protein {
  my $defline = shift;
 
  my($cid,$left,$right,$strand,$gene_info) = split /\#/, $defline;
  map s/^\s+//, ($cid,$left,$right,$strand,$gene_info);
  map s/\s+$//, ($cid,$left,$right,$strand,$gene_info);
  map s/^>//, ($cid);
  map s/_\d+$//, ($cid);

  # extra for future use if needed
  my($pdgl_id,$partial,$start_type,$stop_type,$rbs_motif,$rbs_spacer,$gc_cont,$gc_skew) = split /\;/, $gene_info;
  map s/^\s+//, ($pdgl_id,$partial,$start_type,$stop_type,$rbs_motif,$rbs_spacer,$gc_cont,$gc_skew);
  map s/\s+$//, ($pdgl_id,$partial,$start_type,$stop_type,$rbs_motif,$rbs_spacer,$gc_cont,$gc_skew);
  
  return  {cid => $cid, left => $left, right => $right,
	   strand => $strand, gene_info => $gene_info};

} 

sub parse_megahit_assembly {
  my $defline = shift or die "no defline provided";
  my($id, $cov, $len);

  # look at the id
  $id = $1 if />(\S+)/;
  $id = $1 if />(\S+)_length/;
  die "could not parse id" unless $id;
  # look at coverage
  $cov = $1 if /multi=([\d\.]+)/;
  $cov = $1 if /multi_([\d\.]+)/;
  die "could not parse coverage" unless $cov;
  # look at length
  $len = $1 if /len=(\d+)/;
  $len = $1 if /length_(\d+)/;
  die "could not parse length" unless $len;

  return {'contig_id' => $id, 'coverage' => $cov, 'length' => $len};
}

1; 
