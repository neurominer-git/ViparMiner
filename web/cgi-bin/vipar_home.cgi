#!/usr/bin/perl

use strict;
use DBI;
use CGI;
use CGI::Carp qw(fatalsToBrowser);
use CGI::Session;
use CGI::Cookie;
use File::DirList;
use AppConfig;

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

my $dbconfig = AppConfig->new();
my $dbconfig_file = $ENV{'VIPAR_ROOT'}."/daemon/current/db.conf";

#define db vars
$dbconfig->define("database_name=<undef>");
$dbconfig->define("database_adminuser=<undef>");
$dbconfig->define("database_adminpass=<undef>");
$dbconfig->define("database_queryuser=<undef>");
$dbconfig->define("database_querypass=<undef>");
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

# see what privileges the user has and thus what management interfaces to display
my %user_priv = ();
# get the value of IT from the users table for this user as this gives special privs to add users, studies, variables, DataDictionaries, Sites, servers, resources, projects
$user_priv{'it'} = $dbh->selectrow_array("select it from users where u_auto = $uid and delstat = 0");
# also check if this user is a study lead the relevant management scripts will take care of which study they can access
$user_priv{'lead'} = $dbh->selectrow_array("select priv from users_study where priv = 2 and user = $uid");
# also check if this user is a data certification manager to access the data certification interface
$user_priv{'cert'} = $dbh->selectrow_array("select priv from users_study where priv = 3 and user = $uid");

# get the projects this user has access to (irresective of "display" flag")
my $stmt = "select p.p_auto, p.project from projects as p, users_projects as up where p.p_auto = up.project and p.delstat = 0 and up.user = $uid order by p.project asc";
my $query = $dbh->prepare($stmt);
$query->execute();
my %projects = ();
while (my @data = $query->fetchrow_array()){
 $projects{$data[0]} = $data[1];
 }
$query->finish();

# get the projects this user isnt a part of, that are displayable
$stmt = "select p_auto, project,display from projects where display=1 and delstat = 0 order by project asc";
$query = $dbh->prepare($stmt);
$query->execute();
my %otherprojects = ();
while (my @data = $query->fetchrow_array())
{
	#ignore ones we already have listed in the projects
	$otherprojects{$data[0]} = $data[1] unless (exists($projects{$data[0]}));
}
$query->finish();

my ($uname) = $dbh->selectrow_array("select username from users where u_auto = $uid and delstat = 0");
my $jsrnd = sprintf("%.2f",rand());

print $cgi->header( -cookie=>[$cookie], -charset=>'utf-8' );
print $cgi->start_html(
	-title=>'ViPAR Web based Analysis Portal - Project Manager',
	-style=>[ {'src'=>"/viparstyle/vipar.css"} ],
	-script=>[ {-type=>'text/javascript',-src=>'/viparjs/jquery-1.4.2.js'}, 
                   {-type=>'text/javascript',-src=>"/viparjs/vipar.js?rnd=$jsrnd"},
                   {-type=>'text/javascript',-src=>'/viparjs/CollapsibleLists.compressed.js'} ],
	-head => [ $cgi->meta({ -http_equiv => 'Pragma', -content => 'no-cache' }),
		$cgi->meta({ -http_equiv => 'Expires', -content => '-1' }) ]
	);

# Show projects user has access to
print "<div class=\"logout\">$uname<br>[ <a href=\"/viparcgi/vipar_logout.cgi\">Logout</a> ]</div>\n";
print "<div class=\"projmenu\"><h2>Welcome " . ucfirst($uname) . "!<br></h2>\n";
print "<a href=\"/viparcgi/vipar_home.cgi\">Home</a><br>\n";
if ( ($user_priv{'it'} == 1) || ($user_priv{'lead'} == 2) ) {
 print "<ul id=\"manage\" class=\"collapsibleList\">";
 print "<li>Manage<ul>\n";
 print "<li><span class=\"link\" onclick=\"new_user();\">Users</span></li>\n" if $user_priv{'it'} == 1;
 print "<li><span class=\"link\" onclick=\"new_study();\">Studies</span></li>\n" if $user_priv{'it'} == 1;
 print "<li><span class=\"link\" onclick=\"new_vardd();\">Variables and DataDictionaries</span></li>\n";
 print "<li><span class=\"link\" onclick=\"new_res();\">Resources</span></li>\n";
 print "<li><span class=\"link\" onclick=\"new_proj();\">Projects</span></li>\n";
 print "<li><span class=\"link\" onclick=\"do_cert();\">Certification</span></li>\n";
 print "</ul></li></ul>\n";
 print "<script type=\"text/javascript\">CollapsibleLists.applyTo(document.getElementById('manage'));</script>";
 }
elsif ( $user_priv{'cert'} == 3 ) {
 print "<ul id=\"manage\" class=\"collapsibleList\">";
 print "<li>Manage<ul>\n";
 print "<li><span class=\"link\" onclick=\"do_cert();\">Certification</span></li>\n";
 print "</ul></li></ul>\n";
 print "<script type=\"text/javascript\">CollapsibleLists.applyTo(document.getElementById('manage'));</script>";
 }

print "<br>Your Projects<br><br>\n";
foreach (sort { $projects{$a} cmp $projects{$b} } keys %projects){
 print "<img src=\"/viparimages/project_small1.png\" /><span class=\"link\" onclick=\"projheader($_,'h');\">". $projects{$_} . "</span><br>\n";
 }

print "<BR><br>Other Projects<br><br>\n";
foreach (sort { $otherprojects{$a} cmp $otherprojects{$b} } keys %otherprojects){
 print "<img src=\"/viparimages/project_small1.png\" /><span class=\"link\" onclick=\"projheader($_,'h');\">". $otherprojects{$_} . "</span><br>\n";
 }

print "</div>";

print "<div id='runres' class='projdetails'>\n";

print $cgi->h2("The ViPAR Analysis Portal");
print $cgi->p("Welcome to the ViPAR Analysis Portal.");
print $cgi->p("Browse the ongoing and completed projects below as well as the official Data Dictionary releases for each version of the database. If you have any ongoing projects you should see them on the left. The status of each ViPAR site can be seen below.");
print $cgi->p("If you have problems or suggestion please contact your site administrators</a>");

print "<div class=\"spacer\"></div>";
print "<div class=\"fileman\" id=\"files\">Data Dictionaries<br><br>";
print "<table><tr>\n";

# Need to make this dynamic and pull the DDs from the the database and into a Word doc

# use the id to find the data dictionaries within each study the user belongs
my $stmt = "select s.study,dd_version,dd_date,dd_auto from users_study as us, study as s, datadictionaries as dd where s.st_auto = us.study and s.st_auto = dd.study and dd.delstat = 0 and s.delstat = 0 and user = $uid";

my $query = $dbh->prepare($stmt);
$query->execute();
my $row = 1; 
while (my @data = $query->fetchrow_array()){
 $data[1] =~ s/\s+/_/;
 $data[1] =~ s/\W+//;
 $data[2] =~ s/\s+/_/;
 $data[2] =~ s/\W+//;
 print "<td><a href=\"/viparcgi/vipar_getdd.cgi?dd=$data[3]\"><img src=\"/viparimages/pdf.png\" />&nbsp;&nbsp;$data[0]_v$data[1]_$data[2]</td></a>";
 # could store DD remotely and link here too
 #print "<td><a target=\"_blank\" href=\"https://drive.google.com/open?id=XYZ\"><img src=\"/viparimages/pdf.png\" />&nbsp;&nbsp;$data[0]_v$data[1]_$data[2]</td></a>";
 print "</tr><tr>" if $row % 3 == 0;
 }

print "</tr></table>"; 
print "</div>";

print "<div id='sitestat' class='sitestat'>Site Status\n";
# The licence for the flags says we need to put a reference to the authors. This was the easiest way to do it.
print "<div class='credit'>www.icondrawer.com</div>";

my $stmt = "select country,server,resource,available,Lastcheck,r.study from resources as r,server as s,site as si, users_study as us where r.server=s.sv_auto and s.site=si.s_auto and r.study=us.study and r.delstat = 0 and us.user = $uid order by sv_auto asc";

my $query = $dbh->prepare($stmt);
$query->execute();
my %sites = ();
 
while (my @data = $query->fetchrow_array()){
 $sites{$data[0]}{$data[2]}{'server'} = $data[1];
 $sites{$data[0]}{$data[2]}{'available'} = $data[3];
 $sites{$data[0]}{$data[2]}{'Lastcheck'} = $data[4];
 }
$query->finish();

#check if any sites are configured
my @k = keys %sites;
if ($#k<0){
 print "<div class=\"red\">No site resources are configured yet</div>";
 }
else {
 foreach my $site (sort {$a cmp $b} keys %sites){
  print "<div style=\"float:left\">";
  print "<table style=\"padding:8px\"><tr>";
  print "<td>";
  print "<td id=\"tdpop\"><img src=\"/viparimages/flags/$site\.png\"/>
  <div style=\"position:absolute; top:-120px; z-index:9;\">$site<br>\n";
  my $status = 0;
  foreach my $rs (sort {$a cmp $b} keys %{$sites{$site}}) {
   my $ok = $sites{$site}{$rs}{'available'} == 1 ? "OK" : "notOK";
   print "$rs - $ok \@ $sites{$site}{$rs}{'Lastcheck'}<br>\n";
   # here need to use the resources_tables table to get all the strings for each table to display for this resource
   my $stmt = "select rt.cstring from resources_tables as rt, resources as r where rt.resid = r.r_auto and r.delstat = 0 and resource = \"$rs\" order by rt.cstring asc";

   my $query = $dbh->prepare($stmt);
   $query->execute();
   while (my @data = $query->fetchrow_array()){
    print "$data[0]<br>";
    }
   $query->finish();
   $status += $sites{$site}{$rs}{'available'};
   }
  print "</div></td>";
#  print "<td><img src=\"/viparimages/flags/$site\.png\"/></a></td>";
  if ($status == (1 * scalar(keys %{ $sites{$site} }))){ # all sites are OK
   print "<td><img src=\"/viparimages/green_light.png\"/></td>";
   }
  elsif ($status == (-1 * scalar(keys %{ $sites{$site} }))){ # all sites are not OK
   print "<td><img src=\"/viparimages/red_light.png\"/></td>";
   }
  else { # one of the sites is not happy but the rest are fine
   print "<td><img src=\"/viparimages/yellow_light.png\"/></td>";
   }
  print "</tr></table>";
  print "</div>";
  }
 }

print "</div>";
print "<div id='results'></div>";

print $cgi->end_html();

# disconnect query user
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
