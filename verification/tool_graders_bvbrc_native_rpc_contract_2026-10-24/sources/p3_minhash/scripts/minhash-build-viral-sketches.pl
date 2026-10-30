#
# Build viral sketches from the BV-BRC database
#

use strict;
use Data::Dumper;
use Getopt::Long::Descriptive;
use LPTScheduler;
use P3DataAPI;
use File::Path qw(make_path);

my($opt, $usage) = describe_options("%c %o sketch-dir",
				    ["sketch-size|s=i" => "Sketch size", { default => 1000 }],
				    ["parallel|p=i" => "Run with this many parallel threads", { default => 1 }],
				    ["batch-size|b=i" => "Size of genome batches to process in a thread", { default => 100 }],
				    ["reference" => "Pull reference genomes"],
				    ["representative" => "Pull representative genomes"],
				    ["dry-run" => "Show the commands that would be run"],
				    ["help|h" => "Show this help message"]);
print($usage->text), exit 0 if $opt->help;
die($usage->text), exit 0 if @ARGV != 1;

my $sketch_dir = shift;

-d $sketch_dir or die "Sketch directory $sketch_dir is not a directory\n";

my $api = P3DataAPI->new;

my @what;
push(@what, "Reference") if $opt->reference;
push(@what, "Representative") if $opt->representative;

my @refsearch;

if (@what)
{
    push(@refsearch, ["in", "reference_genome", "(" . join(",", @what) . ")"]);
}

my @genomes = $api->query("genome",
			  ["eq", "superkingdom", "Viruses"],
			  ["select", "genome_name,genome_id,genome_length,family"],
			  ["ne", "taxon_id", "2697049"],
			  @refsearch,
			 );

print "Starting\n";
undef $api;

my $sched = LPTScheduler->new($opt->parallel);


for my $g (@genomes)
{
    $sched->add_work($g, $g->{genome_length});
}
# die Dumper($sched);

$sched->run(sub { my $path = "/dev/shm/tmp.$$.genomes";
		  make_path($path);
		  return [$path, P3DataAPI->new()];
	      },
	    sub {
		my($glob, $item) = @_;
		my($base, $api) = @$glob;

		my $outdir = $sketch_dir;
		if (@what == 0)
		{
		    # if pulling everything, place into family subdir
		    $outdir .= "/$item->{family}";
		    make_path($outdir);
		}
		my $gid = $item->{genome_id};

		my $sketch_file = "$outdir/$gid.msh";

		$api->retrieve_contigs_in_genomes([$gid], $base, "%s.fna");
		my $file = "$base/$gid.fna";
		my @cmd = ("mash", "sketch", "-s", $opt->sketch_size, "-o", $sketch_file, $file);
		if ($opt->dry_run)
		{
		    print "@cmd\n";
		    unlink($file);
		    return;
		}
		print "@cmd\n";

		my($stdout, $stderr);
		
		my $ok = IPC::Run::run(\@cmd, '>', \$stdout, '2>', \$stderr);
		unlink($file);
		if (!$ok)
		{
		    warn "Error running @cmd\nstdout=$stdout\nstderr=$stderr\n";
		}
	    });
