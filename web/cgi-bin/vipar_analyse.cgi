#!/usr/bin/perl

BEGIN { $| = 1 }

use strict;
use Fcntl;             # for sysopen
use DBI;
use CGI;
use CGI::Carp qw(fatalsToBrowser);
use CGI::Session;
use CGI::Cookie;
use IO::Handle;
use DateTime;
use AppConfig;
use IO::Socket::INET;

# Check for Cookie or err
my $cgi = new CGI;
my $sid = $cgi->cookie("VIPAR_CGISESSID") || &err_login();

my $session = CGI::Session->load($sid);
&err_login() if $session->is_expired();
$session->expire('+1h');
my $uid = $session->param("userid");
my %cookies = fetch CGI::Cookie;
my $cookie = $cookies{'VIPAR_CGISESSID'};
$cookie->expires('+1h');

###############
# Get the input parameters
###############

# Read in the analysis name 
my $aname = $cgi->param('aname');
# remove potential problem characters
#$aname=~s/\+[][&;`'\\"|*?~<>^(){}\$\n\r#@]\///g if $aname ne "";
$aname=~s/ /_/g if $aname ne "";
$aname=~ tr/A-Za-z0-9_-//cd;

# Read in the analysis description (optional)
my $desc = $cgi->param('description');
#$desc=~s/[][&;`'\\"|*?~<>^(){}\$\n\r#@]\///g if $desc ne "";
$desc=~ tr/ A-Za-z0-9_-//cd;

# Read in the databases to use 
my @resources = $cgi->param('resources');
# Read in the variable names of the data
my @variables = $cgi->param('variables');
# Read in the user's stats package preference
my $stats = $cgi->param('package');
# Read in the user's syntax
my $syntax = $cgi->param('syntax');
#print SPACE "CGI val\n$syntax";
$syntax =~ s/\r//g;
#print SPACE "CGI val altered\n$syntax";
# Get the project number for the selected project
my $project = $cgi->param('proj');
# Store run related data for the email and log files
my $runlog = "";
my $string = "";

# some checks
my $err = "";
# has to be aname
$err .= "You must provide a short name for the analysis<br>" if $aname eq "";
# has to be variables
$err .= "You must select at least 1 variable for analysis<br>" if scalar(@variables) == 0;
# has to be resources
$err .= "You must select at least 1 resource to pull data from<br>" if scalar(@resources) == 0;
# has to be syntax
$err .= "You must supply some syntax<br>" if $syntax eq "";

# get where clause data
my $where = "";
foreach my $p ($cgi->param()){
 if ($p =~ m/(\w+)_where/){
  my $data = join("\t",split("\n",$cgi->param($p)));
  $where .= "$1:::$data\----";
  }
 }

$| = 1;

# print CGI header so that we see something happening
print $cgi->header( -cookie=>[$cookie], -charset=>'utf-8' );
print $cgi->start_html(
	-title=>'VIPAR Web based Analysis Portal - Analysis',
	-style=>{'src'=>"/viparstyle/vipar.css"},
	-script=>[ {-type=>'text/javascript',-src=>'/viparjs/jquery-1.4.2.js'}, 
	           {-type=>'text/javascript',-src=>'/viparjs/vipar.js'} ],
	-head => [ $cgi->meta({ -http_equiv => 'Pragma', -content => 'no-cache' }),
		   $cgi->meta({ -http_equiv => 'Expires', -content => '-1' }) ]
	);

my $dbconfig = AppConfig->new();
my $dbconfig_file = $ENV{'VIPAR_ROOT'}."/daemon/current/db.conf";

#define db vars
$dbconfig->define("database_name=<undef>");
$dbconfig->define("database_adminuser=<undef>");
$dbconfig->define("database_adminpass=<undef>");
$dbconfig->define("database_queryuser=<undef>");
$dbconfig->define("database_querypass=<undef>");
$dbconfig->define("database_remoteadminuser=<undef>");
$dbconfig->define("database_remoteadminpass=<undef>");
$dbconfig->define("database_remotequeryuser=<undef>");
$dbconfig->define("database_remotequerypass=<undef>");


$dbconfig->file($dbconfig_file);

#check all DB options are set
my %conf = $dbconfig->varlist("database_*");
foreach my $c (keys %conf)
{
        if ( !defined($dbconfig->get($c)) )
        {
		die "Option $c not set in config file $dbconfig_file ... exiting\n";
        }
}

# connect to DB
my $dsn = "dbi:mysql:".$dbconfig->get("database_name");
my $dbuser = $dbconfig->get("database_queryuser");
my $dbpass = $dbconfig->get("database_querypass");
my %attr = (
        RaiseError => 1,
        AutoCommit => 0
        );
my $dbh = DBI->connect($dsn, $dbuser, $dbpass, \%attr);

# get details from vipar_config table
my $stmt = "select v_key,v_value from vipar_config where v_key in ('server_servername','server_execport','execkey')";
my %config = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($stmt)};

if (!keys %config)  #if nothing returned
{
	print $cgi->header();
	print $cgi->start_html(
		-title=>'Virtual Pooling and Analysis of Research data - ViPAR - site down!',);
	print "<p style=\"font-size:20px;font-family:verdana,geneva,sans-serif;color:red;\">Virtual Pooling and Analysis of Research data - VIPARD is not currently running. Please contact the site administrators</p>";
	$cgi->end_html();

	$dbh->disconnect();

	exit(1);
}

if ($err eq ""){
print $cgi->h2("Thank you, your job has been submitted!");

$stmt="select email from users where username='viparadmin'";
my ($email) = $dbh->selectrow_array($stmt);
my $servername = $config{"server_servername"};
my $execport = $config{"server_execport"};
my $execkey = $config{"execkey"};

#log error to VIPARD log file
my $sock = IO::Socket::INET->new(PeerAddr => $servername,
                                 PeerPort => $execport,
                                 Proto     => 'tcp') or die "can't connect to VIPARD: $!";
#print "Successfully connected to $server:$port\n";
$sock->autoflush(1);    

# make the variables array in to a human readable comma separated list of variables separated by "."
# get the study id from the project
my $query = "select study from projects where p_auto = $project";
my @sname = $dbh->selectrow_array($query);
# get all tables
my $query = "select tid, name from dtables where study = $sname[0] and delstat = 0";
my %tables = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($query)};
# get all variables
my $query = "select v_auto, variable from variables where study = $sname[0] and delstat = 0";
my %vars = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($query)};

# now make a string for each
my @varar = ();
foreach my $vs (@variables){
 my ($t,$v) = split("_",$vs);
 push @varar, "$tables{$t}.$vars{$v}";
 }
my $varstring = join(",",@varar);

print $sock "$execkey\n";
print $sock "exec\n"; #command	
print $sock "$uid\n"; #uid
print $sock "$project\n"; #project
print $sock "$aname\n"; #aname
print $sock "$desc\n";
print $sock join(",",@resources)."\n"; #resources
#print $sock join(",",@variables)."\n"; #variables;
print $sock "$varstring\n"; #variables;
print $sock "$stats\n"; #stats pack
print $sock "$where\n"; # where clause data
print $sock "$syntax\n"; #syntax

$sock->close();
}
else {
 print $cgi->h2({-style=>'Color: red;'},"$err");
 }

print "<center>";
print "<input type=\"button\" value=\"Close this window\" onclick=\"self.close()\">";
print "</center>";
$cgi->end_html();

# disconnect the query user
$dbh->disconnect();

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


