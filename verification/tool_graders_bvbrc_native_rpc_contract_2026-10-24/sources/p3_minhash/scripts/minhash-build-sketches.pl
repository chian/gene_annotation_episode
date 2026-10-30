#
# Build the minhash sketches for the BV-BRC bacterial and archaeal genomes.
#
# Genome selection is driven by the data API, not by the contents of the
# downloads tree. The tree is a cache of the genome population, not the
# population itself: coverage is very uneven across the genome id range and the
# most recently loaded genomes are absent from it entirely, so a readdir-driven
# build cannot see -- and therefore cannot sketch -- the genomes it is missing.
# It has no way to report them either; the gap only showed up later, as the
# "missing" tally in minhash-create-combined-sketches.pl.
#
# So: enumerate from the API, probe the downloads tree per genome, and fetch the
# misses from the data API in batches. That is the shape
# homology_service/scripts/p3x-create-blast-db.pl uses
# (process_from_download_files + prefetch_missing_genomes), and the fetch code
# below is adapted from its contigs branch.
#
# Two deliberate differences from the blast version:
#
#  - The fetch happens inside the parallel workers rather than serially up
#    front. Blast builds one genus at a time, so its miss list is small; here a
#    single run can have a couple hundred thousand misses and a serial prefetch
#    would be the whole runtime.
#
#  - The fetched files are a persistent cache (--fetch-dir), so they are written
#    through a temp name and renamed, and a genome that returned no contigs
#    leaves no file at all. Blast keeps its empty files on purpose, because its
#    cache lives in a File::Temp dir that dies with the run; here an empty file
#    would be a permanent cache hit and the genome would never be retried.
#
# Sketch identity: mash records the path of the fasta it sketched, and
# minhash-search.pl used to recover the genome id from that path with a regex
# requiring a "genomes/<gid>" component. A sketch built from anywhere else was
# silently dropped at search time. We now stamp the id explicitly with
# "mash sketch -I <genome id>", which survives mash paste and appears verbatim
# as column 0 of mash dist. NOTE: minhash-search.pl must be deployed with the
# matching change (it accepts both the new bare id and the legacy path form)
# BEFORE sketches built by this script are published.
#

use strict;
use Data::Dumper;
use Getopt::Long::Descriptive;
use LPTScheduler;
use P3DataAPI;
use IPC::Run;
use IO::File;
use File::Path qw(make_path);
use File::Basename;
use gjoseqlib;

my($opt, $usage) = describe_options("%c %o genome-dir sketch-dir",
				    ["sketch-size|s=i" => "Sketch size", { default => 1000 }],
				    ["parallel|p=i" => "Run with this many parallel threads", { default => 1 }],
				    ["batch-size|b=i" => "Size of genome batches to process in a thread", { default => 100 }],
				    ["fetch-missing!" => "Fetch genomes with no download file from the data API. Invert with --no-fetch-missing to sketch only what is on disk, which is what this script used to do", { default => 1 }],
				    ["fetch-dir=s" => "Persistent cache directory for contigs fetched from the data API. Required unless --no-fetch-missing"],
				    ["fetch-batch-size=i" => "Number of genomes per data API contig query", { default => 10 }],
				    ["quality-check!" => "Require genome_quality:Good (invert with --no-quality-check)", { default => 1 }],
				    ["genomes-from=s" => "Restrict the run to the genome ids in this file (one per line, or the first column of a TSV -- so a --missing-list from an earlier run can be fed straight back in)"],
				    ["limit=i" => "Stop enumerating after this many genomes. For smoke tests, not for production runs"],
				    ["genome-list=s" => "Write the enumerated genome ids here"],
				    ["missing-list=s" => "Write a TSV of the genomes that still have no sketch when the run finishes"],
				    ["stale-list=s" => "Write the genome ids that have a sketch but are not in the enumerated set here"],
				    ["dry-run" => "Show the commands that would be run"],
				    ["help|h" => "Show this help message"]);
print($usage->text), exit 0 if $opt->help;
die($usage->text), exit 0 if @ARGV != 2;

my $genome_dir = shift;
my $sketch_dir = shift;

-d $genome_dir or die "Genome directory $genome_dir is not a directory\n";
-d $sketch_dir or die "Sketch directory $sketch_dir is not a directory\n";

my $fetch_dir = $opt->fetch_dir;
if ($opt->fetch_missing)
{
    $fetch_dir or die "--fetch-dir is required unless --no-fetch-missing is given\n";
    make_path($fetch_dir);
    -d $fetch_dir or die "Fetch directory $fetch_dir is not a directory\n";
}

#
# Enumerate the genomes we intend to have sketches for.
#
# These filters match the ones p3x-create-blast-db.pl applies, so the sketch
# population and the blast database population are the same set of genomes.
#
my $api = P3DataAPI->new();

my @params;
push(@params, fq => 'superkingdom:(Bacteria OR Archaea)');
push(@params, fq => 'public:true');
push(@params, fq => 'genome_quality:Good') if $opt->quality_check;
push(@params, fq => 'genome_length:*');

#
# Exclude deprecated genomes, which is what BV-BRC does site-wide -- the
# displays filter on ne(genome_status,Deprecated). This is the raw Solr spelling
# of that RQL: 53,195 of the 1,088,899 genomes the filters above select are
# deprecated, and sketching them would let the similar-genome finder return
# genomes the rest of the site does not admit exist.
#
# A negative clause also admits documents where the field is absent, which is
# the behaviour we want and matches ne(); as of 2026-09 no genome in this set
# lacks genome_status, so the two spellings agree exactly (1,035,704).
#
push(@params, fq => '-genome_status:Deprecated');
push(@params, fl => 'genome_id,genome_length');
push(@params, q => '*:*');

#
# --genomes-from restricts the run without changing the filters above, so a
# retry sketches exactly the genomes it is asked about and nothing else. The
# ids are still put through the query rather than trusted, so a genome that has
# since been withdrawn or dropped below Good is not silently resurrected.
#
my %restrict;
if ($opt->genomes_from)
{
    open(RF, "<", $opt->genomes_from) or die "Cannot open " . $opt->genomes_from . ": $!";
    while (<RF>)
    {
	$restrict{$1} = 1 if /^(\d+\.\d+)/;
    }
    close(RF);
    %restrict or die "No genome ids found in " . $opt->genomes_from . "\n";
    printf STDERR "Restricting to %d genome id(s) from %s\n", scalar keys %restrict, $opt->genomes_from;
}

print STDERR "Enumerating genomes\n";

my $genomes;
if (%restrict)
{
    #
    # Push the restriction into the query rather than enumerating the whole
    # population and filtering it. A retry list is usually small, and paging
    # through a million genomes to keep twenty of them is most of the runtime.
    # Chunked because the ids go into the query string, and quoted because a
    # genome id contains a dot.
    #
    my @ids = sort keys %restrict;
    $genomes = [];
    while (@ids)
    {
	my @chunk = splice(@ids, 0, 1000);
	my @p = (@params, fq => "genome_id:(" . join(" OR ", map { qq("$_") } @chunk) . ")");
	push(@$genomes, @{$api->solr_query_list("genome", \@p)});
    }

    my $dropped = scalar(keys %restrict) - scalar(@$genomes);
    warn "$dropped requested genome(s) are not in the enumerated set and will not be sketched\n"
	if $dropped > 0;
}
else
{
    $genomes = $api->solr_query_list("genome", \@params, $opt->limit);
}

#
# Guard against the same genome appearing twice. Deep paging in the data API
# has returned duplicates before (it is what corrupted a blast build in
# 2026-08); here a duplicate would just mean sketching the same genome twice,
# but it would also inflate every count this script prints.
#
{
    my %seen;
    my @uniq = grep { !$seen{$_->{genome_id}}++ } @$genomes;
    if (@uniq != @$genomes)
    {
	warn "Dropping " . (scalar(@$genomes) - scalar(@uniq)) .
	    " duplicate genome(s) from the query result\n";
	@$genomes = @uniq;
    }
}

printf STDERR "Enumerated %d genomes\n", scalar @$genomes;

if (@$genomes == 0)
{
    die "Genome query returned nothing; refusing to run\n";
}

if ($opt->genome_list)
{
    open(GL, ">", $opt->genome_list) or die "Cannot write " . $opt->genome_list . ": $!";
    print GL "$_->{genome_id}\n" foreach @$genomes;
    close(GL);
}

#
# Partition into work.
#
# A genome with a non-empty sketch is done. Otherwise we need a fasta: the
# download file if it is there and non-empty, else a previously cached fetch,
# else a fetch. The -s tests matter -- a zero length file would sketch to
# nothing and hide the genome just as effectively as an absent one.
#
my @local;			# genomes whose fasta is already on disk
my @to_fetch;			# genomes we must pull from the data api
my $have = 0;
my $skipped = 0;

for my $g (@$genomes)
{
    my $gid = $g->{genome_id};

    $g->{sketch} = "$sketch_dir/$gid.msh";
    if (-s $g->{sketch})
    {
	$have++;
	next;
    }

    my $dl = "$genome_dir/$gid/$gid.fna";
    my $cached = $fetch_dir ? "$fetch_dir/$gid.fna" : undef;

    if (-s $dl)
    {
	$g->{fna} = $dl;
	push(@local, $g);
    }
    elsif ($cached && -s $cached)
    {
	$g->{fna} = $cached;
	push(@local, $g);
    }
    elsif ($opt->fetch_missing)
    {
	push(@to_fetch, $g);
    }
    else
    {
	$skipped++;
    }
}

printf STDERR "%d genomes already sketched, %d to sketch from disk, %d to fetch, %d skipped for lack of data\n",
    $have, scalar @local, scalar @to_fetch, $skipped;

#
# Report sketches on disk that are no longer in the enumerated set. We only
# count them -- mash paste works from an explicit file list built from the same
# query, so a stale sketch is already excluded from the combined sketches and
# costs nothing but an inode.
#
if ($opt->stale_list)
{
    my %want = map { $_->{genome_id} => 1 } @$genomes;
    opendir(my $sd, $sketch_dir) or die "Cannot opendir $sketch_dir: $!";
    open(SL, ">", $opt->stale_list) or die "Cannot write " . $opt->stale_list . ": $!";
    my $n = 0;
    while (my $f = readdir($sd))
    {
	next unless $f =~ /^(\d+\.\d+)\.msh$/;
	next if $want{$1};
	print SL "$1\n";
	$n++;
    }
    closedir($sd);
    close(SL);
    print STDERR "$n sketch(es) on disk are not in the enumerated set (listed in " . $opt->stale_list . ")\n";
}

#
# Build work items. Both kinds are batches: one item per genome would put over
# a million arrayrefs into the scheduler for no benefit.
#
# The weight is the summed genome length. For the fetch batches that understates
# the real cost, which is dominated by the round trip rather than by the bases,
# but it is monotonic in the right direction and the batches are uniform in size.
#
my $sched = LPTScheduler->new($opt->parallel);
my $nwork = 0;

while (@local)
{
    my @batch = splice(@local, 0, $opt->batch_size);
    my $w = 0;
    $w += $_->{genome_length} for @batch;
    $sched->add_work({ fetch => 0, genomes => \@batch }, $w);
    $nwork++;
}

while (@to_fetch)
{
    my @batch = splice(@to_fetch, 0, $opt->fetch_batch_size);
    my $w = 0;
    $w += $_->{genome_length} for @batch;
    $sched->add_work({ fetch => 1, genomes => \@batch }, $w);
    $nwork++;
}

if ($nwork == 0)
{
    print STDERR "Nothing to do\n";
    exit 0;
}

print STDERR "Running $nwork work items with " . $opt->parallel . " workers\n";

undef $api;

$sched->run(sub { return P3DataAPI->new() },
	    sub {
		my($api, $item) = @_;

		if ($item->{fetch})
		{
		    #
		    # A dry run must not touch the API or the cache: the point
		    # of it is to see the size of the job before paying for it.
		    #
		    if ($opt->dry_run)
		    {
			print "fetch $_->{genome_id}\n" for @{$item->{genomes}};
			return;
		    }
		    fetch_contigs_batch($api, $item->{genomes}, $fetch_dir);
		}

		sketch_one($_) for @{$item->{genomes}};
	    });

#
# Verify.
#
# LPTScheduler::run throws away the exit status of its children, so a worker
# that died is invisible from here. Re-probing the sketch directory is the only
# honest check, and it is cheap.
#
exit 0 if $opt->dry_run;

my @still_missing = grep { ! -s "$sketch_dir/$_->{genome_id}.msh" } @$genomes;

printf STDERR "%d of %d genomes have a sketch; %d still missing\n",
    scalar(@$genomes) - scalar(@still_missing), scalar @$genomes, scalar @still_missing;

if ($opt->missing_list)
{
    open(ML, ">", $opt->missing_list) or die "Cannot write " . $opt->missing_list . ": $!";
    for my $g (@still_missing)
    {
	my $gid = $g->{genome_id};
	#
	# Distinguish "we had contigs and sketching them failed" from "we never
	# got contigs" -- they need different follow-up, and only the second is
	# fixed by retrying the fetch.
	#
	my $dl = "$genome_dir/$gid/$gid.fna";
	my $cached = $fetch_dir ? "$fetch_dir/$gid.fna" : undef;
	my $why = (-s $dl || ($cached && -s $cached)) ? "sketch_failed"
	    : (-f $dl)                                ? "empty_download_file"
	    : ($cached && -f $cached)                 ? "empty_fetched_file"
	    :                                           "no_sequence_data";
	print ML join("\t", $gid, $why, $g->{genome_length}), "\n";
    }
    close(ML);
}

#
# Fetch contigs for a batch of genomes with one in(genome_id,(...)) query,
# demultiplexed into per-genome files by the genome_id on each record.
#
# Adapted from prefetch_missing_genomes() in
# homology_service/scripts/p3x-create-blast-db.pl. Note that
# P3DataAPI::retrieve_contigs_in_genomes, which the viral sketch builder uses,
# loops over its genome list and issues one query per genome -- passing it a
# list batches nothing.
#
sub fetch_contigs_batch
{
    my($api, $batch, $fetch_dir) = @_;

    my %out;

    for my $g (@$batch)
    {
	my $gid = $g->{genome_id};
	my $path = "$fetch_dir/$gid.fna";
	my $tmp = "$path.$$.tmp";
	my $fh = IO::File->new($tmp, "w") or die "Cannot write $tmp: $!";
	$out{$gid} = [$fh, $tmp, $path];
	$g->{fna} = $path;
    }

    my $genome_cond = [ "in", "genome_id",
			"(" . join(",", map { $_->{genome_id} } @$batch) . ")" ];

    $api->query_cb("genome_sequence",
		   sub {
		       my($data) = @_;
		       for my $ent (@$data)
		       {
			   my $e = $out{$ent->{genome_id}} or next;
			   my($fh, $tmp) = @$e;

			   #
			   # mash sketches the whole file and never looks at
			   # the headers, but reproducing the download file's
			   # header exactly makes a cached file a drop-in
			   # replacement for the real one. That format is
			   #
			   #   >ACCESSION   DESCRIPTION   [NAME | GENOME_ID]
			   #
			   # with three spaces between fields;
			   # print_alignment_as_fasta puts one space between
			   # the id and the description, hence the two leading
			   # spaces here.
			   #
			   print_alignment_as_fasta($fh,
						    [$ent->{accession},
						     "  $ent->{description}   [$ent->{genome_name} | $ent->{genome_id}]",
						     $ent->{sequence}]);
			   $fh->error
			       and die "Write failed on $tmp: $!\n";
		       }
		       return 1;
		   },
		   $genome_cond,
		   [ "select", "accession,sequence_id,description,genome_name,genome_id,sequence" ]);

    for my $gid (keys %out)
    {
	my($fh, $tmp, $path) = @{$out{$gid}};
	$fh->close or die "Close failed on $tmp: $!\n";

	if (-s $tmp)
	{
	    rename($tmp, $path) or die "Cannot rename $tmp to $path: $!\n";
	}
	else
	{
	    #
	    # No contigs came back. Leave nothing behind: an empty file in a
	    # persistent cache is a permanent hit and the genome would never be
	    # retried.
	    #
	    unlink($tmp);
	    warn "No contigs returned for $gid\n";
	}
    }
}

sub sketch_one
{
    my($g) = @_;

    my($gid, $fna, $sketch) = @$g{qw(genome_id fna sketch)};

    if (!$fna || ! -s $fna)
    {
	warn "No contig data for $gid, not sketching\n";
	return;
    }

    #
    # -I stamps the genome id into the sketch so its identity does not depend on
    # where the fasta happened to live. mash appends .msh to -o if it is not
    # already there, so the temp name below becomes $sketch.$$.tmp.msh; write
    # there and rename, so an interrupted mash cannot leave a partial sketch
    # that the next run would accept as a cache hit.
    #
    my $tmp = "$sketch.$$.tmp";
    my @cmd = ("mash", "sketch",
	       "-s", $opt->sketch_size,
	       "-I", $gid,
	       "-o", $tmp,
	       $fna);

    if ($opt->dry_run)
    {
	print "@cmd\n";
	return;
    }

    my($stdout, $stderr);
    my $ok = IPC::Run::run(\@cmd, '>', \$stdout, '2>', \$stderr);

    if (!$ok)
    {
	warn "Error running @cmd\nstdout=$stdout\nstderr=$stderr\n";
	unlink("$tmp.msh");
	return;
    }

    if (! -s "$tmp.msh")
    {
	warn "mash produced no sketch for $gid from $fna\n";
	unlink("$tmp.msh");
	return;
    }

    rename("$tmp.msh", $sketch) or die "Cannot rename $tmp.msh to $sketch: $!\n";
}
