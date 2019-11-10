#!/usr/bin/perl

use strict;
use DBI;
use CGI;
use CGI::Carp qw(fatalsToBrowser);
use CGI::Session;
use CGI::Cookie;
use AppConfig;
use IO::Socket::INET;

my $cgi = new CGI;
my $type = $cgi->param('type');
my $sname = $cgi->param('sname');
my $pname = $cgi->param('pname');
my $psdesc = $cgi->param('psdesc');
my $pdesc = $cgi->param('pdesc');
my $pdisp = $cgi->param('pdisp') eq "yes" ? 1 : 0;
my $pres = $cgi->param('pres');
my @vars = $cgi->param('variable');
my @unamesa = $cgi->param('unamea');
my @unamesg = $cgi->param('unameg');
my $action = $cgi->param('action');
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
 
 #log error to VIPARD log file
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

if ($type eq "np"){
 # get all studies
 my $query = "";
 if ($user_priv{'it'} == 1){ $query = "select st_auto, s.study from study as s where delstat = 0"; }
 elsif ($user_priv{'lead'} == 2){ $query = "select st_auto, s.study from study as s, users_study as us where s.st_auto = us.study and s.delstat = 0 and user = $uid and priv = 2"; }
 my %studies = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($query)};
 $studies{0} = "-- Select Study --";

 print $cgi->h2("Select Study Name");
 print $cgi->popup_menu( -name=>'sname', -id=>'sname', -values=>[sort keys %studies], -labels=>\%studies, -onchange=>"get_sp(this.value,'sp');" );
 print $cgi->br();
 print $cgi->br();
 print $cgi->hr();
 print "<div id=\"sp\"></div>";
 }
elsif ($type eq "npi"){
 if ($sname > 0){
  # get all projects
  my $query = "select p_auto, project, title from projects where study = $sname and delstat = 0";
  my %projects = map { $_->[0], "$_->[1] - $_->[2]"} @{$dbh->selectall_arrayref($query)};
  $projects{0} = "-- Select Project --";

  # get all users
  my $query = "select u_auto,username from users as u, users_study as us where u.u_auto = us.user and us.study = $sname and priv > 0 and u.delstat = 0";
  my %users = map {$_->[0], $_->[1]} @{$dbh->selectall_arrayref($query)};

  # get all variables
#  my $query = "select v_auto, variable from variables where study = $sname and delstat = 0";
#  my %variables = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($query)};

  # get all variables by table
  # would normally use the dtv_auto but as dtables_variables gets wiped on any changes this cannot be done
  my $query = "select dtv.tid, dtv.vid, dt.name, variable from dtables_variables as dtv,variables as v,dtables as dt where dtv.vid = v.v_auto and dtv.tid = dt.tid and v.study = $sname and v.delstat = 0 and dt.study = $sname";
  my %variables = ();
  foreach my $v (@{$dbh->selectall_arrayref($query)}){
   $variables{$v->[2]}{"$v->[0]_$v->[1]"} = $v->[3];
   }

  # get all resources
  my $query = "select r_auto, resource from resources where study = $sname and delstat = 0";
  my %resources = map { $_->[0], "$_->[1]"} @{$dbh->selectall_arrayref($query)};
  my @res_sort = sort { $resources{$a} cmp $resources{$b} } keys %resources;
  $resources{0} = "All Resources";
  unshift @res_sort, 0;

  ################
  # Add Project

  print $cgi->h2("Add New Project");

  print $cgi->start_multipart_form(
   -method=>'POST',
   -action=>'/viparcgi/vipar_manageprojects.cgi',
   -name=>'newproj',
   -id=>'newproj',
   );

  # print text box for title
  print $cgi->h2("Give a name for this project (used in the side menu)");
  print $cgi->textfield( -name=>'pname', -id=>'pnamenewproj', -size=>50, -maxlength=>50, -onblur=>"checkproj(this.value,'cprojdiv');", -onkeyup=>"limchar(this);" );
  print $cgi->textfield( -name=>'pnamenewprojlim', -id=>"pnamenewprojlim", -size=>2, -readonly=>1, -value=>50 );
  print "<br><div id=\"cprojdiv\">\n";
  print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
  print "</div>";
  # print display project on home page
  print $cgi->h2("Display this project on the home page?");
  print $cgi->checkbox( -name=>'pdisp', -id=>'pdispnewproj', -value=>'yes', -label=>"" );
  # print text box for short description
  print $cgi->h2("Give a short description for this project");
  print $cgi->textfield( -name=>'psdesc', -id=>'psdescnewproj', -size=>50, -maxlength=>100, -onkeyup=>"limchar(this);" );
  print $cgi->textfield( -name=>'psdescnewprojlim', -id=>"psdescnewprojlim", -size=>3, -readonly=>1, -value=>100 );
  # print text box for description
  print $cgi->h2("Give a description for this project");
  print $cgi->textfield( -name=>'pdesc', -id=>'pdescnewproj', -size=>50, -maxlength=>255, -onkeyup=>"limchar(this);" );
  print $cgi->textfield( -name=>'pdescnewprojlim', -id=>"pdescnewprojlim", -size=>3, -readonly=>1, -value=>255 );
  print $cgi->hidden(-name=>'action', -default=>"newproject");
  print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");

  # print multi select for analyst users
  print $cgi->h2("Select the analyst users for this project");
  print $cgi->scrolling_list(-name=>'unamea', -id=>'unameanewproj', -multiple=>'true', -size=>5, -values=>[sort {$users{$a} cmp $users{$b}} keys %users], -labels=>\%users );
  # print multi select for guest users
  print $cgi->h2("Select the guest users for this project");
  print $cgi->scrolling_list( -name=>'unameg', -id=>'unamegnewproj', -multiple=>'true', -size=>5, -values=>[sort {$users{$a} cmp $users{$b}} keys %users], -labels=>\%users  );
  # print variables list
  print $cgi->h2("Select the variables for this project");
  print $cgi->checkbox_group( -name=>'ana_sa', -id=>'ana_sa', -values=>['Select all'], -columns=>1, -onclick=>"sa(this,'newproj','variable');" );
#  print $cgi->checkbox_group( -name=>'variable', -id=>'variablenewproj', -values=>[sort {$variables{$a} cmp $variables{$b}} keys %variables], -labels=>\%variables, -columns=>8 );

  foreach my $t (sort {$a cmp $b} keys %variables){
   print "<p>$t</p>";
   # labelattributes doesn't work as it should
   # have reported bug to CGI bugzilla
   # print $cgi->checkbox_group( -name=>'variables', -id=>'variables', -values=>[sort {$a cmp $b} keys %variables], -columns=>10, -labelattributes=>\%variables );
   print $cgi->checkbox_group( -name=>'variable', -id=>'variablenewproj', -values=>[sort {$variables{$t}{$a} cmp $variables{$t}{$b}} keys %{$variables{$t}}], -labels=>\%{$variables{$t}}, -columns=>10 );
   }

  # print sites for the resources available
  # used for certification to allow access to all variables but only for a single particular resource
  # default is all
  print $cgi->h2("Select the resources available to this project");
  print $cgi->popup_menu( -name=>'pres', -id=>'presnewproj', -values=>\@res_sort, -labels=>\%resources );

  print "<table><tr><td style=\"text-align:right\"><br>";
  print $cgi->button(-name=>"sub_newproj", -value=>"Submit", -onclick=>"check_proj('newproj');");
  print "</td>";
  print "<td></td><td><br>\n";
  print $cgi->button(-value=>"Reset", -onclick=>"get_sp($sname,'sp');");
  print "</td><td></td></tr>";
  print "</table><br>";

  print $cgi->end_multipart_form();
  print $cgi->br();
  print $cgi->hr();

  ################
  # Update Project

  print $cgi->h2("Update Project");

  print $cgi->start_multipart_form(
   -method=>'POST',
   -action=>'/viparcgi/vipar_manageprojects.cgi',
   -name=>'upproj',
   -id=>'upproj',
   );

  print $cgi->h2("Project");
  print $cgi->popup_menu( -name=>'pname', -id=>'pnameupproj', -values=>[sort {$projects{$a} cmp $projects{$b}} keys %projects], -labels=>\%projects, -onchange=>"get_pinfo(this.value,'pinfo');" );
  print $cgi->hidden(-name=>'action',-default=>"updateproject");
  print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
  print "<div id=\"pinfo\"></div>";

  print $cgi->end_multipart_form();
  print $cgi->br();
  print $cgi->hr();

  ################
  # Remove Project

  print $cgi->h2("Remove Project");

  print $cgi->start_multipart_form(
   -method=>'POST',
   -action=>'/viparcgi/vipar_manageprojects.cgi',
   -name=>'remproj',
   -id=>'remproj',
   );

  print $cgi->h2("Project");
  print $cgi->popup_menu( -name=>'pname', -id=>'pnameremp', -values=>[sort  {$projects{$a} cmp $projects{$b}} keys %projects], -labels=>\%projects, -onchange=>"get_submit_p(this.value,'pdel',$sname);" );
  print $cgi->hidden(-name=>'action',-default=>"deleteproject");
  print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");
  print "<div id=\"pdel\"></div>";

  print $cgi->end_multipart_form();
  print $cgi->br();
  print $cgi->hr();

  }
 }
elsif ($type eq "cp"){
 # Check if the project name already exists
 $pname =~ s/\s+/_/g;
 if (($pname eq "_") || ($pname eq "")){
  print "<span class=\"warn\">Project name cannot be blank</span>";
  print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
  }
 else {
  # Note that this does not take delstat in to account and will complain even if "deleted" projects share the same name
  # the db admin can remove projects with the new name BUT as the db is InnoDB this will remove any data for that project
  my $check = $dbh->selectrow_array("select project from projects where project = \"$pname\"");
  if ($check){
   print "<span class=\"warn\">A project exists with this name</span>";
   print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
   }
  else {
   print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>1);
   }
  }
 }
elsif ( $type eq "pi"){
 if ($pname > 0){

  # Get project data to display
  my @pdata = $dbh->selectrow_array("select title, description, display, res from projects where p_auto = $pname and delstat = 0");
  # Get users and privileges for this project
  # analysts
  my $query = "select user from users_projects as up, users as u where u.u_auto = up.user and project = $pname and user_level = 1 and delstat = 0";
  my %attr_ua = map { $_->[0], {'selected'=>'yes'} } @{$dbh->selectall_arrayref($query)};
  # guests
  my $query = "select user from users_projects as up, users as u where u.u_auto = up.user and project = $pname and user_level = 2 and delstat = 0";
  my %attr_ug = map { $_->[0], {'selected'=>'yes'} } @{$dbh->selectall_arrayref($query)};
  # Get variables for this project
  #$query = "select pv.variable from projects_variables as pv, variables as v where v.v_auto = pv.variable and project = $pname and delstat = 0";
  $query = "select pv.tid, pv.variable from projects_variables as pv, variables as v where v.v_auto = pv.variable and project = $pname and delstat = 0";
#  my %attr_v = map { $_->[0], {'checked'=>'true' } } @{$dbh->selectall_arrayref($query)};
  my %attr_v = map { $_->[0]."_".$_->[1], {'checked'=>'true' } } @{$dbh->selectall_arrayref($query)};
#  my %attr_v = ();
#  foreach my $pv (@{$dbh->selectall_arrayref($query)}){
#   $attr_v{"$pv->[0]_$pv->[1]"} = '{ "checked"=>"true" }';
#   }

  # get all users
  my $query = "select u_auto,username from users as u, users_study as us where u.u_auto = us.user and us.study = $sname and priv > 0 and u.delstat = 0";
  my %users = map {$_->[0], $_->[1]} @{$dbh->selectall_arrayref($query)};
 
  # get all variables by table
  my $query = "select dtv.tid, dtv.vid, dt.name, variable from dtables_variables as dtv,variables as v,dtables as dt where dtv.vid = v.v_auto and dtv.tid = dt.tid and v.study = $sname and v.delstat = 0 and dt.study = $sname";
  my %variables = ();
  foreach my $v (@{$dbh->selectall_arrayref($query)}){
   $variables{$v->[2]}{"$v->[0]_$v->[1]"} = $v->[3];
   }
#  my $query = "select v_auto, variable from variables where study = $sname and delstat = 0";
#  my %variables = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($query)};

  # get all resources
  my $query = "select r_auto, resource from resources where study = $sname and delstat = 0";
  my %resources = map { $_->[0], "$_->[1]"} @{$dbh->selectall_arrayref($query)};
  my @res_sort = sort { $resources{$a} cmp $resources{$b} } keys %resources;
  $resources{0} = "All Resources";
  unshift @res_sort, 0;
  my %attr_res = ( $pdata[3] => {'selected'=>'yes'} );

  # print display project on home page
  print $cgi->h2("Display this project on the home page?");
  print $cgi->checkbox( -name=>'pdisp', -id=>'pdispupproj', -value=>'yes', -label=>"", -checked=>$pdata[2] );
  # print text box for short description
  print $cgi->h2("Give a short description for this project");
  print $cgi->textfield( -name=>'psdesc', -id=>'psdescupproj', -size=>50, -maxlength=>100, -value=>"$pdata[0]", -onkeyup=>"limchar(this);" );
  my $val = 100 - length($pdata[0]);
  print $cgi->textfield( -name=>'psdescupprojlim', -id=>"psdescupprojlim", -size=>3, -readonly=>1, -value=>$val );
  # print text box for description
  print $cgi->h2("Give a description for this project");
  print $cgi->textfield( -name=>'pdesc', -id=>'pdescupproj', -size=>50, -maxlength=>255, -value=>"$pdata[1]", -onkeyup=>"limchar(this);" );
  $val = 255 - length($pdata[1]);
  print $cgi->textfield( -name=>'pdescupprojlim', -id=>"pdescupprojlim", -size=>3, -readonly=>1, -value=>$val );
  print $cgi->hidden(-name=>'action', -default=>"updateproject");
  print $cgi->hidden(-name=>'sname', -id=>'sname', -default=>"$sname");

  # print multi select for analyst users
  print $cgi->h2("Select the analyst users for this project");
  print $cgi->scrolling_list( -name=>'unamea', -id=>'unameaupproj', -multiple=>'true', -size=>5, -values=>[sort {$users{$a} cmp $users{$b}} keys %users], -labels=>\%users, -attributes=>\%attr_ua );
  # print multi select for guest users
  print $cgi->h2("Select the guest users for this project");
  print $cgi->scrolling_list( -name=>'unameg', -id=>'unamegupproj', -multiple=>'true', -size=>5, -values=>[sort {$users{$a} cmp $users{$b}} keys %users], -labels=>\%users, -attributes=>\%attr_ug );
  # print variables list
  print $cgi->h2("Select the variables for this project");
  print $cgi->checkbox_group( -name=>'ana_sa', -id=>'ana_sa', -values=>['Select all'], -columns=>1, -onclick=>"sa(this,'upproj','variable');" );
#  print $cgi->checkbox_group( -name=>'variable', -id=>'variableupproj', -values=>[sort {$variables{$a} cmp $variables{$b}} keys %variables], -labels=>\%variables, -columns=>8, -attributes=>\%attr_v );

  foreach my $t (sort {$a cmp $b} keys %variables){
   print "<p>$t</p>";
   # labelattributes doesn't work as it should
   # have reported bug to CGI bugzilla
   # print $cgi->checkbox_group( -name=>'variables', -id=>'variables', -values=>[sort {$a cmp $b} keys %variables], -columns=>10, -labelattributes=>\%variables );
   print $cgi->checkbox_group( -name=>'variable', -id=>'variableupproj', -values=>[sort {$variables{$t}{$a} cmp $variables{$t}{$b}} keys %{$variables{$t}}], -labels=>\%{$variables{$t}}, -attributes=>\%attr_v, -columns=>10 );
   }

  print $cgi->h2("Select the resources available to this project");
  print $cgi->popup_menu( -name=>'pres', -id=>'presupproj', -values=>\@res_sort, -labels=>\%resources, -attributes=>\%attr_res );

  print "<table><tr><td style=\"text-align:right\"><br>";
  print $cgi->button(-name=>"sub_upproj", -value=>"Submit", -onclick=>"check_proj('upproj');");
  print "</td>";
  print "<td></td><td><br>\n";
  print $cgi->button(-value=>"Reset", -onclick=>"get_pinfo($pname,'pinfo');");
  print "</td><td></td></tr>";
  print "</table><br>";

  }
 }
elsif ( $type eq "rp"){
 unless ($pname == 0) {
  print "<br>";
  print "<table><tr><td>";
  print $cgi->button(-name=>"sub_remp", -value=>"Submit", -onclick=>"check_proj('remproj');");
  print "</td><td>";
  print $cgi->button(-value=>"Reset", -onclick=>"get_sp($sname,'sp');");
  print "</td></tr></table>";
  }
 }

# disconnect query user
$dbh->disconnect();

################
# Loading Data
################

if ($action){

 print $cgi->start_html(
        -title=>'ViPAR Web based Analysis Portal - Project Management Event',
        -style=>[ {'src'=>"/viparstyle/vipar.css"} ],
        -head => [ $cgi->meta({ -http_equiv => 'Pragma', -content => 'no-cache' }),
                $cgi->meta({ -http_equiv => 'Expires', -content => '-1' }) ]
        );
 
 # reconnect as admin user
 my $dbuser = $dbconfig->get("database_adminuser");
 my $dbpass = $dbconfig->get("database_adminpass");
 my %attr = (
        RaiseError => 1,
        AutoCommit => 0
        );

 my $dbh = DBI->connect($dsn, $dbuser, $dbpass, \%attr);

 $dbh->do("lock tables projects WRITE, projects_variables WRITE, users_projects WRITE, variables READ, users READ, resources READ, dtables WRITE"); 

 # get all tables
 my $query = "select tid, name from dtables where study = $sname and delstat = 0";
 my %tables = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($query)};

 # get all variables
 my $query = "select v_auto, variable from variables where study = $sname and delstat = 0";
 my %variables = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($query)};

 # get all users
 my $query = "select u_auto,username from users where delstat = 0";
 my %users = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($query)};

 # get all resources
 my $query = "select r_auto, resource, description from resources where study = $sname and delstat = 0";
 my %resources = map { $_->[0], "$_->[1] - $_->[2]"} @{$dbh->selectall_arrayref($query)};
 $resources{0} = "All Resources";

 $pname =~ s/\s+/_/g;
 if ( $action eq "newproject" ){
  print "New Project Added:<br><br>Name: $pname<br>Short Description: $psdesc<br>Long Description: $pdesc<br><br>Users:<br>Analysts";
  print "<br>&nbsp;&nbsp;&nbsp;" . $users{$_} foreach @unamesa;
  print "<br>Guests";
  print "<br>&nbsp;&nbsp;&nbsp;" . $users{$_} foreach @unamesg;
  print "<br><br>Resources:<br>&nbsp;&nbsp;&nbsp;" . $resources{$pres} . "<br>";
  print "<br>Variables:";
  foreach my $vs (@vars) { my ($t,$v) = split("_",$vs); print "<br>&nbsp;&nbsp;&nbsp;" . $tables{$t} . "." . $variables{$v}; }
  $dbh->do("insert into projects (project,title,description,display,res,study) VALUES (\"$pname\",\"$psdesc\",\"$pdesc\",$pdisp,$pres,$sname)");
  my $p_id = $dbh->last_insert_id(undef, "vipar", "projects", undef);
  foreach my $vs (@vars) { my ($t,$v) = split("_",$vs); $dbh->do("insert into projects_variables (project,variable,tid) VALUES ($p_id,$v,$t)"); }
  $dbh->do("insert into users_projects (user,project,user_level) VALUES ($_,$p_id,1)") foreach @unamesa;
  $dbh->do("insert into users_projects (user,project,user_level) VALUES ($_,$p_id,2)") foreach @unamesg;
  # Now add the creation of the project folder and code library directories
  my $vipar_home = $ENV{'VIPAR_ROOT'};
  mkdir("$vipar_home/projects/project_$p_id");
  mkdir("$vipar_home/projects/project_$p_id/codelibs");
  mkdir("$vipar_home/projects/project_$p_id/codelibs/deleted");
  mkdir("$vipar_home/projects/project_$p_id/codelibs/rlibs");
  mkdir("$vipar_home/projects/project_$p_id/codelibs/saslibs");
  mkdir("$vipar_home/projects/project_$p_id/codelibs/statalibs");
  mkdir("$vipar_home/projects/project_$p_id/codelibs/matlablibs");
  mkdir("$vipar_home/projects/project_$p_id/sasuserdir");

  # set correct permissions
  # need to know the correct web user - maybe should be in config file
  # apache initially makes this directory
  # when an analysis is run viparadmin makes the files so the group needs to be apache so that the s permission takes effect
  system("chown -R viparadmin:apache $vipar_home/projects/project_$p_id");
  system("chmod -R 770 $vipar_home/projects/project_$p_id"); 
  system("chmod -R g+s $vipar_home/projects/project_$p_id");
  }
 elsif ( $action eq "updateproject" ){
  my $pname_name = $dbh->selectrow_array("select project from projects where p_auto = $pname and delstat = 0");
  print "Project $pname_name updated:<br><br>Name: $pname_name<br>Short Description: $psdesc<br>Long Description: $pdesc<br><br>Users:<br>Analysts";
  print "<br>&nbsp;&nbsp;&nbsp;" . $users{$_} foreach @unamesa;
  print "<br><br>Guests";
  print "<br>&nbsp;&nbsp;&nbsp;" . $users{$_} foreach @unamesg;
  print "<br><br>Resources:<br>&nbsp;&nbsp;&nbsp;" . $resources{$pres};
  print "<br><br>Variables:";
  foreach my $vs (@vars) { my ($t,$v) = split("_",$vs); print "<br>&nbsp;&nbsp;&nbsp;" . $tables{$t} . "." . $variables{$v}; }
  $dbh->do("update projects set project = \"$pname_name\", title = \"$psdesc\", description = \"$pdesc\", display = $pdisp, res = $pres, study = $sname where p_auto = $pname");
  $dbh->do("delete from projects_variables where project = $pname");
  $dbh->do("delete from users_projects where project = $pname");
  $dbh->do("delete from users_projects where project = $pname");
  foreach my $vs (@vars) { my ($t,$v) = split("_",$vs); $dbh->do("insert into projects_variables (project,variable,tid) VALUES ($pname,$v,$t)"); }
  $dbh->do("insert into users_projects (user,project,user_level) VALUES ($_,$pname,1)") foreach @unamesa;
  $dbh->do("insert into users_projects (user,project,user_level) VALUES ($_,$pname,2)") foreach @unamesg;
  }
 elsif ( $action eq "deleteproject" ){
  my $pname_name = $dbh->selectrow_array("select project from projects where p_auto = $pname and delstat = 0");
  print "Project $pname_name deleted<br><br>This project name cannot be reused until it is permanently deleted from the database by your system administrator.";
  $dbh->do("update projects set delstat = 1 where p_auto = $pname");
  }

 $dbh->do("unlock tables");

 # disconnect admin user
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

