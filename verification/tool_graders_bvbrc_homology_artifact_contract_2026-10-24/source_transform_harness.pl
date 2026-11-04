use strict;
use JSON::PP;
package SyntheticHomologyTransform;
sub json { return $_[0]->{json}; }
sub massage_blast_json
{
    my($self, $json) = @_;
    my $doc = eval { $self->json->decode($json) };
    if ($@)
    {
	die "json parse failed: $@\n$json\n";
    }
    $doc = $doc->{BlastOutput2};
    $doc or die "JSON output didn't have expected key BlastOutput2";

    my $metadata = {};
    for my $report (@$doc)
    {
	my $search = $report->{report}->{results}->{search};
	$search->{query_id} =~ s/^gnl\|//;
	if ($search->{query_id} =~ /^Query_\d+/)
	{
	    my($xid) = $search->{query_title} =~ /^(\S+)/;
	    $search->{query_id} = $xid if $xid;
	}
	for my $res (@{$search->{hits}})
	{
	    for my $desc (@{$res->{description}})
	    {
		my $md = $self->decode_title($desc);
		
		$metadata->{$desc->{id}} = $md if $md;
	    }
	}
    }
    return($doc, $metadata);
}

sub decode_title
{
    my($self, $desc) = @_;
	
    my $md;
    
    if ($desc->{id} =~ /^gnl\|BL_ORD/)
    {
	if ($desc->{title} =~ /^(\S+)\s{3}(.*)\s{3}(.*)$/)
	{
	    my $id = $1;
	    my $fun = $2;
	    my $ginfo = $3;
	    $id =~ s/^((fig\|\d+\.\d+.[^.]+\.\d+)|(accn\|[^|]+))//;
	    my $fid = $1;
	    print "id=$id\n";
	    $id =~ s/^\|//;
	    $id =~ s/\|$//;
	    my @rest = split(/\|/, $id);
	    my $locus;
	    my $alt;
	    if (@rest == 2)
	    {
		($locus, $alt) = @rest;
		$md->{locus_tag} = $locus;
		$md->{alt_locus_tag} = $alt;
	    }
	    elsif (@rest == 1)
	    {
		$alt = $rest[0];
		$md->{alt_locus_tag} = $alt;
	    }
	    if ($ginfo =~ /^\[(.*) \| (\d+\.\d+)/)
	    {
		$md->{genome_name} = $1;
		$md->{genome_id} = $2;
	    }
	    $desc->{id} = $fid;
	    $md->{function} = $fun;
	}
	elsif ($desc->{title} =~ /^(\S+)\s+(.*)\s{3}\[(.*?)(\s*\|\s*(\S+))?\]\s*$/)
	{
	    $desc->{id} = $1;
	    $md->{function} = $2;
	    $md->{genome_name} = $3;
	    $md->{genome_id} = $5 if $5;
	}
	elsif ($desc->{title} =~ /^(\S+)\s+\[(.*?)(\s*\|\s*(\S+))?\]\s*$/)
	{
	    $desc->{id} = $1;
	    $md->{genome_name} = $2;
	    $md->{genome_id} = $4 if $4;
	}
	elsif ($desc->{title} =~ /^(\S+)\s+(.*)\s*$/)
	{
	    $desc->{id} = $1;
	    $md->{function} = $2;
	    $desc->{title} = $2;
	}
	else
	{
	    $desc->{id} = $desc->{title};
	}
    }
    else
    {
	$desc->{id} =~ s/^gnl\|//;
	if ($desc->{title} =~ /^\s*(.*)\s{3}\[(.*?)(\s*\|\s*(\S+))?\]\s*$/)
	{
	    $md->{function} = $1;
	    $md->{genome_name} = $2;
	    $md->{genome_id} = $4 if $4;
	}
	elsif ($desc->{title} =~ /^\s*\[(.*?)(\s*\|\s*(\S+))?\]\s*$/)
	{
	    $md->{genome_name} = $1;
	    $md->{genome_id} = $3 if $3;
	}
    }
    if ($desc->{id} =~ /^(kb\|g\.\d+)/)
    {
	$md->{genome_id} = $1;
    }
    return $md;
}


package main;
local $/;
open(my $in, '<', $ARGV[0]) or die $!;
my $text = <$in>;
my $codec = JSON::PP->new->pretty->canonical;
my $self = bless({json => $codec}, 'SyntheticHomologyTransform');
my ($processed, $metadata) = $self->massage_blast_json($text);
open(my $proc, '>', $ARGV[1]) or die $!;
print $proc $codec->encode($processed);
open(my $meta, '>', $ARGV[2]) or die $!;
print $meta $codec->encode($metadata);
