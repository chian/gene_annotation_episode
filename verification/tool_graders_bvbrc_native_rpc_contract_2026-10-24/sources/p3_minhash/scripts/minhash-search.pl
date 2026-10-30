#
# Search a minhash database for the given genome.
#
# Input is either a contigs file or a genome object. If a genome object is
# used the output will be a genome object modified with the closest genomes added
# to the close_genomes list.
#

use strict;
use GenomeTypeObject;
use Getopt::Long::Descriptive;
use File::Basename;
use Data::Dumper;

my($opt, $usage) = describe_options("%c %o reference-database [reference-database ... ] input-file",
				    ["max-pvalue|v=f", "Maximum p-value to report (0-1)", { default => 0.2 }],
				    ["max-distance|d=f", "Maximium distance to report (0-1)", { default => 1 }],
				    ["parallelism|p=i", "Parallelism", { default => 4 }],
				    ["help|h", "Show this help message"]);
print($usage->text), exit 0 if $opt->help;
die($usage->text) if @ARGV < 2;

my $input = pop;
my @refs = @ARGV;

open(I, "<", $input) or die "Cannot open input file $input: $!";

my @err;
for my $ref (@refs)
{
    if (!-s $ref)
    {
	push(@err, "Reference database $ref not found\n");
    }
}
die join("", @err) if @err;

my $type = "";

if ($input =~ /\.msh$/)
{
    $type = 'sketch';
} else {
	my $la = <I>;
	seek(I, 0, 0);
	my $hex_string = unpack "H*", substr($la, 0, 2);
	if ($hex_string eq "1f8b") { # magic constant to check for gzip compression.
		my @cmd = ("zcat", $input, "|", "head", "-n", "1");
		open(P, "-|", @cmd) or die "Cannot run @cmd: $!";
		while (<P>)
		{
			chomp;
			if ($_ =~ /^>/) {
				$type = 'fasta';
			}
		    elsif ($_ =~ /^@/) {
		    	$type = 'fastq';
		    }
		    last;
		}
	}
}

if ($type eq "")
{
    my $l1 = <I>;
    
    if ($l1 =~ /^\{/)
    {
	$type = 'gto';
    }
    elsif ($l1 =~ /^>/)
    {
	$type = 'fasta';
    }
    elsif ($l1 =~ /^@/)
    {
	$type = 'fastq';
    }
    else
    {
	die "Input file $input doesn't look like either a genome object or a fasta file\n";
    }
    seek(I, 0, 0);
}

my $gto;
my $fasta;
if ($type eq 'gto')
{
    #
    # Need to read and parse the GTO, then extract contigs to a file.
    #
    $gto = GenomeTypeObject->new({ file => $input });
    $gto or die "Could not create genome object from $input\n";
    $fasta = $gto->extract_contig_sequences_to_temp_file();
}
else
{
    $fasta = $input;
}

#
# Run mash with appropriate parameters.
#

my @opts;

if ($type eq 'fastq')
{
    push(@opts, "-r");
}

my @vals;

for my $ref (@refs)
{
    my @cmd = ("mash", "dist",
	       "-p", $opt->parallelism,
	       "-v", $opt->max_pvalue,
	       "-d", $opt->max_distance,
	       @opts,
	       $ref,
	       $fasta);
    
    open(P, "-|", @cmd) or die "Cannot run @cmd: $!";
    while (<P>)
    {
	chomp;
	my($ref_file, $me, $dist, $pv, $counts) = split(/\t/);

	my $g = genome_id_from_sketch_id($ref_file);
	if (!defined($g))
	{
	    warn "Cannot determine a genome id from sketch id '$ref_file'\n";
	    next;
	}

	my($tax, $idx) = split(/\./, $g);
	push(@vals, [$g, $tax, $idx, $dist, $pv, $counts]);
    }
}

for my $ent (sort { $a->[3] <=> $b->[3] or $a->[1] <=> $b->[1] or $a->[2] <=> $b->[2] } @vals)
{
    my($g, undef, undef,  $dist, $pv, $counts) = @$ent;
    print join("\t", $g, $dist, $pv, $counts), "\n";
}

#
# Recover the genome id from the id mash reports for a reference sketch.
#
# There are two forms in circulation, and both have to keep working:
#
#  - Sketches built before 2026-09 record the path of the fasta they were built
#    from, e.g. /vol/patric3/downloads/genomes/196024.85/196024.85.fna. All
#    889,929 sketches in the production tree, and everything pasted into
#    combined/all.msh, are this form. The viral builder produces it too, by
#    sketching out of a scratch directory deliberately named ".../tmp.$$.genomes".
#
#  - Sketches built by the current minhash-build-sketches.pl stamp the bare
#    genome id with "mash sketch -I", so their identity no longer depends on
#    where the fasta happened to live. That matters because contigs fetched from
#    the data API for genomes absent from the downloads tree have no natural
#    home under a "genomes/" path, and under the old scheme such a sketch would
#    be built, pasted, and then silently dropped here.
#
# The path form is tried first because a path contains the bare form as a
# substring. The last resort is the basename, anchored, which covers a
# per-genome file in some other layout. Returning undef makes the caller warn;
# the previous code let an unmatched id through as undef and dropped the hit
# without saying anything.
#
sub genome_id_from_sketch_id
{
    my($id) = @_;

    my($g) = $id =~ m,genomes/(\d+\.\d+),;
    return $g if defined $g;

    ($g) = $id =~ m,^(\d+\.\d+)$,;
    return $g if defined $g;

    ($g) = basename($id) =~ m,^(\d+\.\d+)(?:\.(?:msh|fna))?$,;
    return $g;
}
