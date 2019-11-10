#!/usr/bin/perl

# need code for adding, updating, deleting variables and data dictionaries
# select study first
# 	then split in to Missing, Variables and DDs
# 		Missing
# 			New missing
# 			Update missing
# 			Delete missing
#		Variables
# 			New variable
# 			Update variable
# 			Delete variable
# 		DD
# 			New DataDictionary
# 			Update DataDictionary
# 				Add Variables
# 				Remove variables
#
# mysql> describe variables;
# +-------------+------------------+------+-----+---------+----------------+
# | Field       | Type             | Null | Key | Default | Extra          |
# +-------------+------------------+------+-----+---------+----------------+
# | v_auto      | int(11) unsigned | NO   | PRI | NULL    | auto_increment |
# | variable    | varchar(50)      | NO   |     | NULL    |                |
# | description | varchar(255)     | YES  |     | NULL    |                |
# | study       | int(11) unsigned | NO   |     | NULL    |                |
# +-------------+------------------+------+-----+---------+----------------+
# 4 rows in set (0.00 sec)
#
# mysql> describe variables_missing;
# +----------+------------------+------+-----+---------+----------------+
# | Field    | Type             | Null | Key | Default | Extra          |
# +----------+------------------+------+-----+---------+----------------+
# | vm_auto  | int(11) unsigned | NO   | PRI | NULL    | auto_increment |
# | variable | int(11) unsigned | NO   |     | NULL    |                |
# | missing  | int(11) unsigned | NO   |     | NULL    |                |
# +----------+------------------+------+-----+---------+----------------+
# 3 rows in set (0.00 sec)
#
# mysql> describe missing;
# +-------------+---------------------+------+-----+---------+----------------+
# | Field       | Type                | Null | Key | Default | Extra          |
# +-------------+---------------------+------+-----+---------+----------------+
# | m_auto      | int(11) unsigned    | NO   | PRI | NULL    | auto_increment |
# | value       | varchar(50)         | NO   |     | NULL    |                |
# | description | varchar(255)        | YES  |     | NULL    |                |
# | study       | int(11) unsigned    | NO   |     | NULL    |                |
# | delstat     | tinyint(1) unsigned | NO   |     | 0       |                |
# +-------------+---------------------+------+-----+---------+----------------+
# 
# mysql> describe datadictionaries;
# +------------+-----------------------+------+-----+---------+----------------+
# | Field      | Type                  | Null | Key | Default | Extra          |
# +------------+-----------------------+------+-----+---------+----------------+
# | dd_auto    | int(11) unsigned      | NO   | PRI | NULL    | auto_increment |
# | dd_version | mediumint(4) unsigned | NO   |     | NULL    |                |
# | dd_date    | varchar(50)           | NO   |     | NULL    |                |
# | study      | int(11) unsigned      | NO   |     | NULL    |                |
# +------------+-----------------------+------+-----+---------+----------------+
# 4 rows in set (0.00 sec)
#
# mysql> describe datadictionaries_variables;
# +------------+------------------+------+-----+---------+----------------+
# | Field      | Type             | Null | Key | Default | Extra          |
# +------------+------------------+------+-----+---------+----------------+
# | df_auto    | int(11) unsigned | NO   | PRI | NULL    | auto_increment |
# | dd_version | int(11) unsigned | NO   |     | NULL    |                |
# | variable   | int(11) unsigned | NO   |     | NULL    |                |
# +------------+------------------+------+-----+---------+----------------+
# 
# dtables and dtables_variables
# Need an interface to populate these tables that will look like the data dictionary interface
# It will pull variables from the DD as table definitions will be per DD
# This will have the same insert, update, delete feel as the rest
# Insert will have input fields for the table name and description and list the variables to tick
# Update will retreive current variables and table description for update
# Delete will delete the table

use strict;
use DBI;
use CGI;
use CGI::Carp qw(fatalsToBrowser);
use CGI::Session;
use CGI::Cookie;
use Data::Dumper;
use Scalar::Util qw(looks_like_number);
use AppConfig;
use IO::Socket::INET;

my $cgi = new CGI;
my $type = $cgi->param('type');
my $action = $cgi->param('action');
my $sname = $cgi->param('sname');
my $mname = $cgi->param('mname');
my $mdesc = $cgi->param('mdesc');
my $vname = $cgi->param('vname');
my $vdesc = $cgi->param('vdesc');
my $vtype = $cgi->param("vtype");
my $ftype = $cgi->param("ftype");
my $mvd = $cgi->param("mvd");
my @missing = $cgi->param("missing");
my $vt_min = $cgi->param("vt_min");
my $vt_max = $cgi->param("vt_max");
my $vt_min2 = $vt_min;
$vt_min2 =~ s/",/"",/g;
$vt_min2 =~ s/[\r\n]//g;
my @vt_mins = split("\",",$vt_min2);
my $vt_dp = $cgi->param("vt_dp");
my $ddname = $cgi->param('ddname');
my $dddate = $cgi->param('dddate');
my $dtname = $cgi->param('dtname');
my $dtdesc = $cgi->param('dtdesc');
my @variable = $cgi->param("variable");

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

if ($type eq "nv"){
 # get all studies this user has permission to access
 my $query = "";
 if ($user_priv{'it'} == 1){ $query = "select st_auto, s.study from study as s where delstat = 0"; }
 elsif ($user_priv{'lead'} == 2){ $query = "select st_auto, s.study from study as s, users_study as us where s.st_auto = us.study and s.delstat = 0 and user = $uid and priv = 2"; }
 my %studies = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($query)};
 $studies{0} = "-- Select study --";

 print $cgi->h2("Select Study Name");
 print $cgi->popup_menu( -name=>'sname', -id=>'sname', -values=>[sort keys %studies], -labels=>\%studies, -onchange=>"get_mvd(this.value,'mvd');" );
 print "<div id=\"mvd\"></div>";
 }
elsif ($type eq "mvd"){
 if ($sname > 0){
  my %opts = (
 	"mis" => "Missing Value",
 	"var" => "Variable",
 	"dd" => "Data Dictionary",
 	"dtdd" => "Dynamic Table"
 	);
  $opts{0} = "-- Select Type --";
 
  print $cgi->h2("Select Type");
  print $cgi->popup_menu( -name=>'mvd_opt', -id=>'mvd_opt', -values=>[sort keys %opts], -labels=>\%opts, -onchange=>"get_mvd_info(this.value,$sname,'mvd_info')" );
  print $cgi->br();
  print $cgi->br();
  print $cgi->hr();
  print "<div id=\"mvd_info\"></div>";
  } 
 }
elsif ($type eq "mvdi"){
 if ($sname > 0){

################
# Missing
################
 
  if ($mvd eq "mis"){
   # get all missing vals
   my $query = "select m_auto, value from missing where study = $sname and delstat = 0";
   my %missing = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($query)};
   $missing{0} = "-- Select Value --";

################
# Add Missing

   print $cgi->h2("Add Missing value");

   print $cgi->start_multipart_form(
    -method=>'POST',
    -action=>'/viparcgi/vipar_managevariables.cgi',
    -name=>'newmis',
    -id=>'newmis',
    );

   print "<table><tr>";
   print "<td colspan=\"4\">";
   print $cgi->h2("Value");
   print $cgi->textfield( -name=>'mname', -id=>"mnamenewmis", -size=>50, -maxlength=>50, -onblur=>"checkm(this.value,'checkm');", onkeyup=>"limchar(this);" );
   print $cgi->textfield( -name=>'mnamenewmislim', -id=>"mnamenewmislim", -size=>2, -readonly=>1, -value=>50 ); 
   print "<br><div id=\"checkm\">\n";
   print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
   print "</div>";
   print "</td><td valign=\"top\">";
   print $cgi->h2("Value Description");
   print $cgi->textfield( -name=>'mdesc', -id=>"mdescnewmis", -size=>50, -maxlength=>255, onkeyup=>"limchar(this);" );
   print $cgi->textfield( -name=>'mdescnewmislim', -id=>"mdescnewmislim", -size=>3, -readonly=>1, -value=>255 ); 
   print $cgi->hidden(-name=>'action', -default=>"newmissing");
   print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
   print "</td></tr>";
   print "<tr><td></td>";
   print "<td style=\"text-align:right\"><br>";
   print $cgi->button(-name=>"sub_newmis", -value=>"Submit", -onclick=>"check_mis('newmis');");
   print "</td>";
   print "<td></td><td><br>\n";
   print $cgi->button(-value=>"Reset", -onclick=>"get_mvd_info('mis',$sname,'mvd_info')");
   print "</td><td></td></tr>";
   print "</table><br>";

   print $cgi->end_multipart_form();
   print $cgi->br();
   print $cgi->hr();

################
# Update Missing

   print $cgi->h2("Update Missing value");

   print $cgi->start_multipart_form(
    -method=>'POST',
    -action=>'/viparcgi/vipar_managevariables.cgi',
    -name=>'upmis',
    -id=>'upmis',
    );

   print $cgi->h2("Missing Value");
   print $cgi->popup_menu( -name=>'mname', -id=>'mnameupmis', -values=>[sort keys %missing], -labels=>\%missing, -onchange=>"get_minfo(this.value,'minfo');" );
   print $cgi->hidden(-name=>'action',-default=>"updatemissing");
   print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
   print "<div id=\"minfo\"></div>";

   print $cgi->end_multipart_form();
   print $cgi->br();
   print $cgi->hr();

################
# Remove Missing

   print $cgi->h2("Remove Missing value");

   print $cgi->start_multipart_form(
    -method=>'POST',
    -action=>'/viparcgi/vipar_managevariables.cgi',
    -name=>'remmis',
    -id=>'remmis',
    );

   print $cgi->h2("Missing Value");
   print $cgi->popup_menu( -name=>'mname', -id=>'mnameremmis', -values=>[sort keys %missing], -labels=>\%missing, -onchange=>"get_submit_m(this.value,'mdel',$sname);" );
   print $cgi->hidden(-name=>'action',-default=>"deletemissing");
   print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
   print "<div id=\"mdel\"></div>";

   print $cgi->end_multipart_form();
   print $cgi->br();
   print $cgi->hr();
   }

################
# Variables
################
 
  elsif ($mvd eq "var"){
   # get all missing vals
   my $query = "select m_auto, value, description from missing where study = $sname and delstat = 0";
   my %missing = map { $_->[0], "$_->[1] - $_->[2]" } @{$dbh->selectall_arrayref($query)};
   
   # get all variables
   my $query = "select v_auto, variable from variables where study = $sname and delstat = 0";
   my %variables = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($query)};
   $variables{0} = "-- Select Variable --";

   # get all variable_types
   my $query = "select vt_auto, type from variables_type";
   my %vtypes = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($query)};
   $vtypes{0} = "-- Select Type --";

################
# Add Variable

   print $cgi->h2("Add Variable");

   print $cgi->start_multipart_form(
    -method=>'POST',
    -action=>'/viparcgi/vipar_managevariables.cgi',
    -name=>'newvar',
    -id=>'newvar',
    );

   print "<table><tr>";
   print "<td colspan=\"2\">";
   print $cgi->h2("Name");
   print $cgi->textfield( -name=>'vname', -id=>"vnamenewvar", -size=>50, -maxlength=>50, -onblur=>"checkv(this.value,'checkv');", onkeyup=>"limchar(this);" );
   print $cgi->textfield( -name=>'vnamenewvarlim', -id=>"vnamenewvarlim", -size=>2, -readonly=>1, -value=>50 );
   print "<br><div id=\"checkv\">\n";
   print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
   print "</div>";
   print "</td><td valign=\"top\" colspan=\"2\">";
   print $cgi->h2("Description");
   print $cgi->textfield( -name=>'vdesc', -id=>"vdescnewvar", -size=>50, -maxlength=>255, onkeyup=>"limchar(this);" );
   print $cgi->textfield( -name=>'vdescnewvarlim', -id=>"vdescnewvarlim", -size=>3, -readonly=>1, -value=>255 );
   print $cgi->hidden(-name=>'action', -default=>"newvariable");
   print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
   print "</td></tr>";
   print "<tr><td>".$cgi->h2("Type")."</td><td></td><td></td><td></td></tr>";
   print "<tr><td colspan=\"4\">";
   print $cgi->popup_menu( -name=>'vtype', -id=>'vtypenewvar', -values=>[sort {$a <=> $b} keys %vtypes], -labels=>\%vtypes, -onchange=>"get_vtype(this.value,'vtype','newvar')" );
   print "</td></tr>";
   print "<tr><td colspan=\"4\"><br><br><div id=\"vtype\"></div>";

   print "<tr><td>".$cgi->h2("Missing")."</td><td></td><td></td><td></td></tr>";
   print "<tr><td colspan=\"4\">";
   print $cgi->checkbox_group( -name=>'missing', -id=>'missingnewvar', -values=>[sort {$missing{$a} <=> $missing{$b}} keys %missing], -labels=>\%missing, -columns=>2 );
   print "</td></tr></table>";
   
   print "<table><tr>";
   print "<td style=\"text-align:right\"><br>";
   print $cgi->button(-name=>"sub_newvar", -value=>"Submit", -onclick=>"check_var('newvar');");
   print "</td>";
   print "<td></td><td><br>\n";
   print $cgi->button(-value=>"Reset", -onclick=>"get_mvd_info('var',$sname,'mvd_info');");
   print "</td></tr></table>";

   print $cgi->end_multipart_form();
   print $cgi->br();
   print $cgi->hr();

################
# Update Variable

   print $cgi->h2("Update Variable");

   print $cgi->start_multipart_form(
    -method=>'POST',
    -action=>'/viparcgi/vipar_managevariables.cgi',
    -name=>'upvar',
    -id=>'upvar',
    );

   print $cgi->h2("Variable");
   print $cgi->popup_menu( -name=>'vname', -id=>'vnameupvar', -values=>[sort { $variables{$a} cmp $variables{$b}  } keys %variables], -labels=>\%variables, -onchange=>"get_vinfo(this.value,'vinfo');" );
   print $cgi->hidden(-name=>'action',-default=>"updatevariable");
   print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
   print "<div id=\"vinfo\"></div>";

   print $cgi->end_multipart_form();
   print $cgi->br();
   print $cgi->hr();

################
# Remove Variable

   print $cgi->h2("Remove Variable");

   print $cgi->start_multipart_form(
    -method=>'POST',
    -action=>'/viparcgi/vipar_managevariables.cgi',
    -name=>'remvar',
    -id=>'remvar',
    );

   print $cgi->h2("Variable");
   print $cgi->popup_menu( -name=>'vname', -id=>'vnameremvar', -values=>[sort { $variables{$a} cmp $variables{$b}  } keys %variables], -labels=>\%variables, -onchange=>"get_submit_v(this.value,'vdel',$sname);" );
   print $cgi->hidden(-name=>'action',-default=>"deletevariable");
   print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
   print "<div id=\"vdel\"></div>";
  
   print $cgi->end_multipart_form();
   print $cgi->br();
   print $cgi->hr();
   }

################
# Data Dictionary
################

  elsif ($mvd eq "dd"){

   # get all variables
   my $query = "select v_auto, variable from variables where study = $sname and delstat = 0";
   my %variables = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($query)};

   # get all datadictionaries
   my $query = "select dd_auto, dd_version, dd_date from datadictionaries where study = $sname and delstat = 0";
   my %datadictionaries = map { $_->[0], "$_->[1] - $_->[2]"} @{$dbh->selectall_arrayref($query)};
   $datadictionaries{0} = "-- Select Data Dictionary --";

################
# Add Data Dictionary

   print $cgi->h2("Add Data Dictionary");

   print $cgi->start_multipart_form(
    -method=>'POST',
    -action=>'/viparcgi/vipar_managevariables.cgi',
    -name=>'newdd',
    -id=>'newdd',
    );

   print "<table><tr>";
   print "<td style=\"width: 250px;\">";
   print $cgi->h2("Version");
   print $cgi->textfield( -name=>'ddname', -id=>"ddnamenewdd", -size=>5, -maxlength=>5, -onblur=>"checkdd(this.value,'checkdd');", onkeyup=>"limchar(this);" );
   print $cgi->textfield( -name=>'ddnamenewddlim', -id=>"ddnamenewddlim", -size=>2, -readonly=>1, -value=>5 );
   print "<br><div id=\"checkdd\">\n";
   print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
   print "</div></td>";
   print "<td valign=\"top\">";
   print $cgi->h2("Date");
   print $cgi->textfield( -name=>'dddate', -id=>"dddatenewdd", -size=>50, -maxlength=>50, onkeyup=>"limchar(this);" );
   print $cgi->textfield( -name=>'dddatenewddlim', -id=>"dddatenewddlim", -size=>2, -readonly=>1, -value=>50 );
   print $cgi->hidden(-name=>'action', -default=>"newdatadictionary");
   print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
   print "</td></tr><tr><td colspan=\"3\">".$cgi->h2("Variables")."</td></tr></table>";

   print $cgi->checkbox_group( -name=>'variable', -id=>'variablenewdd', -values=>[sort {$variables{$a} cmp $variables{$b}} keys %variables], -labels=>\%variables, -columns=>8 );

   print "<table><tr>";
   print "<td style=\"text-align:right\"><br>";
   print $cgi->button(-name=>"sub_newdd", -value=>"Submit", -onclick=>"check_dd('newdd');");
   print "</td>";
   print "<td></td><td><br>\n";
   print $cgi->button(-value=>"Reset", -onclick=>"get_mvd_info('dd',$sname,'mvd_info');");
   print "</td></tr></table><br>";

   print $cgi->end_multipart_form();
   print $cgi->br();
   print $cgi->hr();

################
# Update Data Dictionary

   print $cgi->h2("Update Data Dictionary");

   print $cgi->start_multipart_form(
    -method=>'POST',
    -action=>'/viparcgi/vipar_managevariables.cgi',
    -name=>'updd',
    -id=>'updd',
    );

   print $cgi->h2("Data Dictionary");
   print $cgi->popup_menu( -name=>'ddname', -id=>'ddnameupdd', -values=>[sort { $datadictionaries{$a} cmp $datadictionaries{$b}  } keys %datadictionaries], -labels=>\%datadictionaries, -onchange=>"get_ddinfo(this.value,'ddinfo');" );
   print $cgi->hidden(-name=>'action',-default=>"updatedatadictionary");
   print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
   print "<div id=\"ddinfo\"></div>";

   print $cgi->end_multipart_form();
   print $cgi->br();
   print $cgi->hr();

################
# Remove Data Dictionary

   print $cgi->h2("Remove Data Dictionary");

   print $cgi->start_multipart_form(
    -method=>'POST',
    -action=>'/viparcgi/vipar_managevariables.cgi',
    -name=>'remdd',
    -id=>'remdd',
    );

   print $cgi->h2("Data Dictionary");
   print $cgi->popup_menu( -name=>'ddname', -id=>'ddnameremdd', -values=>[sort { $datadictionaries{$a} cmp $datadictionaries{$b}  } keys %datadictionaries], -labels=>\%datadictionaries, -onchange=>"get_submit_dd(this.value,'dddel',$sname);" );
   print $cgi->hidden(-name=>'action',-default=>"deletedatadictionary");
   print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
   print "<div id=\"dddel\"></div>";

   print $cgi->end_multipart_form();
   print $cgi->br();
   print $cgi->hr();

   }
  

################
# Dynamic Tables
################
  elsif ($mvd eq "dtdd"){
   # need to display a drop down with the current datadictionaries
   # once this is selected, then display dt content
   # get all datadictionaries
   my $query = "select dd_auto, dd_version, dd_date from datadictionaries where study = $sname and delstat = 0";
   my %datadictionaries = map { $_->[0], "$_->[1] - $_->[2]"} @{$dbh->selectall_arrayref($query)};
   $datadictionaries{0} = "-- Select Data Dictionary --";
   print $cgi->h2("Select Data Dictionary");

   print $cgi->start_multipart_form(
    -method=>'POST',
    -action=>'/viparcgi/vipar_managevariables.cgi',
    -name=>'updd',
    -id=>'updd',
    );

   print $cgi->popup_menu( -name=>'ddname', -id=>'ddnameupdt', -values=>[sort { $datadictionaries{$a} cmp $datadictionaries{$b}  } keys %datadictionaries], -labels=>\%datadictionaries, -onchange=>"get_dtddinfo(this.value,$sname,'dtddinfo');" );
   print "<div id=\"dtddinfo\"></div>";

   print $cgi->end_multipart_form();
   print $cgi->br();
   print $cgi->hr();
   }
  elsif ($mvd eq "dt"){
   if ($ddname > 0){
    # get all variables
    #my $query = "select v_auto, variable from variables where study = $sname and delstat = 0";
    my $query = "select v.v_auto, v.variable from variables as v, datadictionaries_variables as ddv where v.v_auto = ddv.variable and ddv.dd_version = $ddname and v.delstat = 0";
    my %variables = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($query)};

    # get all dynamic tables
    my $query = "select tid, name from dtables where study = $sname and dd_version = $ddname and delstat = 0";
    my %dtables = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($query)};
    $dtables{0} = "-- Select Dynamic Table --";

################
# Add Dynamic Table

    print $cgi->h2("Add Dynamic Table");

    print $cgi->start_multipart_form(
     -method=>'POST',
     -action=>'/viparcgi/vipar_managevariables.cgi',
     -name=>'newdt',
     -id=>'newdt',
     );

    print "<table><tr>";
    print "<td style=\"width: 250px;\">";
    print $cgi->h2("Name");
    print $cgi->textfield( -name=>'dtname', -id=>"dtnamenewdt", -size=>20, -maxlength=>50, -onblur=>"checkdt(this.value,'checkdt');", onkeyup=>"limchar(this);" );
    print $cgi->textfield( -name=>'dtnamenewdtlim', -id=>"dtnamenewdtlim", -size=>2, -readonly=>1, -value=>50 );
    print "<br><div id=\"checkdt\">\n";
    print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
    print "</div></td>";
    print "<td valign=\"top\">";
    print $cgi->h2("Description");
    print $cgi->textfield( -name=>'dtdesc', -id=>"dtdescnewdt", -size=>50, -maxlength=>100, onkeyup=>"limchar(this);" );
    print $cgi->textfield( -name=>'dtdescnewdtlim', -id=>"dtdescnewdtlim", -size=>3, -readonly=>1, -value=>100 );
    print $cgi->hidden(-name=>'action', -default=>"newdynamictable");
    print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
    print $cgi->hidden(-name=>'ddname', -id=>'ddname', -default=>"$ddname");
    print "</td></tr><tr><td colspan=\"3\">".$cgi->h2("Variables")."</td></tr></table>";

    print $cgi->checkbox_group( -name=>'variable', -id=>'variablenewdt', -values=>[sort {$variables{$a} cmp $variables{$b}} keys %variables], -labels=>\%variables, -columns=>8 );

    print "<table><tr>";
    print "<td style=\"text-align:right\"><br>";
    print $cgi->button(-name=>"sub_newdt", -value=>"Submit", -onclick=>"check_dt('newdt');");
    print "</td>";
    print "<td></td><td><br>\n";
    print $cgi->button(-value=>"Reset", -onclick=>"get_mvd_info('dt',$sname,'mvd_info');");
    print "</td></tr></table><br>";

    print $cgi->end_multipart_form();
    print $cgi->br();
    print $cgi->hr();

################
# Update Dynamic Table

    print $cgi->h2("Update Dynamic Table");

    print $cgi->start_multipart_form(
     -method=>'POST',
     -action=>'/viparcgi/vipar_managevariables.cgi',
     -name=>'updt',
     -id=>'updt',
     );

    print $cgi->h2("Dynamic Table");
    print $cgi->popup_menu( -name=>'dtname', -id=>'dtnameupdt', -values=>[sort { $dtables{$a} cmp $dtables{$b}  } keys %dtables], -labels=>\%dtables, -onchange=>"get_dtinfo(this.value,'dtinfo');" );
    print $cgi->hidden(-name=>'action',-default=>"updatedynamictable");
    print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
    print $cgi->hidden(-name=>'ddname', -id=>'ddname', -default=>"$ddname");
    print "<div id=\"dtinfo\"></div>";

    print $cgi->end_multipart_form();
    print $cgi->br();
    print $cgi->hr();

################
# Remove Dynamic Table

    print $cgi->h2("Remove Dynamic Table");

    print $cgi->start_multipart_form(
     -method=>'POST',
     -action=>'/viparcgi/vipar_managevariables.cgi',
     -name=>'remdt',
     -id=>'remdt',
     );

    print $cgi->h2("Dynamic Table");
    print $cgi->popup_menu( -name=>'dtname', -id=>'dtnameremdt', -values=>[sort { $dtables{$a} cmp $dtables{$b}  } keys %dtables], -labels=>\%dtables, -onchange=>"get_submit_dt(this.value,'dtdel',$sname);" );
    print $cgi->hidden(-name=>'action',-default=>"deletedynamictable");
    print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
    print "<div id=\"dtdel\"></div>";

    print $cgi->end_multipart_form();
    print $cgi->br();
    print $cgi->hr();

    }
   }
  }
 }

################
# Missing Values
################
elsif ( $type eq "cm" ){
 # check if a missing val exists with this name
 if ($mname eq ""){
  print "<span class=\"warn\">Missing value cannot be blank</span>";
  print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
  }
 elsif (!looks_like_number($mname)){
  print "<span class=\"warn\">Missing value must be number</span>";
  print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
  }
 else {
  # Note that this does not take delstat in to account and will complain even if "deleted" mis share the same name
  # the db admin can remove mis with the new name BUT as the db is InnoDB this will remove any data for that mis
  my $check = $dbh->selectrow_array("select value from missing where value = \"$mname\" and study = $sname");
  if ($check) {
   print "<span class=\"warn\">Missing value already exists</span>";
   print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
   }
  else {
   print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>1);
   }
  }
 }
elsif ( $type eq "mi" ){
 if ($mname > 0){
  
  my @misdata = $dbh->selectrow_array("select description from missing where m_auto = \"$mname\" and delstat = 0");
  print $cgi->h2("Description");
  print $cgi->textfield( -name=>'mdesc', -id=>"mdescupmis", -size=>50, -maxlength=>255, -value=>"$misdata[0]", onkeyup=>"limchar(this);" );
  my $val = 255 - length($misdata[0]);
  print $cgi->textfield( -name=>'mdescupmislim', -id=>"mdescupmislim", -size=>3, -readonly=>1, -value=>$val );
  print "<table><tr><td></td><td style=\"text-align:right\"><br>";
  print $cgi->button(-name=>"sub_upmis", -value=>"Submit", -onclick=>"check_mis('upmis');");
  print "</td><td></td><td><br>\n";
  print $cgi->button(-value=>"Reset", -onclick=>"get_minfo($mname,'minfo');");
  print "</td></tr></table><br>";

  }
 }
elsif ( $type eq "rm" ){
 unless ($mname == 0) {
  print "<br>";
  print "<table><tr><td>";
  print $cgi->button(-name=>"sub_remmis", -value=>"Submit", -onclick=>"check_mis('remmis');");
  print "</td><td>";
  print $cgi->button(-value=>"Reset", -onclick=>"get_mvd_info('mis',$sname,'mvd_info');");
  print "</td></tr></table>";
  }
 }
################
# Variables
################
elsif ( $type eq "cv" ){
 # check if a variables exists with this name
 if ($vname eq ""){
  print "<span class=\"warn\">Variable value cannot be blank</span>";
  print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
  }
 elsif ($vname =~ m/\s+/){
  print "<span class=\"warn\">Variable cannot contain spaces</span>";
  print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
  }
 else {
  # Note that this does not take delstat in to account and will complain even if "deleted" variables share the same name
  # the db admin can remove variables with the new name BUT as the db is InnoDB this will remove any data for that variable
  my $check = $dbh->selectrow_array("select variable from variables where variable = \"$vname\" and study = $sname");
  if ($check) {
   print "<span class=\"warn\">Variable already exists with that name</span>";
   print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
   }
  else {
   print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>1);
   }
  }
 }
elsif ( $type eq "vi" ){
 if ($vname > 0){
  # get all variable_types
  my $query = "select vt_auto, type from variables_type";
  my %vtypes = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($query)};
  $vtypes{0} = "-- Select Type --";

  # get all missing vals
  my $query = "select m_auto, value, description from missing where study = $sname and delstat = 0";
  my %missing = map { $_->[0], "$_->[1] - $_->[2]" } @{$dbh->selectall_arrayref($query)};
  # get all missing for this variable
  my $query = "select missing from variables_missing where variable = \"$vname\"";
  my @missingcheck = ();
  push @missingcheck, $_->[0] foreach @{$dbh->selectall_arrayref($query)};
   
  my @vardata = $dbh->selectrow_array("select description,type from variables where v_auto = \"$vname\" and delstat = 0");
  print "<table><tr>";
  print "<td valign=\"top\" colspan=\"2\">";
  print $cgi->h2("Description");
  print $cgi->textfield( -name=>'vdesc', -id=>"vdescupvar", -size=>50, -maxlength=>255, -value=>"$vardata[0]", onkeyup=>"limchar(this);" );
  my $val = 255 - length($vardata[0]);
  print $cgi->textfield( -name=>'vdescupvarlim', -id=>"vdescupvarlim", -size=>3, -readonly=>1, -value=>$val );
  print $cgi->hidden(-name=>'action', -default=>"updatevariable");
  print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
  print "</td></tr>";

  print "<tr><td>".$cgi->h2("Type")."</td><td></td><td></td><td></td></tr>";
  print "<tr><td colspan=\"4\">";
  print $cgi->popup_menu( -name=>'vtype', -id=>'vtypeupvar', -default=>$vardata[1], -values=>[sort {$a <=> $b} keys %vtypes], -labels=>\%vtypes, -onchange=>"get_vtype(this.value,'vtypeup','upvar')" );
  print "</td></tr>";
  print "<tr><td colspan=\"4\"><br><br><div id=\"vtypeup\">";

  if ($vardata[1] == 1){ # categorical
   # get all categories for this variable
   my $query = "select cat, code from variables_cat where variable = \"$vname\" order by cat asc";
   my @cats = ();
   push @cats, "$_->[0]=\"$_->[1]\"" foreach @{$dbh->selectall_arrayref($query)};
   # text box - comma separated quoted list
   print "<label for=\"vt_minupvar\">Categories (comma separated quoted pairs eg 1=\"this\",2=\"that\"):</label>" . $cgi->textarea( -name=>'vt_min', -id=>"vt_minupvar", -default=>join(",",@cats), -rows=>5, -columns=>50 );
   }
  elsif ($vardata[1] == 2){ # continuous
   my $query = "select min, max, prec from variables_con where variable = \"$vname\"";
   my $result = $dbh->selectall_arrayref($query);
   my $min = $result->[0]->[0];
   my $max = $result->[0]->[1];
   my $prec = $result->[0]->[2];
   # 2 x text box - max and min
   print "<label for=\"vt_minupvar\">Min Value:</label>" . $cgi->textfield( -name=>'vt_min', -id=>"vt_minupvar", -size=>20, -default=>$min, -maxlength=>50 );
   print "<label for=\"vt_maxupvar\">Max Value:</label>" . $cgi->textfield( -name=>'vt_max', -id=>"vt_maxupvar", -size=>20, -default=>$max, -maxlength=>50 );
   # decimal point dropdown 1-10
   print "<label for=\"vt_dpupvar\">Decimals:</label>" . $cgi->popup_menu( -name=>'vt_dp', -id=>'vt_dpupvar', -values=>[0 .. 10], -default=>$prec );
   }
  elsif ($vardata[1] == 3){ # date
   my $query = "select min, max from variables_dat where variable = \"$vname\"";
   my $result = $dbh->selectall_arrayref($query);
   my $min = $result->[0]->[0];
   my $max = $result->[0]->[1];
   # 2 x date box - max and min
   print "<label for=\"vt_minupvar\">Min Date:</label>" . $cgi->textfield( -name=>'vt_min', -id=>"vt_minupvar", -size=>10, -maxlength=>10, -default=>$min, -onfocus=>"blank_date('vt_minupvar');", -onblur=>"blank_date('vt_minupvar');" );
   print "<label for=\"vt_maxupvar\">Max Date:</label>" . $cgi->textfield( -name=>'vt_max', -id=>"vt_maxupvar", -size=>10, -maxlength=>10, -default=>$max, -onfocus=>"blank_date('vt_maxupvar');", -onblur=>"blank_date('vt_maxupvar');" );
   }

  print "</div>";

  print "<tr><td>".$cgi->h2("Missing")."</td><td></td><td></td><td></td></tr>";
  print "<tr><td colspan=\"4\">";
  print $cgi->checkbox_group( -name=>'missing', -id=>'missingupvar', -values=>[sort {$missing{$a} <=> $missing{$b}} keys %missing], -labels=>\%missing, -columns=>2, -default=>\@missingcheck );
  print "</td></tr></table>";
   
  print "<table><tr>";
  print "<td style=\"text-align:right\"><br>";
  print $cgi->button(-name=>"sub_upvar", -value=>"Submit", -onclick=>"check_var('upvar');");
  print "</td>";
  print "<td></td><td><br>\n";
  #print $cgi->button(-name=>"res_upvar", -value=>"Reset", -onclick=>"get_vinfo(document.getElementById('vnameupvar').value,'vinfo');");
  print $cgi->button(-name=>"res_upvar", -value=>"Reset", -onclick=>"get_vinfo($vname,'vinfo');");
  print "</td></tr></table>";

  }
 }
elsif ($type eq "vt" ){
 if ($vtype == 1){
  # text box - comma separated quoted list
  print "<label for=\"vt_min$ftype\">Categories (comma separated quoted pairs eg 1=\"this\",2=\"that\"):</label>" . $cgi->textarea( -name=>'vt_min', -id=>"vt_min$ftype", -rows=>5, -columns=>50);
  }
 elsif ($vtype == 2){
  # 2 x text box - max and min
  print "<label for=\"vt_min$ftype\">Min Value:</label>" . $cgi->textfield( -name=>'vt_min', -id=>"vt_min$ftype", -size=>20, -maxlength=>50 );
  print "<label for=\"vt_max$ftype\">Max Value:</label>" . $cgi->textfield( -name=>'vt_max', -id=>"vt_max$ftype", -size=>20, -maxlength=>50 );
  # decimal point dropdown 0-10
  print "<label for=\"vt_dp$ftype\">Decimals:</label>" . $cgi->popup_menu( -name=>'vt_dp', -id=>"vt_dp$ftype", -values=>[0 .. 10] );
  }
 elsif ($vtype == 3){
  # 2 x date box
  print "<label for=\"vt_min$ftype\">Min Date:</label>" . $cgi->textfield( -name=>'vt_min', -id=>"vt_min$ftype", -size=>10, -maxlength=>10, -value=>"YYYY-MM-DD", -onfocus=>"blank_date(\"vt_min$ftype\");", -onblur=>"blank_date(\"vt_min$ftype\");" );
  print "<label for=\"vt_max$ftype\">Max Date:</label>" . $cgi->textfield( -name=>'vt_max', -id=>"vt_max$ftype", -size=>10, -maxlength=>10, -value=>"YYYY-MM-DD", -onfocus=>"blank_date(\"vt_max$ftype\");", -onblur=>"blank_date(\"vt_max$ftype\");" );
  }
 }
elsif ( $type eq "rv" ){
 unless ($vname == 0) {
  print "<br>";
  print "<table><tr><td>";
  print $cgi->button(-name=>"sub_remvar", -value=>"Submit", -onclick=>"check_var('remvar');");
  print "</td><td>";
  print $cgi->button(-value=>"Reset", -onclick=>"get_mvd_info('var',$sname,'mvd_info');");
  print "</td></tr></table>";
  }
 }
################
# Dynamic Tables
################
elsif ( $type eq "cdt" ){
 # check if a name of this dt exists with this value
 if ($dtname eq ""){
  print "<span class=\"warn\">Name cannot be blank</span>";
  print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
  }
 elsif ($dtname =~ m/\s+/){
  print "<span class=\"warn\">Name cannot contain spaces</span>";
  print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
  }
# elsif (length($dtname) > 4){
#  print "<span class=\"warn\">Name must be less than 4 characters</span>";
#  print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
#  }
 else {
  # Note that this does not take delstat in to account and will complain even if "deleted" dts share the same name
  # the db admin can remove dts with the new name BUT as the db is InnoDB this will remove any data for that dt
  my $check = $dbh->selectrow_array("select name from dtables where name = \"$dtname\" and study = $sname");
  if ($check) {
   print "<span class=\"warn\">Name already exists</span>";
   print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
   }
  else {
   print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>1);
   }
  }
 }
elsif ( $type eq "dti" ){
 if ($dtname > 0){
  # get all variables
  #my $query = "select v_auto, variable from variables where study = $sname and delstat = 0";
  my @ddnames = $dbh->selectrow_array("select dd_version from dtables where tid = \"$dtname\"");
  my $query = "select v.v_auto, v.variable from variables as v, datadictionaries_variables as ddv where v.v_auto = ddv.variable and ddv.dd_version = $ddnames[0] and v.delstat = 0";
  my %variables = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($query)};
  # get all variables for this dynamic table
  my $query = "select dtv.vid from dtables_variables as dtv, variables as v where v.v_auto = dtv.vid and v.delstat = 0 and tid = \"$dtname\"" ;
  my @variablecheck = ();
  push @variablecheck, $_->[0] foreach @{$dbh->selectall_arrayref($query)};
  my @dtdata = $dbh->selectrow_array("select description from dtables where tid = \"$dtname\" and delstat = 0");

  print $cgi->h2("Description");
  print $cgi->textfield( -name=>'dtdesc', -id=>"dtdescupdt", -size=>50, -maxlength=>100, -value=>$dtdata[0], -onkeyup=>"limchar(this);" );
  my $val = 100 - length($dtdata[0]);
  print $cgi->textfield( -name=>'dtdescupdtlim', -id=>"dtdescupdtlim", -size=>2, -readonly=>1, -value=>$val );
  print $cgi->h2("Variables");

  print $cgi->checkbox_group( -name=>'variable', -id=>'variableupdt', -values=>[sort {$variables{$a} cmp $variables{$b}} keys %variables], -labels=>\%variables, -columns=>8, -default=>\@variablecheck );

  print "<table><tr>";
  print "<td style=\"text-align:right\"><br>";
  print $cgi->button(-name=>"sub_updt", -value=>"Submit", -onclick=>"check_dt('updt');");
  print "</td>";
  print "<td></td><td><br>\n";
  print $cgi->button(-name=>"res_updt", -value=>"Reset", -onclick=>"get_dtinfo($dtname,'dtinfo');");
  print "</td></tr></table><br>";
  }
 }
elsif ( $type eq "rdt" ){
 unless ($dtname == 0) {
  print "<br>";
  print "<table><tr><td>";
  print $cgi->button(-name=>"sub_remdt", -value=>"Submit", -onclick=>"check_dt('remdt');");
  print "</td><td>";
  print $cgi->button(-value=>"Reset", -onclick=>"get_mvd_info('dt',$sname,'mvd_info')");
  print "</td></tr></table>";
  }
 }

################
# Data Dictionaries
################
elsif ( $type eq "cdd" ){
 # check if a version of this dd exists with this number
 if ($ddname eq ""){
  print "<span class=\"warn\">Version cannot be blank</span>";
  print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
  }
 elsif ($ddname =~ m/\s+/){
  print "<span class=\"warn\">Version cannot contain spaces</span>";
  print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
  }
 elsif ($ddname !~ m/^\d+$/){
  print "<span class=\"warn\">Version must be an integer</span>";
  print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
  }
 elsif (length($ddname) > 4){
  print "<span class=\"warn\">Version must be less than 4 characters</span>";
  print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
  }
 else {
  # Note that this does not take delstat in to account and will complain even if "deleted" dds share the same name
  # the db admin can remove dds with the new name BUT as the db is InnoDB this will remove any data for that dd
  my $check = $dbh->selectrow_array("select dd_version from datadictionaries where dd_version = \"$ddname\" and study = $sname");
  if ($check) {
   print "<span class=\"warn\">Version already exists</span>";
   print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
   }
  else {
   print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>1);
   }
  }
 }
elsif ( $type eq "ddi" ){
 if ($ddname > 0){
  # get all variables
  my $query = "select v_auto, variable from variables where study = $sname and delstat = 0";
  my %variables = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($query)};
  # get all variables for this datadictionary
  my $query = "select dv.variable from datadictionaries_variables as dv, variables as v where v.v_auto = dv.variable and v.delstat = 0 and dd_version = \"$ddname\"" ;
  my @variablecheck = ();
  push @variablecheck, $_->[0] foreach @{$dbh->selectall_arrayref($query)};
  my @dddata = $dbh->selectrow_array("select dd_date from datadictionaries where dd_auto = \"$ddname\" and delstat = 0");

  print $cgi->h2("Date");
  print $cgi->textfield( -name=>'dddate', -id=>"dddateupdd", -size=>50, -maxlength=>50, -value=>$dddata[0], -onkeyup=>"limchar(this);" );
  my $val = 50 - length($dddata[0]);
  print $cgi->textfield( -name=>'dddatupddlim', -id=>"dddateupddlim", -size=>2, -readonly=>1, -value=>$val );
  print $cgi->h2("Variables");

  print $cgi->checkbox_group( -name=>'variable', -id=>'variableupdd', -values=>[sort {$variables{$a} cmp $variables{$b}} keys %variables], -labels=>\%variables, -columns=>8, -default=>\@variablecheck );

  print "<table><tr>";
  print "<td style=\"text-align:right\"><br>";
  print $cgi->button(-name=>"sub_updd", -value=>"Submit", -onclick=>"check_dd('updd');");
  print "</td>";
  print "<td></td><td><br>\n";
  #print $cgi->button(-name=>"res_updd", -value=>"Reset", -onclick=>"get_ddinfo(document.getElementById('ddnameupdd').value,'ddinfo');");
  print $cgi->button(-name=>"res_updd", -value=>"Reset", -onclick=>"get_ddinfo($ddname,'ddinfo');");
  print "</td></tr></table><br>";
  }
 }
elsif ( $type eq "rdd" ){
 unless ($ddname == 0) {
  print "<br>";
  print "<table><tr><td>";
  print $cgi->button(-name=>"sub_remdd", -value=>"Submit", -onclick=>"check_dd('remdd');");
  print "</td><td>";
  print $cgi->button(-value=>"Reset", -onclick=>"get_mvd_info('dd',$sname,'mvd_info')");
  print "</td></tr></table>";
  }
 }

# disconnect query user
$dbh->disconnect();

if ($action){

 print $cgi->start_html(
        -title=>'ViPAR Web based Analysis Portal - Variables Management Event',
        -style=>[ {'src'=>"/viparstyle/vipar.css"} ],
        -head => [ $cgi->meta({ -http_equiv => 'Pragma', -content => 'no-cache' }),
                $cgi->meta({ -http_equiv => 'Expires', -content => '-1' }) ]
        );

 my $dbuser = $dbconfig->get("database_adminuser");
 my $dbpass = $dbconfig->get("database_adminpass");
 
 # connect to the database
 $dbh = DBI->connect($dsn, $dbuser, $dbpass, \%attr);

 $dbh->do("lock tables missing write, variables write, variables_type write, variables_cat write, variables_con write, variables_dat write, variables_missing write, datadictionaries write, datadictionaries_variables write, dtables write, dtables_variables write");

 # get all missing vals
 my $query = "select m_auto, value from missing where study = $sname and delstat = 0";
 my %missing = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($query)};

 # get all variables
 my $query = "select v_auto, variable from variables where study = $sname and delstat = 0";
 my %variables = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($query)};

 # get all variable types
 my $query = "select vt_auto, type from variables_type";
 my %types = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($query)};

 if ( $action eq "newmissing" ){
  print "New missing value added:<br><br>Value = $mname<br>Description = $mdesc";
  $dbh->do("insert into missing (value,description,study) VALUES (\"$mname\",\"$mdesc\",\"$sname\")");
  }
 elsif ( $action eq "updatemissing" ){
  my $mname_name = $dbh->selectrow_array("select value from missing where m_auto = $mname and delstat = 0");
  print "Missing value $mname_name updated<br><br>Description = $mdesc";
  $dbh->do("update missing set description=\"$mdesc\" where m_auto = $mname");
  }
 elsif ( $action eq "deletemissing" ){
  my $mname_name = $dbh->selectrow_array("select value from missing where m_auto = $mname and delstat = 0");
  print "Missing value $mname_name deleted<br><br>This missing value cannot be reused until it is permanently deleted from the database by your system administrator.";
  $dbh->do("update missing set delstat = 1 where m_auto = $mname");
  }
 elsif ( $action eq "newvariable" ){
  my $vtype_name = $types{$vtype};
  print "New variable added:<br><br>Name = $vname<br>Description = $vdesc<br><br>Type = $vtype_name<br>";
  $dbh->do("insert into variables (variable,description,study,type) VALUES (\"$vname\",\"$vdesc\",$sname,$vtype);");
  my $vnameid = $dbh->last_insert_id(undef,"vipar","variables",undef);
  if ($vtype == 1){
   print "<br>Categories";
   foreach my $ccd (@vt_mins){
    $ccd =~ m/^(\d+)=(".+")$/;
    my $cat = $1;
    my $code = $2;
    $code =~ s/^"//g;
    $code =~ s/"$//g;
    $code =~ s/"/\\"/g;
    $code =~ s/=/\=/g;
    print "<br>&nbsp;&nbsp;&nbsp;$cat = \"$code\"";
    $dbh->do("insert into variables_cat (variable,cat,code) VALUES ($vnameid,$cat,\"$code\")");
    }
   }
  elsif ($vtype == 2){
   print "<br>Range<br>Min = $vt_min<br>Max = $vt_max<br>Precision = $vt_dp dps<br>";
   $dbh->do("insert into variables_con (variable,min,max,prec) VALUES ($vnameid,$vt_min,$vt_max,$vt_dp)");
   }
  elsif ($vtype == 3){
   print "<br>Date Range<br>Min = $vt_min<br>Max = $vt_max<br>";
   $dbh->do("insert into variables_dat (variable,min,max) VALUES ($vnameid,\"$vt_min\",\"$vt_max\")");
   }
  print "<br>Missing Values";
  foreach my $mis (@missing){
   print "<br>&nbsp;&nbsp;&nbsp;$missing{$mis}";
   $dbh->do("insert into variables_missing (variable,missing) VALUES ($vnameid,$mis)");
   }
  }
 elsif ( $action eq "updatevariable" ){
  my $vname_name = $variables{$vname};
  my $vtype_name = $types{$vtype};
  print "Variable $vname_name updated<br><br>Description = $vdesc<br><br>Type = $vtype_name<br>";
  $dbh->do("update variables set description=\"$vdesc\", type = $vtype where v_auto = $vname");
  # empty the extra tables 
  $dbh->do("delete from variables_cat where variable = $vname");
  $dbh->do("delete from variables_con where variable = $vname");
  $dbh->do("delete from variables_dat where variable = $vname");
  $dbh->do("delete from variables_missing where variable = $vname");
  # now fill them
  if ($vtype == 1){
   print "<br>Categories";
   foreach my $ccd (@vt_mins){
    $ccd =~ m/^(\d+)=(".+")$/;
    my $cat = $1;
    my $code = $2;
    $code =~ s/^"//g;
    $code =~ s/"$//g;
    $code =~ s/"/\\"/g;
    $code =~ s/=/\=/g;
    print "<br>&nbsp;&nbsp;&nbsp;$cat = \"$code\"";
    $dbh->do("insert into variables_cat (variable,cat,code) VALUES ($vname,$cat,\"$code\")");
    }
   }
  elsif ($vtype == 2){
   print "<br>Range<br>Min = $vt_min<br>Max = $vt_max<br>Precision = $vt_dp dps<br>";
   $dbh->do("insert into variables_con (variable,min,max,prec) VALUES ($vname,$vt_min,$vt_max,$vt_dp)");
   }
  elsif ($vtype == 3){
   print "<br>Date Range<br>Min = $vt_min<br>Max = $vt_max<br>";
   $dbh->do("insert into variables_dat (variable,min,max) VALUES ($vname,\"$vt_min\",\"$vt_max\")");
   }
  print "<br>Missing Values";
  foreach my $mis (@missing){
   print "<br>&nbsp;&nbsp;&nbsp;$missing{$mis}";
   $dbh->do("insert into variables_missing (variable,missing) VALUES ($vname,$mis)");
   }
  }
 elsif ( $action eq "deletevariable" ){
  my $vname_name = $variables{$vname};
  print "Variable $vname_name deleted<br><br>This variable name cannot be reused until it is permanently deleted from the database by your system administrator.";
  $dbh->do("update variables set delstat = 1 where v_auto = $vname");
  }
 elsif ( $action eq "newdatadictionary" ){
  print "New Data Dictionary added<br><br>Version = $ddname<br>Date = $dddate<br><br>Variables";
  $dbh->do("insert into datadictionaries (dd_version,dd_date,study) VALUES ($ddname,\"$dddate\",$sname)");
  my $ddnameid = $dbh->last_insert_id(undef,"vipar","datadictionaries",undef);
  foreach my $var (@variable){
   print "<br>&nbsp;&nbsp;&nbsp;$variables{$var}";
   $dbh->do("insert into datadictionaries_variables (dd_version,variable) VALUES ($ddnameid,$var)");
   }
  }
 elsif ( $action eq "updatedatadictionary" ){
  my @dddata = $dbh->selectrow_array("select dd_version,dd_date from datadictionaries where dd_auto = \"$ddname\" and delstat = 0");
  print "Data Dictionary $dddata[0] - $dddata[1] updated<br><br>Date = $dddate<br><br>Variables";
  $dbh->do("update datadictionaries set dd_date = \"$dddate\" where dd_auto = $ddname");
  # delete current variables
  $dbh->do("delete from datadictionaries_variables where dd_version = $ddname");
  foreach my $var (@variable){
   print "<br>&nbsp;&nbsp;&nbsp;$variables{$var}";
   $dbh->do("insert into datadictionaries_variables (dd_version,variable) VALUES ($ddname,$var)");
   }
  }
 elsif ( $action eq "deletedatadictionary" ){
  my @dddata = $dbh->selectrow_array("select dd_version,dd_date from datadictionaries where dd_auto = \"$ddname\" and delstat = 0");
  print "Data Dictionary $dddata[0] - $dddata[1] deleted<br><br>This Data Dictionary version cannot be reused until it is permanently deleted from the database by your system administrator.\n";
  $dbh->do("update datadictionaries set delstat = 1 where dd_auto = $ddname");
  }
 elsif ( $action eq "newdynamictable" ){
  print "New Dynamic Table added<br><br>Name = $dtname<br>Description = $dtdesc<br><br>Variables";
  $dbh->do("insert into dtables (name,description,study,dd_version) VALUES (\"$dtname\",\"$dtdesc\",$sname,$ddname)");
  my $dtnameid = $dbh->last_insert_id(undef,"vipar","dtables",undef);
  foreach my $var (@variable){
   print "<br>&nbsp;&nbsp;&nbsp;$variables{$var}";
   $dbh->do("insert into dtables_variables (tid,vid) VALUES ($dtnameid,$var)");
   }
  }
 elsif ( $action eq "updatedynamictable" ){
  my @dtdata = $dbh->selectrow_array("select name from dtables where tid = \"$dtname\" and delstat = 0");
  print "Dynamic Table $dtdata[0] updated<br><br>Description = $dtdesc<br><br>Variables";
  $dbh->do("update dtables set description = \"$dtdesc\" where tid = $dtname");
  # delete current variables
  $dbh->do("delete from dtables_variables where tid = $dtname");
  foreach my $var (@variable){
   print "<br>&nbsp;&nbsp;&nbsp;$variables{$var}";
   $dbh->do("insert into dtables_variables (tid,vid) VALUES ($dtname,$var)");
   }
  }
 elsif ( $action eq "deletedynamictable" ){
  my @dtdata = $dbh->selectrow_array("select name from dtables where tid = \"$dtname\" and delstat = 0");
  print "Dynamic Table $dtdata[0] deleted<br><br>This Dynamic Table name cannot be reused until it is permanently deleted from the database by your system administrator.\n";
  $dbh->do("update dtables set delstat = 1 where tid = $dtname");
  }

 $dbh->do("unlock tables");
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

