#
# App wrapper for read mapping
# Initial version that does not internally fork and report output; instead
# is designed to be executed by p3x-app-shepherd.
#

use Bio::KBase::AppService::AppScript;
use Bio::KBase::AppService::ReadSet;
use Bio::KBase::AppService::AppConfig qw(kma_db data_api_url);
use Bio::KBase::AppService::ClientExt;
use Bio::KBase::AppService::FastaParser 'parse_fasta';
use Bio::P3::Workspace::WorkspaceClientExt;
use Bio::P3::MetagenomicReadMapping::Report 'write_report';
use IPC::Run;
use Cwd;
use File::Path 'make_path';
use strict;
use Data::Dumper;
use File::Basename;
use File::Temp;
use JSON::XS;
use Getopt::Long::Descriptive;
use P3DataAPI;
use gjoseqlib;
use File::Copy;
# adding in for data validation and testing
use Time::HiRes qw( time );

my $app = Bio::KBase::AppService::AppScript->new(\&run_mapping, \&preflight);

my $rc = $app->run(\@ARGV);

exit $rc;

sub run_mapping
{
    my($app, $app_def, $raw_params, $params) = @_;
    my $begin_time = time();
    print STDERR "Processed parameters for application " . $app->app_definition->{id} . ": ", Dumper($params);

    my $here = getcwd;
    my $staging_dir = "$here/staging";
    my $output_dir = "$here/output";

    eval {
        make_path($staging_dir, $output_dir);
        run($app, $params, $staging_dir, $output_dir);
    };
    my $err = $@;
    if ($err)
    {
	warn "Run failed: $@";
    }

    save_output_files($app, $output_dir);
    my $end_time = time();
    printf STDERR "TOTAL TIME ELAPSED %.2f\n", $end_time - $begin_time ;
}

sub run
{
    my($app, $params, $staging_dir, $output_dir) = @_;

    #
    # Set up options for tool and database.
    #

    my @cmd;
    my $db_dir;

    if ($params->{gene_set_type} ne 'predefined_list' and
	$params->{gene_set_type} ne 'feature_group' and
	$params->{gene_set_type} ne 'fasta_file')
    {
	    die "Gene set type $params->{gene_set_type} not supported";
    }

    if ($params->{gene_set_type} eq 'predefined_list')
    {
      my %db_map = (CARD => 'CARD',
  		    VFDB => 'VFDB');
	$db_dir = $db_map{$params->{gene_set_name}};

	if (!$db_dir)
	{
	    die "Invalid gene set name '$params->{gene_set_name}' specified. Valid values are " . join(", ", map { qq("$_") } keys %db_map);
	}

	if ($db_dir !~ m,^/,)
	{
	    $db_dir = kma_db . "/$db_dir";
	}
    }
    
    if($params->{gene_set_type} eq 'fasta_file')
    {
      # load the input fasta file from workspace
      my $fh;
      my $local_fasta = "$staging_dir/local_fasta.fasta";
      my $ws = Bio::P3::Workspace::WorkspaceClientExt->new;

      if (open(my $fh, ">", $local_fasta))
      {

  	     $ws->copy_files_to_handles(1, undef, [[$params->{gene_set_fasta}, $fh]]);

  	      close($fh);
      }
      else
      {
  	     die "Cannot open $local_fasta for writing: $!";
      }

      $db_dir = "$staging_dir/fasta_db";

       @cmd = ("kma_index");
                push(@cmd,
                "-i", $local_fasta,
                "-o", $db_dir);

       # If we are running under Slurm, pick up our memory and CPU limits.
       #
       my $mem = $ENV{P3_ALLOCATED_MEMORY};
       my $cpu = $ENV{P3_ALLOCATED_CPU};

       print STDERR "Run: @cmd\n";
       my $ok = IPC::Run::run(\@cmd);
       if (!$ok)
       {
         die "KMA index execution failed with $?: @cmd";
       }
    }

    if ($params->{gene_set_type} eq 'feature_group')
    {
      my $fh;
      my $file;
      my $group;
      my @cmd;

      my $api = P3DataAPI->new();

      my $group = $params->{gene_set_feature_group};

      my $ftype = 'dna'; # or 'aa'

      my $file = "$staging_dir/input_$params->{gene_set_type}.fasta";

      open($fh, ">", $file) or die "Cannot write $file $!";

      $api->retrieve_features_in_feature_group_in_export_format($group, $ftype, \*$fh);

      close($fh);

    # create database
    $db_dir = "$staging_dir/feature_db";
    my $db_path = kma_db . "/$db_dir";

     @cmd = ("kma_index");
     push(@cmd,
          "-i", $file,
          "-o", $db_dir);

     #
     # If we are running under Slurm, pick up our memory and CPU limits.
     #

     my $mem = $ENV{P3_ALLOCATED_MEMORY};
     my $cpu = $ENV{P3_ALLOCATED_CPU};


     print STDERR "Run: @cmd\n";
     my $ok = IPC::Run::run(\@cmd);
     if (!$ok)
     {
       die "KMA index execution failed with $?: @cmd";
     }
    }

    
    #
    # map to databases
    #
      my $db_path = kma_db . "/$db_dir";
      my $kma_identity = 70;

      -f "$db_dir.name" or die "Database file for $db_dir not found\n";

      my @input_params = stage_input($app, $params, $staging_dir);
      my $output_base = "$output_dir/kma";
      @cmd = ("kma");
      push(@cmd,
          "-ID", $kma_identity,
          "-t_db", $db_dir,
          "-ef",
          @input_params,
          "-o", $output_base);
    #
    # If we are running under Slurm, pick up our memory and CPU limits.
    #
    my $mem = $ENV{P3_ALLOCATED_MEMORY};
    my $cpu = $ENV{P3_ALLOCATED_CPU};

    print STDERR "Run: @cmd\n";
    my $ok = IPC::Run::run(\@cmd);
    if (!$ok)
    {
      die "KMA execution failed with $?: @cmd";
    }

    #
    # Write our report.
    #

    if (open(my $out_fh, ">", "$output_dir/MetagenomicReadMappingReport.html"))
    {
     write_report($app->task_id, $params, $output_base, $out_fh);
     close($out_fh);
    }
}


#
# Stage input data. Return the input parameters for kma.
#
sub stage_input
{
    my($app, $params, $staging_dir) = @_;
    my $readset = Bio::KBase::AppService::ReadSet->create_from_asssembly_params($params, 1);
    my($ok, $errs, $comp_size, $uncomp_size) = $readset->validate($app->workspace);

    if (!$ok)
    {
	     die "Readset failed to validate. Errors:\n\t" . join("\n\t", @$errs);
    }

    $readset->localize_libraries($staging_dir);
    $readset->stage_in($app->workspace);

    my @app_params;

    my $pe_cb = sub {
	my($lib) = @_;
	push(@app_params, "-ipe", $lib->paths());
    };
    my $se_cb = sub {
	my($lib) = @_;
	push(@app_params, "-i", $lib->paths());
    };

    #
    # We skip SRRs since the localize/stage_in created PE and SE libs for them.
    #
    $readset->visit_libraries($pe_cb, $se_cb, undef);

    return @app_params;
}

#
# Run preflight to estimate size and duration.
#
sub preflight
{
    my($app, $app_def, $raw_params, $params) = @_;

    my $readset = Bio::KBase::AppService::ReadSet->create_from_asssembly_params($params);

    my($ok, $errs, $comp_size, $uncomp_size) = $readset->validate($app->workspace);

    if (!$ok)
    {
	     die "Readset failed to validate. Errors:\n\t" . join("\n\t", @$errs);
    }

    my $time = 60 * 60 * 12;
    my $pf = {
            	cpu => 1,
            	memory => "32G",
            	runtime => $time,
            	storage => 1.1 * ($comp_size + $uncomp_size),
              };

    return $pf;
}

sub save_output_files
{
    my($app, $output) = @_;

    my %suffix_map = (fastq => 'reads',
		      fss => 'feature_dna_fasta',
		      res => 'txt',
		      aln => 'txt',
		      txt => 'txt',
		      out => 'txt',
		      err => 'txt',
		      html => 'html');

    #
    # Make a pass over the folder and compress any fastq files.
    #
    if (opendir(D, $output))
    {
	     while (my $f = readdir(D))
	      {
    	    my $path = "$output/$f";
    	    if (-f $path &&
    		     ($f =~ /\.fastq$/))
    	    {
    		      my $rc = system("gzip", "-f", $path);
		          if ($rc)
		            {
		                warn "Error $rc compressing $path";
                }
            }
          }
        }

    if (opendir(D, $output))
    {
	     while (my $f = readdir(D))
      {
	       my $path = "$output/$f";

         my $p2 = $f;
         $p2 =~ s/\.gz$//;
         my($suffix) = $p2 =~ /\.([^.]+)$/;
         my $type = $suffix_map{$suffix} // "txt";

	        if (-f $path)
	         {
		           print "Save $path type=$type\n";
	             $app->workspace->save_file_to_file($path, {}, $app->result_folder . "/$f", $type, 1, 0, $app->token->token);
            }
       }

    }
    else
    {
	     warn "Cannot opendir $output: $!";
    }
}