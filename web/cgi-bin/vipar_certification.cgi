#!/usr/bin/perl

use strict;
use DBI;
use CGI;
use CGI::Carp qw(fatalsToBrowser);
use CGI::Session;
use CGI::Cookie;
use Data::Dumper;
use AppConfig;
use IO::Socket::INET;

my $cgi = new CGI;
my $type = $cgi->param('type');
my $sname = $cgi->param('sname');
my $rsname = $cgi->param('rsname');
my $check = $cgi->param('check');

# Check for Cookie or err
my $sid = $cgi->cookie("VIPAR_CGISESSID") || &err_login();

my $session = CGI::Session->load($sid);
&err_login() if $session->is_expired();
$session->expire('+1h');
my %cookies = fetch CGI::Cookie;
my $cookie = $cookies{'VIPAR_CGISESSID'};
$cookie->expires('+1h');

my $uid = $session->param("userid");

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
foreach my $c (keys %conf)
{
        if ( !defined($dbconfig->get($c)) )
        {
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

#get details and check VIPARD is running
my $stmt = "select v_key,v_value from vipar_config where v_key in ('server_servername','server_execport','execkey')";
my %config = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($stmt)};

if (!keys %config)  #if nothing returned
{
	print $cgi->header();
	print $cgi->start_html(
		-title=>'Virtual Pooling and Analysis of Research data - ViPAR - site down!',);
	print "<p style=\"font-size:20px;font-family:verdana,geneva,sans-serif;color:red;\">Virtual Pooling and Analysis of Research data - VIPARD is n
ot currently running. Please contact the site administrators</p>";
	$cgi->end_html();

	$dbh->disconnect();

	exit(1);
}

$stmt="select email from users where username='viparadmin'";
my ($email) = $dbh->selectrow_array($stmt);
my $servername = $config{"server_servername"};
my $execport = $config{"server_execport"};
my $execkey = $config{"execkey"};

my ($uname) = $dbh->selectrow_array("select username from users where u_auto = $uid and delstat = 0");
print $cgi->header( -cookie=>[$cookie], -charset=>'utf-8' );

# see what privileges the user has and thus what management interfaces to display
my %user_priv = ();
# get the value of IT from the users table for this user as this gives special privs to add users, studies, variables, DataDictionaries, Sites, servers, resources, projects
$user_priv{'it'} = $dbh->selectrow_array("select it from users where u_auto = $uid and delstat = 0");
# also check if this user is a study lead the relevant management scripts will take care of which study they can access
$user_priv{'lead'} = $dbh->selectrow_array("select priv from users_study as us, users as u where u.u_auto = us.user and priv = 2 and user = $uid and delstat = 0");
# also check if this user is a data cert coordinator
$user_priv{'cert'} = $dbh->selectrow_array("select priv from users_study as us, users as u where u.u_auto = us.user and priv = 3 and user = $uid and delstat = 0");
$dbh->disconnect();

# Need to be either IT or Lead to run this script
if ( ($user_priv{'it'} + $user_priv{'lead'} + $user_priv{'cert'}) < 1 ){
 # Need to log this to the daemon
 # user $uid attempted to run $0 but does not have permission to do so.

 #log error to VIPARD log file
 my $sock = IO::Socket::INET->new(PeerAddr => $servername,
                                 PeerPort => $execport,
                                 Proto     => 'tcp') or die "can't connect to VIPARD: $!";
 $sock->autoflush(1);        
	
 #send exec key for verification
 print $sock "$execkey\n";
 print $sock "log\n"; #send log command	
 print $sock "error\n"; #send log level
 print $sock "User $uname has attempted to run $0 but does not have IT/Admin privileges";
 $sock->close(); 

 print $cgi->header();
 print $cgi->start_html(
       -title=>'Virtual Pooling and Analysis of Research - ViPAR',
       -style=>{'src'=>"/viparstyle/vipar.css"}
        );
 my $url = '/vipar';
 print "<script>alert(\"You are not authorised to access that part of ViPAR. You will be returned to the login page (and this login attempt recorded). Please contact the site administrators for more information.\");</script>";
 print $cgi->end_html();

 print "<meta http-equiv=\"refresh\" content=\"0;URL=$url\">\n";

 exit(1);
 }

############
# Interfaces
############

# Function to display the resources and whether they are certified or not (subroutine)
# Function to change the certification status and then display 

if ($type eq "cert"){
 $dbuser = $dbconfig->get("database_queryuser");
 $dbpass = $dbconfig->get("database_querypass");
 $dbh = DBI->connect($dsn, $dbuser, $dbpass, \%attr);
 # get all studies
 my $query = "";
 if ($user_priv{'it'} == 1){ $query = "select st_auto, s.study from study as s where delstat = 0"; }
 elsif ( ($user_priv{'lead'} == 2) || ($user_priv{'cert'} == 3) ){ $query = "select st_auto, s.study from study as s, users_study as us where s.st_auto = us.study and s.delstat = 0 and user = $uid and priv in (2,3)"; }
 my %studies = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($query)};
 $studies{0} = "-- Select Study --";
 
 print $cgi->h2("Select Study Name");
 print $cgi->popup_menu( -name=>'sname', -id=>'sname', -values=>[sort keys %studies], -labels=>\%studies, -onchange=>"get_scert(this.value,'scert');" );
 print "<div id=\"scert\"></div>";
 $dbh->disconnect();
 }
elsif ($type eq "cd"){
 # display
 &cert($sname) if $sname > 0;
 }
elsif ($type eq "cu"){
 # update
 $dbuser = $dbconfig->get("database_adminuser");
 $dbpass = $dbconfig->get("database_adminpass");
 my %attr = (
        RaiseError => 1,
        AutoCommit => 0
        );
 
 # connect to the database
 $dbh = DBI->connect($dsn, $dbuser, $dbpass, \%attr);
 my ($resource) = $dbh->selectrow_array("select resource from resources where r_auto = $rsname and delstat = 0");
 $dbh->do("lock table resources write");
 $dbh->do("update resources set cert = $check, cert_user = $uid, cert_date = NOW() where r_auto = $rsname");
 $dbh->do("unlock tables");
 $dbh->disconnect();

 #log error to VIPARD log file
 my $sock = IO::Socket::INET->new(PeerAddr => $servername,
                                 PeerPort => $execport,
                                 Proto     => 'tcp') or die "can't connect to VIPARD: $!";
 $sock->autoflush(1);

 #send exec key for verification
 print $sock "$execkey\n";
 print $sock "log\n"; #send log command 
 print $sock "warning\n"; #send log level
 
 if ($check>0)
 {
 	print $sock "User $uname has SET certification (for single project $check) for resource $resource";
 }
 elsif ($check==0)
 {
	print $sock "User $uname has SET certification (all projects) resource $resource";
 }
 else
 {
	print $sock "User $uname has UNSET certification for resource $resource";
 }
 $sock->close();

 # display
 &cert($sname);
 }

sub cert {

 $dbuser = $dbconfig->get("database_queryuser");
 $dbpass = $dbconfig->get("database_querypass");
 $dbh = DBI->connect($dsn, $dbuser, $dbpass, \%attr);

 # For the certification process the following values apply
 #  -1 = not certified and is the "Select Project" value in the drop down
 #  0 = certified for all studies
 #  > 0 = certified for a particular study

 print $cgi->start_multipart_form(
 -method=>'POST',
 -action=>'/viparcgi/vipar_certification.cgi',
 -name=>'cert',
 -id=>'cert',
 );

 # Get all projects
 my $query = "select p_auto, project from projects where study = $sname and delstat = 0";
 my %projects = map { $_->[0], "$_->[1]"} @{$dbh->selectall_arrayref($query)};
 my @proj_sort = sort { $projects{$a} cmp $projects{$b} } keys %projects;
 $projects{-1} = "Not Certified";
 $projects{0} = "All Projects";
 unshift @proj_sort, -1, 0;

 print $cgi->h2("Select Resource to certify");
 my $stmt = "select r_auto, resource, description, dd_version, dd_date, username, cert_date, cert from datadictionaries as dd, resources as r LEFT JOIN users as u on r.cert_user = u.u_auto where r.datadictionary = dd.dd_auto and r.study = $sname and r.delstat = 0 and dd.delstat = 0";
 my $query = $dbh->prepare($stmt);
 $query->execute();
 print "<table><tr><th>Resource</th><th>Description</th><th>Data Dictionary</th><th>Cert Status</th><th>Cert User</th><th>Cert Date</th></tr>";
 while (my @data = $query->fetchrow_array()){
  my %attr = ( $data[7] => {'selected'=>'yes'}  );
  my $cert = $data[7] > -1 ? $data[7] == 0 ? "cert" : "projcert" : "nocert";
  print "<tr class=\"$cert\"><td>$data[1]</td><td>$data[2]</td><td>$data[3] - $data[4]</td><td>";
  print $cgi->popup_menu( -name=>'certnocert', -id=>'certnocert', -values=>\@proj_sort, -labels=>\%projects, -attributes=>\%attr, -onchange=>"upcert(this.value,$data[0]);" );
  print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
  print "</td><td>$data[5]</td><td>$data[6]</td></tr>";
  }
 print "</table>";
 $query->finish();

 print $cgi->end_multipart_form();

 $dbh->disconnect();
 }

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

