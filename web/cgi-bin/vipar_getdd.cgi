#!/usr/bin/perl

use strict;
use PDF::Create;
use DBI;
use CGI;
use CGI::Session;
use CGI::Carp qw(fatalsToBrowser);
use AppConfig;

# Check for Cookie or err
my $cgi = new CGI;
my $sid = $cgi->cookie("VIPAR_CGISESSID") || &err_login();

my $session = CGI::Session->load($sid);
&err_login() if $session->is_expired();
$session->expire('+1h');
my $uid = $session->param("userid");

my $form = new CGI;
my $dd = $form->param('dd');

my $dbconfig = AppConfig->new();
my $dbconfig_file = $ENV{'VIPAR_ROOT'}."/daemon/current/db.conf";

#define db vars
$dbconfig->define("database_name=<undef>");
$dbconfig->define("database_adminuser=<undef>");
$dbconfig->define("database_adminpass=<undef>");
$dbconfig->define("database_queryuser=<undef>");
$dbconfig->define("database_querypass=<undef>");

$dbconfig->file($dbconfig_file);

#check all DB options are set
my %conf = $dbconfig->varlist("database_*");
foreach my $c (keys %conf){
 if ( !defined($dbconfig->get($c)) ){
  die "Option $c not set in config file $dbconfig_file ... exiting\n";
  }
 }

#connect to DB
my $dsn = "dbi:mysql:".$dbconfig->get("database_name");
my $dbuser = $dbconfig->get("database_queryuser");
my $dbpass = $dbconfig->get("database_querypass");
my %attr = (
        RaiseError => 1,
        AutoCommit => 0
        );

# connect to the database
my $dbh = DBI->connect($dsn, $dbuser, $dbpass, \%attr);

my $stmt = "select s.study,dd_version,dd_date,dd_auto from users_study as us, study as s, datadictionaries as dd where s.st_auto = us.study and s.st_auto = dd.study and dd.delstat = 0 and user = $uid and dd_auto = $dd";

my $r = rand();
my @data = $dbh->selectrow_array($stmt);
my $filename = "$data[0]_v$data[1]_$data[2].pdf";
$filename = "error.pdf" if (scalar(@data) == 0);
print $form->header( -type => 'application/x-pdf', -attachment => $filename );

my $pdf = PDF::Create->new('filename'     => '-',
                           'Author'       => 'ViPAR',
                           'Title'        => "Data Dictionary for $data[0] v$data[1] $data[2]",
                           'CreationDate' => [ localtime ], );

my $a4 = $pdf->new_page('MediaBox' => $pdf->get_page_size('A4'));
my $page = $a4->new_page;
my $f1 = $pdf->font('BaseFont' => 'Helvetica');

if ($filename eq "error.pdf"){
 # Write error
 $page->stringc($f1, 20, 10, 10, "Permission Denied");
 }
else {
 # Prepare a Title page
 $page->stringc($f1, 40, 306, 426, "$data[0]");
 $page->stringc($f1, 20, 306, 396, "Data Dictionary - version $data[1]");
 $page->stringc($f1, 20, 306, 300, "$data[2]");

 my $stmt = "select v.v_auto, v.variable, v.description, vt.type, v.type from variables as v, datadictionaries_variables as dv, variables_type as vt where dv.variable = v.v_auto and v.type = vt.vt_auto and dv.dd_version = $dd and v.delstat = 0 order by variable asc";
 my $query = $dbh->prepare($stmt);
 $query->execute();

 my $pc = 1;
 while (my @v = $query->fetchrow_array()){
  if ($pc % 2 != 0){
   $page = $a4->new_page;
   $page->string($f1, 25, 50, 750, "$v[1] - $v[2]");
   $page->string($f1, 20, 50, 720, "$v[3]");
   my $str = &write_vdata($v[0],$v[4]);
   $page->printnl($str, $f1, 15, 50, 700);
   }
  else {
   $page->string($f1, 25, 50, 400, "$v[1] - $v[2]");
   $page->string($f1, 20, 50, 370, "$v[3]");
   my $str = &write_vdata($v[0],$v[4]);
   $page->printnl($str, $f1, 15, 50, 350);
   }
  $pc++;
  }

  $query->finish();

}

$dbh->disconnect();

# Close the file and write the PDF
$pdf->close;

sub err_login {
print $cgi->header();
print $cgi->start_html(
 -title=>'Virtual Pooling and Analysis of Research - ViPAR',
 -style=>{'src'=>"/viparstyle/vipar.css"}
 );

my $url = '/vipar';
print "<script>alert(\"Your login to ViPAR has timed out (or you have not logged in yet). You will be returned to the login page. If you have any further problems, please contact the site administrators.\");</script>";
print $cgi->end_html();

print "<meta http-equiv=\"refresh\" content=\"0;URL=$url\">\n";
exit(1);
}

sub write_vdata {
my $v = shift;
my $vt = shift;
my $string = "";

if ($vt == 1){ # categorical
 # get all categories for this variable
 my $query = "select cat, code from variables_cat where variable = \"$v\" order by cat asc";
 my @cats = ();
 $string = "\nCategories\n\n";
 foreach my $cat (@{$dbh->selectall_arrayref($query)}){
  $string .= "$cat->[0] => $cat->[1]\n";
  }
 }
elsif ($vt == 2){ # continuous
 my $query = "select min, max, prec from variables_con where variable = \"$v\"";
 my $result = $dbh->selectall_arrayref($query);
 my $min = $result->[0]->[0];
 my $max = $result->[0]->[1];
 my $prec = $result->[0]->[2];
 $string = "\nMin = $min\nMax = $max\nPrecision = $prec\n";
 }
elsif ($vt == 3){ # date
 my $query = "select min, max from variables_dat where variable = \"$v\"";
 my $result = $dbh->selectall_arrayref($query);
 my $min = $result->[0]->[0];
 my $max = $result->[0]->[1];
 $string = "\nMin = $min\nMax = $max\n";
 }

# get missing
my $stmt = "select m.value, m.description from missing as m, variables_missing as vm where vm.variable = $v and m.m_auto = vm.missing and m.delstat = 0";
$string .= "\nMissing Values\n\n";
foreach my $mis (@{$dbh->selectall_arrayref($stmt)}){
  $string .= "$mis->[0] => $mis->[1]\n";
  }

return($string);
}
