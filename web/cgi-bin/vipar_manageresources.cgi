#!/usr/bin/perl

use strict;
use DBI;
use CGI;
use CGI::Carp qw(fatalsToBrowser);
use CGI::Session;
use CGI::Cookie;
use Locale::Country;
use Data::Dumper;
use Scalar::Util qw(looks_like_number);
use AppConfig;
use IO::Socket::INET;

my $cgi = new CGI;
my $type = $cgi->param('type');
my $action = $cgi->param('action');
my $sname = $cgi->param('sname');
my $stname = $cgi->param('stname');
my $ctname = $cgi->param('ctname');
my $stinst = $cgi->param('stinst');
my $srvport = $cgi->param('srvport');
my $rport = $cgi->param('rport');
my $rhost = $cgi->param('rhost');
my $ruser = $cgi->param('ruser');
my $rsname = $cgi->param('rsname');
my $rsdesc = $cgi->param('rsdesc');
my $ddname = $cgi->param('ddname');
my $ssr = $cgi->param('ssr');

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

$stmt = "select username from users where u_auto=$uid and delstat = 0";
my ($user_name) = $dbh->selectrow_array($stmt);
my $servername = $config{"server_servername"};
my $execport = $config{"server_execport"};
my $execkey = $config{"execkey"};

print $cgi->header( -cookie=>[$cookie], -charset=>'utf-8' );

# see what privileges the user has and thus what management interfaces to display
my %user_priv = ();
# get the value of IT from the users table for this user as this gives special privs to add users, studies, variables, DataDictionaries, Sites, servers, resources, projects
$user_priv{'it'} = $dbh->selectrow_array("select it from users where u_auto = $uid and delstat = 0");
# also check if this user is a study lead the relevant management scripts will take care of which study they can access
$user_priv{'lead'} = $dbh->selectrow_array("select priv from users_study as us, users as u where u.u_auto = us.user and priv = 2 and user = $uid and delstat = 0");

# Need to be either IT or Lead to run this script
if ( ($user_priv{'it'} + $user_priv{'lead'}) < 1 ){
	 # log error to VIPARD log file
	 my $sock = IO::Socket::INET->new(PeerAddr => $servername,
		                         PeerPort => $execport,
		                         Proto     => 'tcp') or die "can't connect to VIPARD: $!";
	 $sock->autoflush(1);

	 #send exec key for verification
	 print $sock "$execkey\n";
	 print $sock "log\n"; #send log command 
	 print $sock "error\n"; #send log level
	 print $sock "User $user_name has attempted to run $0 but does not have IT/Admin privileges";
	 $sock->close();


	 print $cgi->start_html(
		-title=>'Virtual Pooling and Analysis of Research - ViPAR',
		-style=>{'src'=>"/viparstyle/vipar.css"}
	);
	my $url = '/vipar';
	print "<script>alert(\"You are not authorised to access that part of ViPAR. You will be returned to the login page (and this login attempt recorded). Please contact the site administrators for more information.\");</script>";
	print $cgi->end_html();

	print "<meta http-equiv=\"refresh\" content=\"0;URL=$url\">\n";

	$dbh->disconnect();
	exit(1);
 }

############
# Interfaces
############

if ($type eq "nr"){
 # get all studies
 my $query = "";
 if ($user_priv{'it'} == 1){ $query = "select st_auto, s.study from study as s where delstat = 0"; }
 elsif ($user_priv{'lead'} == 2){ $query = "select st_auto, s.study from study as s, users_study as us where s.st_auto = us.study and s.delstat = 0 and user = $uid and priv = 2"; }
 my %studies = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($query)};
 $studies{0} = "-- Select Study --";
 
 print $cgi->h2("Select Study Name");
 print $cgi->popup_menu( -name=>'sname', -id=>'sname', -values=>[sort keys %studies], -labels=>\%studies, -onchange=>"get_ssr(this.value,'ssr');" );
 print "<div id=\"ssr\"></div>";
 }
elsif ($type eq "ssr"){
 if ($sname > 0){
  my %opts = (
 	1 => "Site",
 	2 => "Server",
 	3 => "Resource"
 	);
  $opts{0} = "-- Select Type --";
 
  print $cgi->h2("Select Type");
  print $cgi->popup_menu( -name=>'ssr_opt', -id=>'ssr_opt', -values=>[sort keys %opts], -labels=>\%opts, -onchange=>"get_ssr_info(this.value,$sname,'ssr_info')" );
  print $cgi->br();
  print $cgi->br();
  print $cgi->hr();
  print "<div id=\"ssr_info\"></div>";
  } 
 }

################
# Site
################

elsif ($type eq "ssri"){
 if ($sname > 0){

  if ($ssr == 1){
   # get all sites
   my $query = "select s_auto, shortname, fullname from site where study = $sname and delstat = 0";
   my %sites = map { $_->[0], "$_->[1] - $_->[2]"} @{$dbh->selectall_arrayref($query)};
   $sites{0} = "-- Select Site --";

   my %ctnames = map { $_, "$_" } sort {$a cmp $b} all_country_names();
   $ctnames{0} = "-- Select Country --"; 

################
# Add Site

   print $cgi->h2("Add New Site");

   print $cgi->start_multipart_form(
    -method=>'POST',
    -action=>'/viparcgi/vipar_manageresources.cgi',
    -name=>'newst',
    -id=>'newst',
    );

   print "<table><tr>";
   print "<td style=\"width:250px;\">";
   print $cgi->h2("Site name");
   print "<div id=\"stdiv\">";
   print $cgi->textfield( -name=>'stname', -id=>"stnamenewst", -size=>5, -maxlength=>5, -onblur=>"checkst(this.value,'cstdiv');", onkeyup=>"limchar(this);" );
   print $cgi->textfield( -name=>'stnamenewstlim', -id=>"stnamenewstlim", -size=>2, -readonly=>1, -value=>5 );
   print "<br><div id=\"cstdiv\">\n";
   print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
   print "</div>";
   print "</div>";
   print "</td><td valign=\"top\">";
   print $cgi->h2("Country");
   print $cgi->popup_menu( -name=>'ctname', -id=>'ctnamenewst', -labels=>\%ctnames, -values=>[sort keys %ctnames], -onChange=>"c2c(this.value,'stdiv');checkst(document.getElementById('stnamenewst').value,'cstdiv');" );
   print $cgi->hidden(-name=>'action', -default=>"newsite");
   print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
   print "</td></tr>";
   print "<tr><td colspan=\"2\">";
   print $cgi->h2("Institution Description");
   print $cgi->textfield( -name=>'stinst', -id=>"stinstnewst", -size=>50, -maxlength=>255, onkeyup=>"limchar(this);" );
   print $cgi->textfield( -name=>'stinstnewstlim', -id=>"stinstnewstlim", -size=>3, -readonly=>1, -value=>255 );
   print "</td></tr><table>";

   print "<table><tr><td style=\"text-align:right\"><br>";
   print $cgi->button(-name=>"sub_newst", -value=>"Submit", -onclick=>"check_st('newst');");
   print "</td>";
   print "<td></td><td><br>\n";
   print $cgi->reset(-value=>"Reset", -onclick=>"get_ssr_info(1,$sname,'ssr_info')");
   print "</td><td></td></tr>";
   print "</table><br>";

   print $cgi->end_multipart_form();
   print $cgi->br();
   print $cgi->hr();

################
# Update Site

   print $cgi->h2("Update Site");

   print $cgi->start_multipart_form(
    -method=>'POST',
    -action=>'/viparcgi/vipar_manageresources.cgi',
    -name=>'upst',
    -id=>'upst',
    );

   print $cgi->h2("Site");
   print $cgi->popup_menu( -name=>'stname', -id=>'stnameupst', -values=>[sort {$sites{$a} cmp $sites{$b}} keys %sites], -labels=>\%sites, -onchange=>"get_stinfo(this.value,'stinfo');" );
   print $cgi->hidden(-name=>'action',-default=>"updatesite");
   print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
   print "<div id=\"stinfo\"></div>";

   print $cgi->end_multipart_form();
   print $cgi->br();
   print $cgi->hr();

################
# Remove Site

   print $cgi->h2("Remove Site");

   print $cgi->start_multipart_form(
    -method=>'POST',
    -action=>'/viparcgi/vipar_manageresources.cgi',
    -name=>'remst',
    -id=>'remst',
    );

   print $cgi->h2("Site");
   print $cgi->popup_menu( -name=>'stname', -id=>'stnameremst', -values=>[sort  {$sites{$a} cmp $sites{$b}} keys %sites], -labels=>\%sites, -onchange=>"get_submit_st(this.value,'stdel',$sname);" );
   print $cgi->hidden(-name=>'action',-default=>"deletesite");
   print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
   print "<div id=\"stdel\"></div>";

   print $cgi->end_multipart_form();
   print $cgi->br();
   print $cgi->hr();
   }

################
# Server
################

  if ($ssr == 2){
   # get all sites
   my $query = "select s_auto, shortname, fullname from site where study = $sname and delstat = 0";
   my %sites = map { $_->[0], "$_->[1] - $_->[2]"} @{$dbh->selectall_arrayref($query)};
   $sites{0} = "-- Select Site --";

   # get all servers
   my $query = "select sv_auto, shortname, port from site, server where site.s_auto = server.site and site.study = $sname and server.delstat = 0 and site.delstat = 0";
   my %servers = map { $_->[0], "$_->[1] - $_->[2]"} @{$dbh->selectall_arrayref($query)};
   $servers{0} = "-- Select Server --";

################
# Add Server

   print $cgi->h2("Add New Server");

   print $cgi->start_multipart_form(
    -method=>'POST',
    -action=>'/viparcgi/vipar_manageresources.cgi',
    -name=>'newsrv',
    -id=>'newsrv',
    );

   print "<table><tr>";
   print "<td style=\"width:250px;\">";
   print $cgi->h2("Local port");
   print "<div id=\"srvdiv\">";
   print $cgi->textfield( -name=>'srvport', -id=>"srvportnewsrv", -size=>5, -maxlength=>5, -onblur=>"checksrv(this.value,'csrvdiv');", onkeyup=>"limchar(this);" );
   print $cgi->textfield( -name=>'srvportnewsrvlim', -id=>"srvportnewsrvlim", -size=>2, -readonly=>1, -value=>5 );
   print "<br><div id=\"csrvdiv\">\n";
   print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
   print "</div>";
   print "</div>";
   print "</td></tr>";
   print "<tr><td valign=\"top\">";
   print $cgi->h2("Remote Site");
   print $cgi->popup_menu( -name=>'stname', -id=>'stnamenewsrv', -values=>[sort {$sites{$a} cmp $sites{$b}} keys %sites], -labels=>\%sites );
   print "</td><td>";
   print $cgi->h2("Remote host");
   print $cgi->textfield( -name=>'rhost', -id=>"rhostnewsrv", -size=>50, -maxlength=>100, onkeyup=>"limchar(this);" );
   print $cgi->textfield( -name=>'rhostnewsrvlim', -id=>"rhostnewsrvlim", -size=>3, -readonly=>1, -value=>100 );
   print "</td></tr><tr><td>";
   print $cgi->h2("Remote port");
   print $cgi->textfield( -name=>'rport', -id=>"rportnewsrv", -default=>22, -size=>5, -maxlength=>5, onkeyup=>"limchar(this);" );
   print $cgi->textfield( -name=>'rportnewsrvlim', -id=>"rportnewsrvlim", -size=>2, -readonly=>1, -value=>3 );
   print "</td><td>";
   print $cgi->h2("Remote user");
   print $cgi->textfield( -name=>'ruser', -id=>"rusernewsrv", -default=>"vipar", -size=>20, -maxlength=>20, onkeyup=>"limchar(this);" );
   print $cgi->textfield( -name=>'rusernewsrvlim', -id=>"rusernewsrvlim", -size=>2, -readonly=>1, -value=>15 );
   print $cgi->hidden(-name=>'action', -default=>"newserver");
   print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
   print "</td></tr><table>";

   print "<table><tr><td style=\"text-align:right\"><br>";
   print $cgi->button(-name=>"sub_newsrv", -value=>"Submit", -onclick=>"check_srv('newsrv');");
   print "</td>";
   print "<td></td><td><br>\n";
   print $cgi->reset(-value=>"Reset", -onclick=>"get_ssr_info(2,$sname,'ssr_info')");
   print "</td><td></td></tr>";
   print "</table><br>";

   print $cgi->end_multipart_form();
   print $cgi->br();
   print $cgi->hr(); 

################
# Update Server

   print $cgi->h2("Update Server");

   print $cgi->start_multipart_form(
    -method=>'POST',
    -action=>'/viparcgi/vipar_manageresources.cgi',
    -name=>'upsrv',
    -id=>'upsrv',
    );

   print $cgi->h2("Server");
   print $cgi->popup_menu( -name=>'srvport', -id=>'srvportupsrv', -values=>[sort {$servers{$a} cmp $servers{$b}} keys %servers], -labels=>\%servers, -onchange=>"get_srvinfo(this.value,'srvinfo');" );
   print $cgi->hidden(-name=>'action',-default=>"updateserver");
   print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
   print "<div id=\"srvinfo\"></div>";

   print $cgi->end_multipart_form();
   print $cgi->br();
   print $cgi->hr();

################
# Remove Server

   print $cgi->h2("Remove Server");

   print $cgi->start_multipart_form(
    -method=>'POST',
    -action=>'/viparcgi/vipar_manageresources.cgi',
    -name=>'remsrv',
    -id=>'remsrv',
    );

   print $cgi->h2("Server");
   print $cgi->popup_menu( -name=>'srvport', -id=>'srvportremst', -values=>[sort  {$servers{$a} cmp $servers{$b}} keys %servers], -labels=>\%servers, -onchange=>"get_submit_srv(this.value,'srvdel',$sname);" );
   print $cgi->hidden(-name=>'action',-default=>"deleteserver");
   print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
   print "<div id=\"srvdel\"></div>";

   print $cgi->end_multipart_form();
   print $cgi->br();
   print $cgi->hr();

################
# Generate Xinetd Syntax

   print $cgi->h2("Generate Xinetd Syntax");

   print $cgi->start_multipart_form(
    -method=>'POST',
    -action=>'/viparcgi/vipar_manageresources.cgi',
    -name=>'xsyntax',
    -id=>'xsyntax'
    );

   print $cgi->h2("Select Server");
   print $cgi->popup_menu( -name=>'srvport', -id=>'srvportxsyn', -values=>[sort {$servers{$a} cmp $servers{$b}} keys %servers], -labels=>\%servers );
   print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
   print $cgi->hidden(-name=>'action',-default=>"xsyntax");
 
   print "<table><tr><td style=\"text-align:right\"><br>";
   print $cgi->button(-name=>"sub_xsyn", -value=>"Submit", -onclick=>"x_syntax('xsyntax');");
   print "</td>";
   print "<td></td><td><br>\n";
   print $cgi->reset(-value=>"Reset", -onclick=>"get_ssr_info(2,$sname,'ssr_info')");
   print "</td><td></td></tr>";
   print "</table><br>";
 
   print $cgi->end_multipart_form();
   print $cgi->br();
   print $cgi->hr();
   }

  }

################
# Resource
################

 if ($ssr == 3){

  # get all resources
  my $query = "select r_auto, resource, description from resources where study = $sname and delstat = 0";
  my %resources = map { $_->[0], "$_->[1] - $_->[2]"} @{$dbh->selectall_arrayref($query)};
  $resources{0} = "-- Select Resource --";

  # get all servers
  $query = "select sv_auto, shortname, port from site, server where site.s_auto = server.site and site.study = $sname and server.delstat = 0 and site.delstat = 0";
  my %servers = map { $_->[0], "$_->[1] - $_->[2]"} @{$dbh->selectall_arrayref($query)};
  $servers{0} = "-- Select Server --"; 

  # get all datadictionaries
  $query = "select dd_auto, dd_version, dd_date from datadictionaries where study = $sname and delstat = 0";
  my %datadictionaries = map { $_->[0], "$_->[1] - $_->[2]"} @{$dbh->selectall_arrayref($query)};
  $datadictionaries{0} = "-- Select Data Dictionary --";

################
# Add Resource

  print $cgi->h2("Add Resource");

  print $cgi->start_multipart_form(
   -method=>'POST',
   -action=>'/viparcgi/vipar_manageresources.cgi',
   -name=>'newrs',
   -id=>'newrs',
   );

  print "<table><tr>";
  print "<td style=\"width:250px;\">";
  print $cgi->h2("Resource name");
  print "<div id=\"stdiv\">";
  print $cgi->textfield( -name=>'rsname', -id=>"rsnamenewrs", -size=>50, -maxlength=>50, -onblur=>"checkrs(this.value,'crsdiv');", onkeyup=>"limchar(this);" );
  print $cgi->textfield( -name=>'rsnamenewrslim', -id=>"rsnamenewrslim", -size=>2, -readonly=>1, -value=>50 );
  print "<br><div id=\"crsdiv\">\n";
  print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
  print "</div>";
  print "</div>";
  print "</td><td valign=\"top\">";
  print $cgi->h2("Description");
  print $cgi->textfield( -name=>'rsdesc', -id=>"rsdescnewrs", -size=>50, -maxlength=>255, onkeyup=>"limchar(this);" );
  print $cgi->textfield( -name=>'rsdescnewrslim', -id=>"rsdescnewrslim", -size=>3, -readonly=>1, -value=>255 );
  print "</td></tr>";
  print "<tr><td>";
  print $cgi->h2("Server");
  print $cgi->popup_menu( -name=>'srvport', -id=>'srvportnewrs', -labels=>\%servers, -values=>[sort keys %servers] );
  print "</td><td>";
  print $cgi->h2("Data Dictionary");
  print $cgi->popup_menu( -name=>'ddname', -id=>'ddnamenewrs', -labels=>\%datadictionaries, -values=>[sort keys %datadictionaries] );
  print $cgi->hidden(-name=>'action', -default=>"newresource");
  print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
  print "</td></tr><table>";

  print "<table><tr><td style=\"text-align:right\"><br>";
  print $cgi->button(-name=>"sub_newrs", -value=>"Submit", -onclick=>"check_rs('newrs');");
  print "</td>";
  print "<td></td><td><br>\n";
  print $cgi->reset(-value=>"Reset", -onclick=>"get_ssr_info(3,$sname,'ssr_info')");
  print "</td><td></td></tr>";
  print "</table><br>";

  print $cgi->end_multipart_form();
  print $cgi->br();
  print $cgi->hr(); 

################
# Update Resource

  print $cgi->h2("Update Resource");

  print $cgi->start_multipart_form(
   -method=>'POST',
   -action=>'/viparcgi/vipar_manageresources.cgi',
   -name=>'uprs',
   -id=>'uprs'
   );

  print $cgi->h2("Resource");
  print $cgi->popup_menu( -name=>'rsname', -id=>'rsnameuprs', -values=>[sort {$resources{$a} cmp $resources{$b}} keys %resources], -labels=>\%resources, -onchange=>"get_rsinfo(this.value,'rsinfo');" );
  print $cgi->hidden(-name=>'action',-default=>"updateresource");
  print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
  print "<div id=\"rsinfo\"></div>";

  print $cgi->end_multipart_form();
  print $cgi->br();
  print $cgi->hr();

################
# Remove Resource

  print $cgi->h2("Remove Resource");

  print $cgi->start_multipart_form(
   -method=>'POST',
   -action=>'/viparcgi/vipar_manageresources.cgi',
   -name=>'remrs',
   -id=>'remrs'
   );

  print $cgi->h2("Resource");
  print $cgi->popup_menu( -name=>'rsname', -id=>'rsnameremrs', -values=>[sort  {$resources{$a} cmp $resources{$b}} keys %resources], -labels=>\%resources, -onchange=>"get_submit_rs(this.value,'rsdel',$sname);" );
  print $cgi->hidden(-name=>'action',-default=>"deleteresource");
  print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
  print "<div id=\"rsdel\"></div>";

  print $cgi->end_multipart_form();
  print $cgi->br();
  print $cgi->hr();

################
# Generate Table Syntax

  print $cgi->h2("Generate Table Syntax");

  print $cgi->start_multipart_form(
   -method=>'POST',
   -action=>'/viparcgi/vipar_manageresources.cgi',
   -name=>'rssyntax',
   -id=>'rssyntax'
   );

  print $cgi->h2("Select Resource");
  print $cgi->popup_menu( -name=>'rsname', -id=>'rsnamerssyn', -values=>[sort {$resources{$a} cmp $resources{$b}} keys %resources], -labels=>\%resources );
  print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
  print $cgi->hidden(-name=>'action',-default=>"rssyntax");
  
  print "<table><tr><td style=\"text-align:right\"><br>";
  print $cgi->button(-name=>"sub_rssyn", -value=>"Submit", -onclick=>"rs_syntax('rssyntax');");
  print "</td>";
  print "<td></td><td><br>\n";
  print $cgi->reset(-value=>"Reset", -onclick=>"get_ssr_info(3,$sname,'ssr_info')");
  print "</td><td></td></tr>";
  print "</table><br>";

  print $cgi->end_multipart_form();
  print $cgi->br();
  print $cgi->hr();

  }

 }

################
# Sites
################
elsif ( $type eq "cst" ){
 # check if a site shortname exists with this name
 $stname =~ s/\s+//g;
 if ($stname eq ""){
  print "<span class=\"warn\">Site name cannot be blank</span>";
  print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
  }
 else {
  # Note that this does not take delstat in to account and will complain even if "deleted" sites share the same name
  # the db admin can remove sites with the new name BUT as the db is InnoDB this will remove any data for that site
  my $check = $dbh->selectrow_array("select shortname from site where shortname = \"$stname\"");
  if ($check) {
   print "<span class=\"warn\">A site exists with this name</span>";
   print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
   }
  else {
   print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>1);
   }
  }
 }
elsif ( $type eq "c2c"){
 my $st = uc(country2code("$ctname",LOCALE_CODE_ALPHA_3));
 print $cgi->textfield( -name=>'stname', -id=>"stnamenewst", -value=>"$st", -size=>5, -maxlength=>5, -onblur=>"checkst(this.value,'cstdiv');", onkeyup=>"limchar(this);" );
 my $val = 5 - length($st);
 print $cgi->textfield( -name=>'stnamenewstlim', -id=>"stnamenewstlim", -size=>2, -readonly=>1, -value=>$val );
 print "<br><div id=\"cstdiv\">\n";
 print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
 print "</div>"
 }
elsif ( $type eq "sti"){
 
 if ($stname > 0){

  my @stdata = $dbh->selectrow_array("select country, fullname from site where s_auto = \"$stname\" and delstat = 0");

  my %ctnames = map { $_, "$_" } sort {$a cmp $b} all_country_names();
  $ctnames{0} = "-- Select Country --";
  my %attr = undef;
  foreach my $ct (keys %ctnames){ $attr{$ct} = $stdata[0] eq $ct ? {'selected'=>'yes'} : {}; }

  print $cgi->h2("Country");
  print $cgi->popup_menu( -name=>'ctname', -id=>'ctnameupst', -labels=>\%ctnames, -values=>[sort keys %ctnames], -attributes=>\%attr );
  print $cgi->hidden(-name=>'action', -default=>"updatesite");
  print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
  print $cgi->h2("Institution Description");
  print $cgi->textfield( -name=>'stinst', -id=>"stinstupst", -size=>50, -maxlength=>255, -value=>"$stdata[1]", onkeyup=>"limchar(this);" );
  my $val = 255 - length($stdata[1]);
  print $cgi->textfield( -name=>'sinstupstlim', -id=>"stinstupstlim", -size=>3, -readonly=>1, -value=>$val );

  print "<table><tr><td></td><td style=\"text-align:right\"><br>";
  print $cgi->button(-name=>"sub_upst", -value=>"Submit", -onclick=>"check_st('upst');");
  print "</td><td></td><td><br>\n";
  print $cgi->reset(-value=>"Reset", -onclick=>"get_stinfo($stname,'stinfo');");
  print "</td></tr></table><br>";
  }
 }
elsif ( $type eq "rst"){
 unless ($stname == 0) {
  print "<br>";
  print "<table><tr><td>";
  print $cgi->button(-name=>"sub_remst", -value=>"Submit", -onclick=>"check_st('remst');");
  print "</td><td>";
  print $cgi->reset(-value=>"Reset", -onclick=>"get_ssr_info(1,$sname,'ssr_info')");
  print "</td></tr></table>";
  }
 }

################
# Server
################
elsif ( $type eq "csrv" ){
 # check if a server port is already assigned - regardless of study
 if ($srvport eq ""){
  print "<span class=\"warn\">Port cannot be blank</span>";
  print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
  }
 elsif (!looks_like_number($srvport)){
  print "<span class=\"warn\">Port value must be number</span>";
  print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
  }
 else {
  # Note that this does not take delstat in to account and will complain even if "deleted" server share the same name
  # the db admin can remove servers with the new name BUT as the db is InnoDB this will remove any data for that server
  my @check = $dbh->selectrow_array("select port, study from server, site where site = s_auto and port = $srvport");
  if ($check[0]) {
   print "<span class=\"warn\">This port is already assigned";
   print $check[1] == $sname ? " in this study" : " in a different study";
   print "</span>";
   print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
   }
  else {
   print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>1);
   }
  }
 }
elsif ( $type eq "srvi"){
 if ($srvport > 0){

  my @srvdata = $dbh->selectrow_array("select site,remotehost,remoteport,remoteuser from server where sv_auto = \"$srvport\" and delstat = 0");

  # get all sites
  my $query = "select s_auto, shortname, fullname from site where study = $sname and delstat = 0";
  my %sites = map { $_->[0], "$_->[1] - $_->[2]"} @{$dbh->selectall_arrayref($query)};
  $sites{0} = "-- Select Site --";

  my %attr = undef;
  foreach my $st (keys %sites){ $attr{$st} = $srvdata[0] eq $st ? {'selected'=>'yes'} : {}; }

  print "<table>";
  print "<tr><td valign=\"top\">";
  print $cgi->h2("Remote Site");
  print $cgi->popup_menu( -name=>'stname', -id=>'stnameupsrv', -values=>[sort {$sites{$a} cmp $sites{$b}} keys %sites], -labels=>\%sites, -attributes=>\%attr );
  print "</td><td>";
  print $cgi->h2("Remote host");
  print $cgi->textfield( -name=>'rhost', -id=>"rhostupsrv", -size=>50, -maxlength=>100, -default=>$srvdata[1], -onkeyup=>"limchar(this);" );
  my $val = 100 - length($srvdata[1]);
  print $cgi->textfield( -name=>'rhostupsrvlim', -id=>"rhostupsrvlim", -size=>3, -readonly=>1, -value=>$val );
  print "</td></tr><tr><td>";
  print $cgi->h2("Remote port");
  print $cgi->textfield( -name=>'rport', -id=>"rportupsrv", -size=>5, -maxlength=>5, -default=>$srvdata[2], -onkeyup=>"limchar(this);" );
  $val = 5 - length($srvdata[2]);
  print $cgi->textfield( -name=>'rportupsrvlim', -id=>"rportupsrvlim", -size=>2, -readonly=>1, -value=>$val );
  print "</td><td>";
  print $cgi->h2("Remote user");
  print $cgi->textfield( -name=>'ruser', -id=>"ruserupsrv", -size=>20, -maxlength=>20, -default=>$srvdata[3], -onkeyup=>"limchar(this);" );
  $val = 20 - length($srvdata[3]);
  print $cgi->textfield( -name=>'ruserupsrvlim', -id=>"ruserupsrvlim", -size=>2, -readonly=>1, -value=>$val );
  print $cgi->hidden(-name=>'action', -default=>"updateserver");
  print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
  print "</td></tr><table>";

  print "<table><tr><td></td><td style=\"text-align:right\"><br>";
  print $cgi->button(-name=>"sub_upsrv", -value=>"Submit", -onclick=>"check_srv('upsrv');");
  print "</td><td></td><td><br>\n";
   print $cgi->reset(-value=>"Reset", -onclick=>"get_srvinfo($srvport,'srvinfo');");
  print "</td></tr></table><br>";
  }
 } 
elsif ( $type eq "rsrv"){
 unless ($srvport == 0) {
  print "<br>";
  print "<table><tr><td>";
  print $cgi->button(-name=>"sub_remsrv", -value=>"Submit", -onclick=>"check_srv('remsrv');");
  print "</td><td>";
  print $cgi->reset(-value=>"Reset", -onclick=>"get_ssr_info(2,$sname,'ssr_info')");
  print "</td></tr></table>";
  }
 }

################
# Resource
################

elsif ( $type eq "crs" ){
 # check if a resource already exists
 if ($rsname eq ""){
  print "<span class=\"warn\">Resource name cannot be blank</span>";
  print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
  }
 else {
  # Note that this does not take delstat in to account and will complain even if "deleted" resources share the same name
  # the db admin can remove resources with the new name BUT as the db is InnoDB this will remove any data for that resource
  my @check = $dbh->selectrow_array("select resource from resources where resource = \"$rsname\"");
  if ($check[0]) {
   print "<span class=\"warn\">This resource already exists</span>";
   }
  else {
   print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>1);
   }
  }
 }
elsif ( $type eq "rsi"){
 if ($rsname > 0){

  my @rsdata = $dbh->selectrow_array("select description, datadictionary, server from resources where r_auto = \"$rsname\" and delstat = 0");

  # get all servers
  my $query = "select sv_auto, shortname, port from site, server where site.s_auto = server.site and site.study = $sname and server.delstat = 0 and site.delstat = 0";
  my %servers = map { $_->[0], "$_->[1] - $_->[2]"} @{$dbh->selectall_arrayref($query)};
  $servers{0} = "-- Select Server --"; 

  # get all datadictionaries
  $query = "select dd_auto, dd_version, dd_date from datadictionaries where study = $sname and delstat = 0";
  my %datadictionaries = map { $_->[0], "$_->[1] - $_->[2]"} @{$dbh->selectall_arrayref($query)};
  $datadictionaries{0} = "-- Select Data Dictionary --";

  my %attr_s = undef;
  foreach my $s (keys %servers){ $attr_s{$s} = $rsdata[2] eq $s ? {'selected'=>'yes'} : {}; }
  my %attr_dd = undef;
  foreach my $dd (keys %datadictionaries){ $attr_dd{$dd} = $rsdata[1] eq $dd ? {'selected'=>'yes'} : {}; }

  print "<table><tr><td>";
  print $cgi->h2("Description");
  print $cgi->textfield( -name=>'rsdesc', -id=>"rsdescuprs", -size=>50, -maxlength=>255, -value=>"$rsdata[0]", -onkeyup=>"limchar(this);" );
  my $val = 255 - length($rsdata[0]);
  print $cgi->textfield( -name=>'rsdescuprslim', -id=>"rsdescuprslim", -size=>3, -readonly=>1, -value=>$val );
  print "</td><td></td></tr><tr><td>";
  print $cgi->h2("Server");
  print $cgi->popup_menu( -name=>'srvport', -id=>'srvportuprs', -values=>[sort {$servers{$a} cmp $servers{$b}} keys %servers], -labels=>\%servers, -attributes=>\%attr_s );
  print "</td><td>";
  print $cgi->h2("Data Dictionary");
  print $cgi->popup_menu( -name=>'ddname', -id=>'ddnameuprs', -values=>[sort {$datadictionaries{$a} cmp $datadictionaries{$b}} keys %datadictionaries], -labels=>\%datadictionaries, -attributes=>\%attr_dd );
  print $cgi->hidden(-name=>'action', -default=>"updateresource");
  print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
  print "</td></tr></table>";

  print "<table><tr><td></td><td style=\"text-align:right\"><br>";
  print $cgi->button(-name=>"sub_uprs", -value=>"Submit", -onclick=>"check_rs('uprs');");
  print "</td><td></td><td><br>\n";
  print $cgi->reset(-value=>"Reset", -onclick=>"get_rsinfo($rsname,'rsinfo');");
  print "</td></tr></table><br>";
  }
 } 
elsif ( $type eq "rrs"){
 unless ($rsname == 0) {
  print "<br>";
  print "<table><tr><td>";
  print $cgi->button(-name=>"sub_remrs", -value=>"Submit", -onclick=>"check_rs('remrs');");
  print "</td><td>";
  print $cgi->reset(-value=>"Reset", -onclick=>"get_ssr_info(3,$sname,'ssr_info')");
  print "</td></tr></table>";
  }
 }

# disconnect the query user
$dbh->disconnect();

################
# Loading Data
################

if ($action){

 print $cgi->start_html(
        -title=>'ViPAR Web based Analysis Portal - Resources Management Event',
        -style=>[ {'src'=>"/viparstyle/vipar.css"} ],
        -head => [ $cgi->meta({ -http_equiv => 'Pragma', -content => 'no-cache' }),
                $cgi->meta({ -http_equiv => 'Expires', -content => '-1' }) ]
        );

 $dbuser = $dbconfig->get("database_adminuser");
 $dbpass = $dbconfig->get("database_adminpass");
 
 # connect to the database as admin
 $dbh = DBI->connect($dsn, $dbuser, $dbpass, \%attr);

 $dbh->do("lock tables resources write, server write, site write, datadictionaries read, study read, variables read");

 if ( $action eq "newsite" ){
  $stname = uc($stname);
  print "New site added:<br><br>Name = $stname<br>Institute Description = $stinst<br>Country = $ctname<br>";
  $dbh->do("insert into site (shortname,country,fullname,study) VALUES (\"".uc($stname)."\",\"$ctname\",\"$stinst\",\"$sname\")");
  $dbh->do("unlock tables");
  }
 elsif ( $action eq "updatesite" ){
  my $stname_name = $dbh->selectrow_array("select shortname from site where s_auto = $stname and delstat = 0"); 
  print "Site $stname_name updated:<br><br>Institute Description = $stinst<br>Country = $ctname<br>";
  $dbh->do("update site set country = \"$ctname\", fullname = \"$stinst\" where s_auto = $stname");
  $dbh->do("unlock tables");
  }
 elsif ( $action eq "deletesite" ){
  my $stname_name = $dbh->selectrow_array("select shortname from site where s_auto = $stname and delstat = 0"); 
  print "Site $stname_name deleted:<br><br>This site name cannot be reused until it is permanently deleted from the database by your system administrator.";
  $dbh->do("update site set delstat = 1 where s_auto = $stname");
  $dbh->do("unlock tables");
  }
 elsif ( $action eq "newserver" ){
  my $stname_name = $dbh->selectrow_array("select shortname from site where s_auto = $stname and delstat = 0"); 
  print "New server added:<br><br>Port = $srvport<br>Site = $stname_name<br>Remote Host = $rhost<br>Remote Port = $rport<br>Remote User = $ruser";
  $dbh->do("insert into server (site,port,remotehost,remoteport,remoteuser) VALUES ($stname,$srvport,\"$rhost\",\"$rport\",\"$ruser\")");
  $dbh->do("unlock tables");
  }
 elsif ( $action eq "updateserver" ){
  my $srvport_name = $dbh->selectrow_array("select port from server where sv_auto = $srvport and delstat = 0"); 
  my $stname_name = $dbh->selectrow_array("select shortname from site where s_auto = $stname and delstat = 0"); 
  print "Server on port $srvport_name updated<br><br>Site = $stname_name<br>Remote Host = $rhost<br>Remote Port = $rport<br>Remote User = $ruser";
  $dbh->do("update server set site = $stname, remotehost = \"$rhost\", remoteport = \"$rport\", remoteuser = \"$ruser\" where sv_auto = $srvport");
  $dbh->do("unlock tables");
  }
 elsif ( $action eq "deleteserver" ){
  my $srvport_name = $dbh->selectrow_array("select port from server where sv_auto = $srvport and delstat = 0"); 
  print "Server on port $srvport_name deleted<br><br>This port number cannot be reused until it is permanently deleted from the database by your system administrator.";
  $dbh->do("update server set delstat = 1 where sv_auto = $srvport");
  $dbh->do("unlock tables");
  }
 elsif ( $action eq "newresource" ){
  $rsname =~ s/\s+/_/g;
  my @srvname = $dbh->selectrow_array("select shortname, port from server, site where site.s_auto = server.site and sv_auto = $srvport and server.delstat = 0 and site.delstat = 0");
  my @ddname = $dbh->selectrow_array("select dd_version, dd_date from datadictionaries where dd_auto = $ddname and delstat = 0");
  print "New resource added:<br><br>Name = $rsname<br>Description = $rsdesc<br>Server = $srvname[0] - $srvname[1]<br>Data Dictionary = $ddname[0] - $ddname[1]<br>";
  $dbh->do("insert into resources (resource,description,server,datadictionary,study) VALUES (\"$rsname\",\"$rsdesc\",$srvport,$ddname,$sname)");
  $dbh->do("unlock tables");
  }
 elsif ( $action eq "updateresource" ){
  my @srvname = $dbh->selectrow_array("select shortname, port from server, site where site.s_auto = server.site and sv_auto = $srvport and server.delstat = 0 and site.delstat = 0");
  my @ddnames = $dbh->selectrow_array("select dd_version, dd_date from datadictionaries where dd_auto = $ddname and delstat = 0");
  my $rsname_name = $dbh->selectrow_array("select resource from resources where r_auto = $rsname and delstat =0");
  print "Resource $rsname_name updated<br><br>Description = $rsdesc<br>Server = $srvname[0] - $srvname[1]<br>Data Dictionary = $ddnames[0] - $ddnames[1]<br>";
  $dbh->do("update resources set description = \"$rsdesc\", server = $srvport, datadictionary = $ddname where r_auto = $rsname");
  $dbh->do("unlock tables");
  }
 elsif ( $action eq "deleteresource" ){
  my $rsname_name = $dbh->selectrow_array("select resource from resources where r_auto = $rsname and delstat = 0");
  print "Resource $rsname_name deleted<br><br>This resource name cannot be reused until it is permanently deleted from the database by your system administrator.";
  $dbh->do("update resources set delstat = 1 where r_auto = $rsname");
  $dbh->do("unlock tables");
  }
 elsif ($action eq "rssyntax"){
  my $dbu = $dbconfig->get("database_remotequeryuser");
  my $dbp = $dbconfig->get("database_remotequerypass");
  my $dbuins = $dbconfig->get("database_remoteadminuser");
  my $dbpins = $dbconfig->get("database_remoteadminpass");
  $dbh->do("unlock tables");
  my $intlen = "bigint";
  my %ints = (
      2 => "tinyint",
      4 => "smallint",
      6 => "mediumint",
      9 => "int"
      );

  print "Use the following MySQL syntax to create the table on the remote server<br><br>";
  # get study name for auto_inc name
  my @sdata = $dbh->selectrow_array("select study from study where st_auto = \"$sname\" and delstat = 0");
  # get the resource name
  # this is used as the name of the remote database
  my @rsdata = $dbh->selectrow_array("select resource from resources where r_auto = \"$rsname\" and delstat = 0");
  print "<PRE>";
  print "create database if not exists $rsdata[0];\n";
  print "use $rsdata[0];\n";

  # now we need to get each table from dtables for this study
  my $dtdata = $dbh->selectall_arrayref("select name,tid from dtables where study = \"$sname\" and delstat = 0");
  foreach my $t (@{$dtdata}){
   my $auto = "$t->[0]\_auto";
   print "drop table if exists $t->[0];\ncreate table $t->[0] (\n  `$auto` int(10) NOT NULL AUTO_INCREMENT PRIMARY KEY";
   # get the variables and their types for this table
   my $stmt = "select dtv.vid, v.variable, v.type from variables as v, dtables_variables as dtv, dtables as dt where v.v_auto = dtv.vid and dt.tid = dtv.tid and dt.tid = $t->[1] and v.delstat = 0";
   my $query = $dbh->prepare($stmt);
   $query->execute();
   while (my @data = $query->fetchrow_array()){
    
    # write the table definition
    # get the type, ranges, default and missing for each variable
    # for each variable
    #     if decimal, construct as needed
    #     else should be tinyint,smallint,mediumint (check max digits) with default = NULL
    #     	establish length of value including missing and default
    #     	assign length to correct type
    #     add tablename_auto as auto_inc primary key
    my $length = 0;
    my $stmt = "select length(m.value) from missing as m, variables_missing as vm where m.m_auto = vm.missing and vm.variable = $data[0] and m.delstat = 0";
    my $lquery = $dbh->prepare($stmt);
    $lquery->execute();
    while (my @ldata = $lquery->fetchrow_array()){
     $length = $ldata[0] if $ldata[0] > $length;
     }
    $lquery->finish();
    if ($data[2] == 1){ # categorical
     my @catdata = $dbh->selectrow_array("select max(length(cat)) from variables_cat where variable = $data[0]");
     $length = $catdata[0] if $catdata[0] > $length;
     my $dtype = "bigint($length)";
     foreach my $i (sort{ $a <=> $b} keys %ints){ $dtype = "$ints{$i}($length)"; last if $length < $i; }
     print ",\n  `$data[1]` $dtype NULL DEFAULT NULL";
     }
    elsif ($data[2] == 2){ # continuous
     my @condata = $dbh->selectrow_array("select length(max), prec from variables_con where variable = $data[0]");
     $length = $condata[0] if $condata[0] > $length;
     my $decimalt = $condata[0] + $condata[1];
     my $decimalp = $condata[1];
     my $dtype = "decimal($decimalt,$decimalp)";
     if ($condata[1] == 0){
      $dtype = "bigint($length)";
      foreach my $i (sort{ $a <=> $b} keys %ints){ $dtype = "$ints{$i}($length)"; last if $length < $i; }
      }
     print ",\n  `$data[1]` $dtype NULL DEFAULT NULL";
     }
    elsif ($data[2] == 3){ # date
     print ",\n  `$data[1]` date NULL DEFAULT NULL";
     }
    }
   $query->finish();
   print "\n );\n";
   }
  print "\nGRANT SELECT on `$rsdata[0]`.* TO `$dbu`@`localhost` IDENTIFIED BY '$dbp';\n";
  # we have both % and localhost for the remote insert user as this means that data can be loaded from either the server itself (localhost) or from a user's workstation (%)
  print "\nGRANT SELECT,INSERT,DELETE on `$rsdata[0]`.* TO `$dbuins`@`\%` IDENTIFIED BY '$dbpins';\n";
  print "\nGRANT SELECT,INSERT,DELETE on `$rsdata[0]`.* TO `$dbuins`@`localhost` IDENTIFIED BY '$dbpins';\n";
  print "\nflush privileges;\n";
  print "</PRE>";
  }
 elsif ($action eq "xsyntax"){
  $dbh->do("unlock tables");
  my @srvdata = $dbh->selectrow_array("select st.study,shortname,port,remotehost,remoteport,remoteuser from server as sv,site as s,study as st where st.st_auto = s.study and s.s_auto = sv.site and sv_auto = \"$srvport\" and s.delstat = 0 and sv.delstat = 0 and st.delstat = 0");
  print "Paste the following Xinetd syntax into /etc/xinetd.d/vipar to create a connection to the remote server<br><br>";
  print "<PRE>";
  $srvdata[0] =~ s/ //g;
  $srvdata[1] =~ s/ //g;
  my $servicename = "$srvdata[0]\_$srvdata[1]\_$srvdata[2]";
  print <<XINET;
service $servicename
{
   flags          = REUSE
   type           = UNLISTED
   disable        = no
   socket_type    = stream
   protocol       = tcp
   wait           = no
   user           = viparadmin
   server         = /usr/bin/ssh
   server_args    = -q -C -T -p $srvdata[4] $srvdata[5]\@$srvdata[3]
   bind           = 127.0.0.1
   port           = $srvdata[2]
}

Then restart Xinetd with:
systemctl restart xinetd

Please also check you have setup SSH keys for the server, as described in the ViPAR manual
XINET
  print "</PRE>";
  }

 $dbh->disconnect();

 $cgi->end_html();
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

