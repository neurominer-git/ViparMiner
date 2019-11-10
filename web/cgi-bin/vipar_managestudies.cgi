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
my $action = $cgi->param('action');
my $sname = $cgi->param('sname');
my $sdesc = $cgi->param('sdesc');

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

my $servername = $config{"server_servername"};
my $execport = $config{"server_execport"};
my $execkey = $config{"execkey"};

$stmt = "select username from users where u_auto=$uid and delstat = 0";
my ($user_name) = $dbh->selectrow_array($stmt);

print $cgi->header( -cookie=>[$cookie], -charset=>'utf-8' );

# see what privileges the user has and thus what management interfaces to display
my %user_priv = ();
# get the value of IT from the users table for this user as this gives special privs to add users, studies, variables, DataDictionaries, Sites, servers, resources, projects
$user_priv{'it'} = $dbh->selectrow_array("select it from users where u_auto = $uid and delstat = 0");

# Need to be either IT or Lead to run this script
if ( $user_priv{'it'} < 1 ){

  #log error to VIPARD log file
 my $sock = IO::Socket::INET->new(PeerAddr => $servername,
                                 PeerPort => $execport,
                                 Proto     => 'tcp') or die "can't connect to VIPARD: $!";
 $sock->autoflush(1);        
	
 #send exec key for verification
 print $sock "$execkey\n";
 print $sock "log\n"; #send log command	
 print $sock "error\n"; #send log level
 print $sock "User $user_name has attempted to run $0 but does not not have IT/Admin privileges";
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

if ($type eq "ns"){

 # get all studies
 my $query = "select st_auto, study from study where delstat = 0";
 my %studies = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($query)};
 $studies{0} = "-- Select study --";

 # New Users
 print $cgi->start_multipart_form(
  -method=>'POST',
  -action=>'/viparcgi/vipar_managestudies.cgi',
  -name=>'newstudy',
  -id=>'newstudy',
  );

 print $cgi->h2("Add New Study");
 print "<table><tr>";
 print "<td colspan=\"4\">";
 print $cgi->h2("Study Name");
 print $cgi->textfield( -name=>'sname', -id=>"snamenewstudy", -size=>50, -maxlength=>50, -onblur=>"checks(this.value,'checks');", onkeyup=>"limchar(this);" );
 print $cgi->textfield( -name=>'snamenewstudylim', -id=>"snamenewstudylim", -size=>2, -readonly=>1, -value=>50 );
 print "<br><div id=\"checks\">\n";
 print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
 print "</div>";
 print "</td><td valign=\"top\">";
 print $cgi->h2("Study Description");
 print $cgi->textfield( -name=>'sdesc', -id=>"sdescnewstudy", -size=>50, -maxlength=>255, onkeyup=>"limchar(this);" );
 print $cgi->textfield( -name=>'sdescnewstudylim', -id=>"sdescnewstudylim", -size=>3, -readonly=>1, -value=>255 );
 print $cgi->hidden(-name=>'action', -default=>"new");
 print "</td></tr>";
 print "<tr><td><br>";
 print $cgi->h2("Select the users to add roles to within this study");
 &get_study_users();
 print "</td></tr>";
 print "<tr><td></td>";
 print "<td style=\"text-align:right\"><br>";
 print $cgi->button(-name=>"sub_newstudy", -value=>"Submit", -onclick=>"check_study('newstudy');");
 print "</td>";
 print "<td></td><td><br>\n";
 print $cgi->button(-value=>"Reset", -onclick=>"new_study();");
 print "</td><td></td></tr>";
 print "</table><br>";

 print $cgi->end_multipart_form();

 print $cgi->hr();

# Update Study Users

 print $cgi->start_multipart_form(
  -method=>'POST',
  -action=>'/viparcgi/vipar_managestudies.cgi',
  -name=>'upstudyu',
  -id=>'upstudyu'
  );

 print $cgi->h2("Update Study");
 print $cgi->h2("Study Name");
 print $cgi->popup_menu( -name=>'sname', -id=>'snameupstudy', -values=>[sort keys %studies], -labels=>\%studies, -onchange=>"get_sinfo(this.value,'sinfo');" );
 print $cgi->hidden(-name=>'action',-default=>"update");
 print "<div id=\"sinfo\"></div>";

 print $cgi->end_multipart_form();
 print $cgi->br();
 print $cgi->hr();

# Remove study

 print $cgi->start_multipart_form(
  -method=>'POST',
  -action=>'/viparcgi/vipar_managestudies.cgi',
  -name=>'remstudy',
  -id=>'remstudy',
  );
 
 print $cgi->h2("Remove Study");
 print $cgi->h2("Study Name");
 print $cgi->popup_menu( -name=>'sname', -id=>'snameremstudy', -values=>[sort keys %studies], -labels=>\%studies, -onchange=>"get_submit_s(this.value,'sdel');" );
 print $cgi->hidden(-name=>'action',-default=>"delete");
 print "<div id=\"sdel\"></div>";

 print $cgi->end_multipart_form();
 print $cgi->br();
 print $cgi->hr();

 }
elsif ($type eq "si"){
 unless ($sname == 0){
  # print multi select for users
  print $cgi->br();
  print $cgi->h2("Select the users to add / remove roles within this study");
  print "<div id=\"studu\">";
  &get_study_users($sname);
  print "</div>";
  print "<table><tr><td>";
  print $cgi->button(-name=>"addup_studyusers", -value=>"Add/Update", -onclick=>"adduprem_studyu('upstudyu','up');");
  print "</td><td>";
  print $cgi->button(-name=>"rem_studyusers", -value=>"Remove", -onclick=>"adduprem_studyu('upstudyu','rem');");
  print "</td></tr></table>";
  }
 }
elsif ( $type eq "cs" ){
 # check if a study exists with this name
 $sname =~ s/\s+//g;
 if ($sname eq ""){
  print "<span class=\"warn\">Study name cannot be blank</span>";
  print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
  }
 else {
  # Note that this does not take delstat in to account and will complain even if "deleted" studies share the same name
  # the db admin can remove studies with the new name BUT as the db is InnoDB this will remove any data for that study
  my $check = $dbh->selectrow_array("select study from study where study = \"$sname\"");
  if ($check) {
   print "<span class=\"warn\">A current or old study exists with this name</span>";
   print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
   }
  else {
   print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>1);
   }
  }
 }
elsif ( $type eq "rs" ){
 unless ($sname == 0) {
  print "<br>";
  print "<table><tr><td>";
  print $cgi->button(-name=>"sub_remstudy", -value=>"Submit", -onclick=>"check_study('remstudy');");
  print "</td><td>";
  print $cgi->button(-value=>"Reset", -onclick=>"new_study();");
  print "</td></tr></table>";
  }
 }

# disconnect query user
$dbh->disconnect();

############
# Submission
############

if ($action){

 print $cgi->start_html(
        -title=>'ViPAR Web based Analysis Portal - Study Management Event',
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

 $dbh->do("lock tables study write, users read, users_study write");

 if ( $action eq "new" ){
  print "New study added:<br><br>Study name = $sname<br>Description = $sdesc<br><br>";
  $dbh->do("insert into study (study,description) VALUES (\"$sname\",\"$sdesc\")");
  my $sid = $dbh->last_insert_id(undef,undef,undef,undef);

  my $stmt = "select u_auto,username from users where delstat = 0";
  my %all_users = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($stmt)};
  my @users_s = $cgi->param("users_s");
  my @users_l = $cgi->param("users_l");
  my @users_h = $cgi->param("users_h");
  &upsu(\@users_s,$sid,1,undef,$dbh);
  &upsu(\@users_h,$sid,3,undef,$dbh);
  &upsu(\@users_l,$sid,2,undef,$dbh);

  print "Study Users added:";
  if (scalar(@users_s) > 0){ print "<br>&nbsp;&nbsp;&nbsp;" . $all_users{$_} foreach @users_s; }
  else { print "<br>&nbsp;&nbsp;&nbsp;No change"; }
  print "<br><br>Study Leads";
  if (scalar(@users_l) > 0){ print "<br>&nbsp;&nbsp;&nbsp;" . $all_users{$_} foreach @users_l; }
  else { print "<br>&nbsp;&nbsp;&nbsp;No change"; }
  print "<br><br>Data Certification Coordinator";
  if (scalar(@users_h) > 0){ print "<br>&nbsp;&nbsp;&nbsp;" . $all_users{$_} foreach @users_h; }
  else { print "<br>&nbsp;&nbsp;&nbsp;No change"; }
  }
 elsif ( $action eq "delete" ){
  my $sname_name = $dbh->selectrow_array("select study from study where st_auto = $sname and delstat = 0");
  print "Study $sname_name deleted<br><br>This study name cannot be reused until it is permanently deleted from the database by your system administrator.\n";
  $dbh->do("update study set delstat = 1 where st_auto = $sname");
  }
 elsif ( $action eq "update" ){

  my $stmt = "select u_auto,username from users where delstat = 0";
  my %all_users = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($stmt)};
  my @users_s = $cgi->param("users_s");
  my @users_l = $cgi->param("users_l");
  my @users_h = $cgi->param("users_h");
  my $uprem = $cgi->param("uprem");
  &upsu(\@users_s,$sname,1,$uprem,$dbh);
  &upsu(\@users_h,$sname,3,$uprem,$dbh);
  &upsu(\@users_l,$sname,2,$uprem,$dbh);

  print "Study Users updated:<br>" if $uprem eq "up";
  print "Study Users removed:<br>" if $uprem eq "rem";
  print "<br>Study Users\n";
  if (scalar(@users_s) > 0){ print "<br>&nbsp;&nbsp;&nbsp;" . $all_users{$_} foreach @users_s; }
  else { print "<br>&nbsp;&nbsp;&nbsp;No change"; }
  print "<br><br>Study Leads";
  if (scalar(@users_l) > 0){ print "<br>&nbsp;&nbsp;&nbsp;" . $all_users{$_} foreach @users_l; }
  else { print "<br>&nbsp;&nbsp;&nbsp;No change"; }
  print "<br><br>Data Certification Coordinator";
  if (scalar(@users_h) > 0){ print "<br>&nbsp;&nbsp;&nbsp;" . $all_users{$_} foreach @users_h; }
  else { print "<br>&nbsp;&nbsp;&nbsp;No change"; }

  }

 $dbh->do("unlock tables");

 # disconnect admin user
 $dbh->disconnect();

 $cgi->end_html();
 }

sub upsu {
my $users = shift;
my $sname = shift;
my $val = shift;
my $ur = shift;
my $dbh = shift;
foreach my $u (@$users){
 # check if user and study exist already
 my $found = $dbh->selectrow_array("select us_auto from users_study where user = $u and study = $sname");
 if ($found) {
  # if so update to val or remove
  $ur eq "up" ? $dbh->do("update users_study set priv = $val where us_auto = $found") : $dbh->do("delete from users_study where us_auto = $found");
  }
 else {
  # if not insert unless being removed
  $dbh->do("insert into users_study (user,study,priv) VALUES ($u,$sname,$val)") unless $ur eq "rem";
  }
 }
}

sub get_study_users {
 # get users and privs
 # Need the study name
 my $study = shift;
 my $st_add = defined $study ? "and us.study = $study" : "";
 # this query should get all the users that are delstat = 0 whether or not they have been assigned to this study
 # but only provide the priv value for this study if it exists 
 my $stmt = "select u_auto,username,priv from users as u left join users_study as us on us.user = u.u_auto $st_add where u.delstat = 0";
 my $query = $dbh->prepare($stmt);
 $query->execute();
 my %users = ();
 my %attributes = ();
 # 1 - Standard User
 # 2 - Study Lead
 # 3 - Data Certification
 my @levels = qw(1 2 3);
 while (my @data = $query->fetchrow_array()){
  $users{$data[0]} = $data[1];
  foreach my $l (@levels){
   $attributes{$l}{$data[0]}{'class'} = 'red' if $data[2] == $l;
   }
  }
 %attributes = () if ! defined $sname;
 
 print "<table cellspacing=\"20\"><tr>";
 print "<td>Standard User<br>"; 
 print $cgi->scrolling_list(
  -name=>'users_s',
  -id=>'users_s',
  -multiple=>'true',
  -size=>5,
  -values=>[sort {$users{$a} cmp $users{$b}} keys %users],
  -labels=>\%users,
  -attributes=>\%{ $attributes{1} }
  );
 print "</td><td>Data Certification Coordinator<br>";
 print $cgi->scrolling_list(
  -name=>'users_h',
  -id=>'users_h',
  -multiple=>'true',
  -size=>5,
  -values=>[sort {$users{$a} cmp $users{$b}} keys %users],
  -labels=>\%users,
  -attributes=>\%{ $attributes{3} }
  );
 print "</td><td>Study Leader<br>";
 print $cgi->scrolling_list(
  -name=>'users_l',
  -id=>'users_l',
  -multiple=>'true',
  -size=>5,
  -values=>[sort {$users{$a} cmp $users{$b}} keys %users],
  -labels=>\%users,
  -attributes=>\%{ $attributes{2} }
  );

 print "</td></tr></table>";
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

