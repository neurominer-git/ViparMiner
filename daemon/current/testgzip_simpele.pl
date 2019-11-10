#!/usr/bin/perl

use strict;
use IO::Compress::Gzip qw(gzip $GzipError) ;
use IO::Uncompress::Gunzip qw(gunzip $GunzipError) ;

my $file = "test.gz";
#my $data = undef;
#my $data_ref = \$data;
#my $gzip = new IO::Compress::Gzip $data_ref or die "IO::Compress::Gzip failed: $GzipError\n";
my $gzip = new IO::Compress::Gzip($file) or die "IO::Compress::Gzip failed: $GzipError\n";

$gzip->print($_) while (<DATA>);
$gzip->close();

#my $gunzip = new IO::Uncompress::Gunzip $data_ref or die "IO::Uncompress::Gunzip failed: $GunzipError\n";
my $gunzip = new IO::Uncompress::Gunzip($file) or die "IO::Uncompress::Gunzip failed: $GunzipError\n";

while (my $line = $gunzip->getline()){
 print $line;
 }

$gunzip->close();

# while (<$gunzip>);

__DATA__
12,2,3,4,5,6,7,8,91,2,3,4,5,6,7,8,91,2,3,4,5,6,7,8,91,2,3,4,5,6,7,8,9
1,2,3,4,5,6,7,8,91,2,3,4,5,6,7,8,91,2,3,4,5,6,7,8,91,2,3,4,5,6,7,8,9
