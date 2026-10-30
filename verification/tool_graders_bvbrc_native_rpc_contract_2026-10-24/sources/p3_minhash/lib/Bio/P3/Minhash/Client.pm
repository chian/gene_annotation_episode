package Bio::P3::Minhash::Client;

use POSIX;
use strict;
use Data::Dumper;
use URI;
use P3ClientUA;

use Time::HiRes qw(gettimeofday);

use P3AuthToken;


=head1 NAME

Bio::P3::Minhash::Client

=head1 DESCRIPTION





=cut


sub new
{
    my($class, $url, @args) = @_;
    
    if (!defined($url))
    {
	$url = 'http://localhost:7138';
    }

    my $self = {
	client => Bio::P3::Minhash::Client::RpcClient->new,
	url => $url,
	headers => [],
    };

    chomp($self->{hostname} = `hostname`);
    $self->{hostname} ||= 'unknown-host';

    #
    # Set up for propagating KBRPC_TAG and KBRPC_METADATA environment variables through
    # to invoked services. If these values are not set, we create a new tag
    # and a metadata field with basic information about the invoking script.
    #
    if ($ENV{KBRPC_TAG})
    {
	$self->{kbrpc_tag} = $ENV{KBRPC_TAG};
    }
    else
    {
	my ($t, $us) = gettimeofday;
	$us = sprintf("%06d", $us);
	my $ts = strftime("%Y-%m-%dT%H:%M:%S.${us}Z", gmtime $t);
	$self->{kbrpc_tag} = "C:$0:$self->{hostname}:$$:$ts";
    }
    push(@{$self->{headers}}, 'Kbrpc-Tag', $self->{kbrpc_tag});

    if ($ENV{KBRPC_METADATA})
    {
	$self->{kbrpc_metadata} = $ENV{KBRPC_METADATA};
	push(@{$self->{headers}}, 'Kbrpc-Metadata', $self->{kbrpc_metadata});
    }

    if ($ENV{KBRPC_ERROR_DEST})
    {
	$self->{kbrpc_error_dest} = $ENV{KBRPC_ERROR_DEST};
	push(@{$self->{headers}}, 'Kbrpc-Errordest', $self->{kbrpc_error_dest});
    }

    #
    # This module requires authentication.
    #
    # We create an auth token, passing through the arguments that we were (hopefully) given.

    {
	my $token = P3AuthToken->new(@args);
	
	if (my $token_str = $token->token())
	{
	    $self->{token} = $token_str;
	    $self->{client}->{token} = $token_str;
	}
    }

    my $ua = $self->{client}->ua;	 
    my $timeout = $ENV{CDMI_TIMEOUT} || (30 * 60);	 
    $ua->timeout($timeout);
    $ua->agent(P3ClientUA::user_agent_string());
    bless $self, $class;
    return $self;
}




=head2 compute_genome_distance_for_genome

  $return = $obj->compute_genome_distance_for_genome($genome_id, $max_pvalue, $max_distance, $max_hits, $include_reference, $include_representative)

=over 4

=item Parameter and return types

=begin html

<pre>
$genome_id is a string
$max_pvalue is a float
$max_distance is a float
$max_hits is an int
$include_reference is an int
$include_representative is an int
$return is a reference to a list where each element is a reference to a list containing 4 items:
	0: (genome_id) a string
	1: (distance) a float
	2: (pvalue) a float
	3: (counts) a string

</pre>

=end html

=begin text

$genome_id is a string
$max_pvalue is a float
$max_distance is a float
$max_hits is an int
$include_reference is an int
$include_representative is an int
$return is a reference to a list where each element is a reference to a list containing 4 items:
	0: (genome_id) a string
	1: (distance) a float
	2: (pvalue) a float
	3: (counts) a string


=end text

=item Description



=back

=cut

sub compute_genome_distance_for_genome
{
    my($self, @args) = @_;

# Authentication: optional

    if ((my $n = @args) != 6)
    {
        die "Invalid argument count for function compute_genome_distance_for_genome (received $n, expecting 6)";
    }
    {
	my($genome_id, $max_pvalue, $max_distance, $max_hits, $include_reference, $include_representative) = @args;

	my @_bad_arguments;
        (!ref($genome_id)) or push(@_bad_arguments, "Invalid type for argument 1 \"genome_id\" (value was \"$genome_id\")");
        (!ref($max_pvalue)) or push(@_bad_arguments, "Invalid type for argument 2 \"max_pvalue\" (value was \"$max_pvalue\")");
        (!ref($max_distance)) or push(@_bad_arguments, "Invalid type for argument 3 \"max_distance\" (value was \"$max_distance\")");
        (!ref($max_hits)) or push(@_bad_arguments, "Invalid type for argument 4 \"max_hits\" (value was \"$max_hits\")");
        (!ref($include_reference)) or push(@_bad_arguments, "Invalid type for argument 5 \"include_reference\" (value was \"$include_reference\")");
        (!ref($include_representative)) or push(@_bad_arguments, "Invalid type for argument 6 \"include_representative\" (value was \"$include_representative\")");
        if (@_bad_arguments) {
	    my $msg = "Invalid arguments passed to compute_genome_distance_for_genome:\n" . join("", map { "\t$_\n" } @_bad_arguments);
	    die $msg;
	}
    }

    my $result = $self->{client}->call($self->{url}, $self->{headers}, {
	method => "Minhash.compute_genome_distance_for_genome",
	params => \@args,
    });
    if ($result) {
	if ($result->{error}) {
	    my $msg = $result->{error}->{error} || $result->{error}->{message};
	    $msg =  $self->{client}->json->encode($msg) if ref($msg);
	    die "Error $result->{error}->{code} invoking compute_genome_distance_for_genome:\n$msg\n";
	} else {
	    return wantarray ? @{$result->{result}} : $result->{result}->[0];
	}
    } else {
	die "Error invoking method compute_genome_distance_for_genome: " .  $self->{client}->status_line;
    }
}



=head2 compute_genome_distance_for_fasta

  $return = $obj->compute_genome_distance_for_fasta($ws_fasta_path, $max_pvalue, $max_distance, $max_hits, $include_reference, $include_representative)

=over 4

=item Parameter and return types

=begin html

<pre>
$ws_fasta_path is a string
$max_pvalue is a float
$max_distance is a float
$max_hits is an int
$include_reference is an int
$include_representative is an int
$return is a reference to a list where each element is a reference to a list containing 4 items:
	0: (genome_id) a string
	1: (distance) a float
	2: (pvalue) a float
	3: (counts) a string

</pre>

=end html

=begin text

$ws_fasta_path is a string
$max_pvalue is a float
$max_distance is a float
$max_hits is an int
$include_reference is an int
$include_representative is an int
$return is a reference to a list where each element is a reference to a list containing 4 items:
	0: (genome_id) a string
	1: (distance) a float
	2: (pvalue) a float
	3: (counts) a string


=end text

=item Description



=back

=cut

sub compute_genome_distance_for_fasta
{
    my($self, @args) = @_;

# Authentication: optional

    if ((my $n = @args) != 6)
    {
        die "Invalid argument count for function compute_genome_distance_for_fasta (received $n, expecting 6)";
    }
    {
	my($ws_fasta_path, $max_pvalue, $max_distance, $max_hits, $include_reference, $include_representative) = @args;

	my @_bad_arguments;
        (!ref($ws_fasta_path)) or push(@_bad_arguments, "Invalid type for argument 1 \"ws_fasta_path\" (value was \"$ws_fasta_path\")");
        (!ref($max_pvalue)) or push(@_bad_arguments, "Invalid type for argument 2 \"max_pvalue\" (value was \"$max_pvalue\")");
        (!ref($max_distance)) or push(@_bad_arguments, "Invalid type for argument 3 \"max_distance\" (value was \"$max_distance\")");
        (!ref($max_hits)) or push(@_bad_arguments, "Invalid type for argument 4 \"max_hits\" (value was \"$max_hits\")");
        (!ref($include_reference)) or push(@_bad_arguments, "Invalid type for argument 5 \"include_reference\" (value was \"$include_reference\")");
        (!ref($include_representative)) or push(@_bad_arguments, "Invalid type for argument 6 \"include_representative\" (value was \"$include_representative\")");
        if (@_bad_arguments) {
	    my $msg = "Invalid arguments passed to compute_genome_distance_for_fasta:\n" . join("", map { "\t$_\n" } @_bad_arguments);
	    die $msg;
	}
    }

    my $result = $self->{client}->call($self->{url}, $self->{headers}, {
	method => "Minhash.compute_genome_distance_for_fasta",
	params => \@args,
    });
    if ($result) {
	if ($result->{error}) {
	    my $msg = $result->{error}->{error} || $result->{error}->{message};
	    $msg =  $self->{client}->json->encode($msg) if ref($msg);
	    die "Error $result->{error}->{code} invoking compute_genome_distance_for_fasta:\n$msg\n";
	} else {
	    return wantarray ? @{$result->{result}} : $result->{result}->[0];
	}
    } else {
	die "Error invoking method compute_genome_distance_for_fasta: " .  $self->{client}->status_line;
    }
}



=head2 compute_genome_distance_for_genome2

  $return = $obj->compute_genome_distance_for_genome2($genome_id, $max_pvalue, $max_distance, $max_hits, $include_reference, $include_representative, $bacterial, $viral)

=over 4

=item Parameter and return types

=begin html

<pre>
$genome_id is a string
$max_pvalue is a float
$max_distance is a float
$max_hits is an int
$include_reference is an int
$include_representative is an int
$bacterial is an int
$viral is an int
$return is a reference to a list where each element is a reference to a list containing 4 items:
	0: (genome_id) a string
	1: (distance) a float
	2: (pvalue) a float
	3: (counts) a string

</pre>

=end html

=begin text

$genome_id is a string
$max_pvalue is a float
$max_distance is a float
$max_hits is an int
$include_reference is an int
$include_representative is an int
$bacterial is an int
$viral is an int
$return is a reference to a list where each element is a reference to a list containing 4 items:
	0: (genome_id) a string
	1: (distance) a float
	2: (pvalue) a float
	3: (counts) a string


=end text

=item Description



=back

=cut

sub compute_genome_distance_for_genome2
{
    my($self, @args) = @_;

# Authentication: optional

    if ((my $n = @args) != 8)
    {
        die "Invalid argument count for function compute_genome_distance_for_genome2 (received $n, expecting 8)";
    }
    {
	my($genome_id, $max_pvalue, $max_distance, $max_hits, $include_reference, $include_representative, $bacterial, $viral) = @args;

	my @_bad_arguments;
        (!ref($genome_id)) or push(@_bad_arguments, "Invalid type for argument 1 \"genome_id\" (value was \"$genome_id\")");
        (!ref($max_pvalue)) or push(@_bad_arguments, "Invalid type for argument 2 \"max_pvalue\" (value was \"$max_pvalue\")");
        (!ref($max_distance)) or push(@_bad_arguments, "Invalid type for argument 3 \"max_distance\" (value was \"$max_distance\")");
        (!ref($max_hits)) or push(@_bad_arguments, "Invalid type for argument 4 \"max_hits\" (value was \"$max_hits\")");
        (!ref($include_reference)) or push(@_bad_arguments, "Invalid type for argument 5 \"include_reference\" (value was \"$include_reference\")");
        (!ref($include_representative)) or push(@_bad_arguments, "Invalid type for argument 6 \"include_representative\" (value was \"$include_representative\")");
        (!ref($bacterial)) or push(@_bad_arguments, "Invalid type for argument 7 \"bacterial\" (value was \"$bacterial\")");
        (!ref($viral)) or push(@_bad_arguments, "Invalid type for argument 8 \"viral\" (value was \"$viral\")");
        if (@_bad_arguments) {
	    my $msg = "Invalid arguments passed to compute_genome_distance_for_genome2:\n" . join("", map { "\t$_\n" } @_bad_arguments);
	    die $msg;
	}
    }

    my $result = $self->{client}->call($self->{url}, $self->{headers}, {
	method => "Minhash.compute_genome_distance_for_genome2",
	params => \@args,
    });
    if ($result) {
	if ($result->{error}) {
	    my $msg = $result->{error}->{error} || $result->{error}->{message};
	    $msg =  $self->{client}->json->encode($msg) if ref($msg);
	    die "Error $result->{error}->{code} invoking compute_genome_distance_for_genome2:\n$msg\n";
	} else {
	    return wantarray ? @{$result->{result}} : $result->{result}->[0];
	}
    } else {
	die "Error invoking method compute_genome_distance_for_genome2: " .  $self->{client}->status_line;
    }
}



=head2 compute_genome_distance_for_fasta2

  $return = $obj->compute_genome_distance_for_fasta2($ws_fasta_path, $max_pvalue, $max_distance, $max_hits, $include_reference, $include_representative, $bacterial, $viral)

=over 4

=item Parameter and return types

=begin html

<pre>
$ws_fasta_path is a string
$max_pvalue is a float
$max_distance is a float
$max_hits is an int
$include_reference is an int
$include_representative is an int
$bacterial is an int
$viral is an int
$return is a reference to a list where each element is a reference to a list containing 4 items:
	0: (genome_id) a string
	1: (distance) a float
	2: (pvalue) a float
	3: (counts) a string

</pre>

=end html

=begin text

$ws_fasta_path is a string
$max_pvalue is a float
$max_distance is a float
$max_hits is an int
$include_reference is an int
$include_representative is an int
$bacterial is an int
$viral is an int
$return is a reference to a list where each element is a reference to a list containing 4 items:
	0: (genome_id) a string
	1: (distance) a float
	2: (pvalue) a float
	3: (counts) a string


=end text

=item Description



=back

=cut

sub compute_genome_distance_for_fasta2
{
    my($self, @args) = @_;

# Authentication: optional

    if ((my $n = @args) != 8)
    {
        die "Invalid argument count for function compute_genome_distance_for_fasta2 (received $n, expecting 8)";
    }
    {
	my($ws_fasta_path, $max_pvalue, $max_distance, $max_hits, $include_reference, $include_representative, $bacterial, $viral) = @args;

	my @_bad_arguments;
        (!ref($ws_fasta_path)) or push(@_bad_arguments, "Invalid type for argument 1 \"ws_fasta_path\" (value was \"$ws_fasta_path\")");
        (!ref($max_pvalue)) or push(@_bad_arguments, "Invalid type for argument 2 \"max_pvalue\" (value was \"$max_pvalue\")");
        (!ref($max_distance)) or push(@_bad_arguments, "Invalid type for argument 3 \"max_distance\" (value was \"$max_distance\")");
        (!ref($max_hits)) or push(@_bad_arguments, "Invalid type for argument 4 \"max_hits\" (value was \"$max_hits\")");
        (!ref($include_reference)) or push(@_bad_arguments, "Invalid type for argument 5 \"include_reference\" (value was \"$include_reference\")");
        (!ref($include_representative)) or push(@_bad_arguments, "Invalid type for argument 6 \"include_representative\" (value was \"$include_representative\")");
        (!ref($bacterial)) or push(@_bad_arguments, "Invalid type for argument 7 \"bacterial\" (value was \"$bacterial\")");
        (!ref($viral)) or push(@_bad_arguments, "Invalid type for argument 8 \"viral\" (value was \"$viral\")");
        if (@_bad_arguments) {
	    my $msg = "Invalid arguments passed to compute_genome_distance_for_fasta2:\n" . join("", map { "\t$_\n" } @_bad_arguments);
	    die $msg;
	}
    }

    my $result = $self->{client}->call($self->{url}, $self->{headers}, {
	method => "Minhash.compute_genome_distance_for_fasta2",
	params => \@args,
    });
    if ($result) {
	if ($result->{error}) {
	    my $msg = $result->{error}->{error} || $result->{error}->{message};
	    $msg =  $self->{client}->json->encode($msg) if ref($msg);
	    die "Error $result->{error}->{code} invoking compute_genome_distance_for_fasta2:\n$msg\n";
	} else {
	    return wantarray ? @{$result->{result}} : $result->{result}->[0];
	}
    } else {
	die "Error invoking method compute_genome_distance_for_fasta2: " .  $self->{client}->status_line;
    }
}



=head2 compute_genome_distance_for_sra

  $return = $obj->compute_genome_distance_for_sra($sra_id, $max_pvalue, $max_distance, $max_hits, $include_reference, $include_representative)

=over 4

=item Parameter and return types

=begin html

<pre>
$sra_id is a string
$max_pvalue is a float
$max_distance is a float
$max_hits is an int
$include_reference is an int
$include_representative is an int
$return is a reference to a list where each element is a reference to a list containing 4 items:
	0: (genome_id) a string
	1: (distance) a float
	2: (pvalue) a float
	3: (counts) a string

</pre>

=end html

=begin text

$sra_id is a string
$max_pvalue is a float
$max_distance is a float
$max_hits is an int
$include_reference is an int
$include_representative is an int
$return is a reference to a list where each element is a reference to a list containing 4 items:
	0: (genome_id) a string
	1: (distance) a float
	2: (pvalue) a float
	3: (counts) a string


=end text

=item Description

Compute genome distance for the read data in the given SRA run,
experiment, or project accession (SRR/SRX/SRP or the DDBJ/ENA
equivalents DRR/DRX/DRP/ERR/ERX/ERP). The reads are downloaded via
p3_sra and sketched with mash before being compared to the reference
sketch collections.

=back

=cut

sub compute_genome_distance_for_sra
{
    my($self, @args) = @_;

# Authentication: optional

    if ((my $n = @args) != 6)
    {
        die "Invalid argument count for function compute_genome_distance_for_sra (received $n, expecting 6)";
    }
    {
	my($sra_id, $max_pvalue, $max_distance, $max_hits, $include_reference, $include_representative) = @args;

	my @_bad_arguments;
        (!ref($sra_id)) or push(@_bad_arguments, "Invalid type for argument 1 \"sra_id\" (value was \"$sra_id\")");
        (!ref($max_pvalue)) or push(@_bad_arguments, "Invalid type for argument 2 \"max_pvalue\" (value was \"$max_pvalue\")");
        (!ref($max_distance)) or push(@_bad_arguments, "Invalid type for argument 3 \"max_distance\" (value was \"$max_distance\")");
        (!ref($max_hits)) or push(@_bad_arguments, "Invalid type for argument 4 \"max_hits\" (value was \"$max_hits\")");
        (!ref($include_reference)) or push(@_bad_arguments, "Invalid type for argument 5 \"include_reference\" (value was \"$include_reference\")");
        (!ref($include_representative)) or push(@_bad_arguments, "Invalid type for argument 6 \"include_representative\" (value was \"$include_representative\")");
        if (@_bad_arguments) {
	    my $msg = "Invalid arguments passed to compute_genome_distance_for_sra:\n" . join("", map { "\t$_\n" } @_bad_arguments);
	    die $msg;
	}
    }

    my $result = $self->{client}->call($self->{url}, $self->{headers}, {
	method => "Minhash.compute_genome_distance_for_sra",
	params => \@args,
    });
    if ($result) {
	if ($result->{error}) {
	    my $msg = $result->{error}->{error} || $result->{error}->{message};
	    $msg =  $self->{client}->json->encode($msg) if ref($msg);
	    die "Error $result->{error}->{code} invoking compute_genome_distance_for_sra:\n$msg\n";
	} else {
	    return wantarray ? @{$result->{result}} : $result->{result}->[0];
	}
    } else {
	die "Error invoking method compute_genome_distance_for_sra: " .  $self->{client}->status_line;
    }
}



=head2 compute_genome_distance_for_sra2

  $return = $obj->compute_genome_distance_for_sra2($sra_id, $max_pvalue, $max_distance, $max_hits, $include_reference, $include_representative, $bacterial, $viral)

=over 4

=item Parameter and return types

=begin html

<pre>
$sra_id is a string
$max_pvalue is a float
$max_distance is a float
$max_hits is an int
$include_reference is an int
$include_representative is an int
$bacterial is an int
$viral is an int
$return is a reference to a list where each element is a reference to a list containing 4 items:
	0: (genome_id) a string
	1: (distance) a float
	2: (pvalue) a float
	3: (counts) a string

</pre>

=end html

=begin text

$sra_id is a string
$max_pvalue is a float
$max_distance is a float
$max_hits is an int
$include_reference is an int
$include_representative is an int
$bacterial is an int
$viral is an int
$return is a reference to a list where each element is a reference to a list containing 4 items:
	0: (genome_id) a string
	1: (distance) a float
	2: (pvalue) a float
	3: (counts) a string


=end text

=item Description



=back

=cut

sub compute_genome_distance_for_sra2
{
    my($self, @args) = @_;

# Authentication: optional

    if ((my $n = @args) != 8)
    {
        die "Invalid argument count for function compute_genome_distance_for_sra2 (received $n, expecting 8)";
    }
    {
	my($sra_id, $max_pvalue, $max_distance, $max_hits, $include_reference, $include_representative, $bacterial, $viral) = @args;

	my @_bad_arguments;
        (!ref($sra_id)) or push(@_bad_arguments, "Invalid type for argument 1 \"sra_id\" (value was \"$sra_id\")");
        (!ref($max_pvalue)) or push(@_bad_arguments, "Invalid type for argument 2 \"max_pvalue\" (value was \"$max_pvalue\")");
        (!ref($max_distance)) or push(@_bad_arguments, "Invalid type for argument 3 \"max_distance\" (value was \"$max_distance\")");
        (!ref($max_hits)) or push(@_bad_arguments, "Invalid type for argument 4 \"max_hits\" (value was \"$max_hits\")");
        (!ref($include_reference)) or push(@_bad_arguments, "Invalid type for argument 5 \"include_reference\" (value was \"$include_reference\")");
        (!ref($include_representative)) or push(@_bad_arguments, "Invalid type for argument 6 \"include_representative\" (value was \"$include_representative\")");
        (!ref($bacterial)) or push(@_bad_arguments, "Invalid type for argument 7 \"bacterial\" (value was \"$bacterial\")");
        (!ref($viral)) or push(@_bad_arguments, "Invalid type for argument 8 \"viral\" (value was \"$viral\")");
        if (@_bad_arguments) {
	    my $msg = "Invalid arguments passed to compute_genome_distance_for_sra2:\n" . join("", map { "\t$_\n" } @_bad_arguments);
	    die $msg;
	}
    }

    my $result = $self->{client}->call($self->{url}, $self->{headers}, {
	method => "Minhash.compute_genome_distance_for_sra2",
	params => \@args,
    });
    if ($result) {
	if ($result->{error}) {
	    my $msg = $result->{error}->{error} || $result->{error}->{message};
	    $msg =  $self->{client}->json->encode($msg) if ref($msg);
	    die "Error $result->{error}->{code} invoking compute_genome_distance_for_sra2:\n$msg\n";
	} else {
	    return wantarray ? @{$result->{result}} : $result->{result}->[0];
	}
    } else {
	die "Error invoking method compute_genome_distance_for_sra2: " .  $self->{client}->status_line;
    }
}





=head1 TYPES



=cut

package Bio::P3::Minhash::Client::RpcClient;
use POSIX;
use strict;
use LWP::UserAgent;
use P3ClientUA;
use JSON::XS;

BEGIN {
    for my $method (qw/uri ua json content_type version id allow_call status_line/) {
	eval qq|
	    sub $method {
		\$_[0]->{$method} = \$_[1] if defined \$_[1];
		\$_[0]->{$method};
	    }
	    |;
	}
    }

sub new
{
    my($class) = @_;

    my $ua = P3ClientUA::new_ua();
    my $json = JSON::XS->new->allow_nonref->utf8;
    
    my $self = {
	ua => $ua,
	json => $json,
    };
    return bless $self, $class;
}

sub call {
    my ($self, $uri, $headers, $obj) = @_;
    my $result;


    my @retries = (1, 2, 5, 10, 20, 60, 60, 60, 60, 60, 60);
    my %codes_to_retry =  map { $_ => 1 } qw(110 408 502 503 504 200) ;
    my $n_retries;

    while (1)

    {
	if ($uri =~ /\?/) {
	    $result = $self->_get($uri);
	}
	else {
	    Carp::croak "not hashref." unless (ref $obj eq 'HASH');
	    $result = $self->_post($uri, $headers, $obj);
	}

	#
	# Bail early on success.
	#
	if ($result->is_success)
	{
	    if ($n_retries)
	    {
		print STDERR strftime("%F %T", localtime), ": Request succeeded after $n_retries retries\n";
	    }
	    last;
	}
	$n_retries++;

	#
	# Failure. See if we need to retry and loop, or bail with
	# a permanent failure.
	#
	
        my $code = $result->code;
	my $msg = $result->message;
	my $want_retry = 0;
	if ($codes_to_retry{$code})
	{
	    $want_retry = 1;
	}
	elsif ($code eq 500 && defined( $result->header('client-warning') )
	       && $result->header('client-warning') eq 'Internal response')
	{
	    #
	    # Handle errors that were not thrown by the web
	    # server but rather picked up by the client library.
	    #
	    # If we got a client timeout or connection refused, let us retry.
	    #
	    
	    if ($msg =~ /timeout|connection refused/i)
	    {
		$want_retry = 1;
	    }
	    
	}
	
        if (!$want_retry || @retries == 0) {
	    last;
        }
	
        #
        # otherwise, sleep & loop.
        #
        my $retry_time = shift(@retries);
        print STDERR strftime("%F %T", localtime), ": Request failed with code=$code msg=$msg, sleeping $retry_time and retrying\n";
        sleep($retry_time);

    }

    my $service = $obj->{method} =~ /^system\./ if ( $obj );

    $self->status_line($result->status_line);

    if ($result->is_success || $result->content_type eq 'application/json') {

	my $txt = $result->content;

        return unless($txt); # notification?

	my $obj = eval { $self->json->decode($txt); };

	if (!$obj)
	{
	    die "Error parsing result: $@";
	}

	return $obj;
    }
    else {
        return;
    }
}

sub _get {
    my ($self, $uri) = @_;
    $self->ua->get(
		   $uri,
		   Accept         => 'application/json',
		  );
}

sub _post {
    my ($self, $uri, $headers, $obj) = @_;
    my $json = $self->json;

    $obj->{version} ||= $self->{version} || '1.1';

    if ($obj->{version} eq '1.0') {
        delete $obj->{version};
        if (exists $obj->{id}) {
            $self->id($obj->{id}) if ($obj->{id}); # if undef, it is notification.
        }
        else {
            $obj->{id} = $self->id || ($self->id('JSON::RPC::Legacy::Client'));
        }
    }
    else {
        # $obj->{id} = $self->id if (defined $self->id);
	# Assign a random number to the id if one hasn't been set
	$obj->{id} = (defined $self->id) ? $self->id : substr(rand(),2);
    }

    my $content = $json->encode($obj);

    $self->ua->post(
        $uri,
        Content_Type   => $self->{content_type},
        Content        => $content,
        Accept         => 'application/json',
	@$headers,
	($self->{token} ? (Authorization => $self->{token}) : ()),
    );
}



1;
