use Carp::Always;
use Bio::KBase::AppService::AppScript;
use File::Slurp;
use IPC::Run;
use Cwd qw(abs_path getcwd);
use File::Path qw(rmtree make_path);
use strict;
use Data::Dumper;
use File::Basename;
use File::Temp;
use JSON::XS;
use Getopt::Long::Descriptive;
use CoreGenomeMLST;

my $CoreGenomeMLST_run = new CoreGenomeMLST();

my $app = Bio::KBase::AppService::AppScript->new(sub { $CoreGenomeMLST_run->run_CoreGenomeMLST(@_); },
						 sub { $CoreGenomeMLST_run->preflight(@_); });

$app->run(\@ARGV);