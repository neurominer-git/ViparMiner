#!/usr/bin/perl

# need code for adding, updating, deleting users
#mysql> describe users;
#+-----------+---------------------+------+-----+---------+----------------+
#| Field     | Type                | Null | Key | Default | Extra          |
#+-----------+---------------------+------+-----+---------+----------------+
#| username  | varchar(50)         | YES  |     | NULL    |                |
#| password  | varchar(50)         | YES  |     | NULL    |                |
#| u_auto    | int(11)             | NO   | PRI | NULL    | auto_increment |
#| time_zone | varchar(50)         | YES  |     | NULL    |                |
#| email     | varchar(50)         | YES  |     | NULL    |                |
#| it        | tinyint(1) unsigned | YES  |     | 0       |                |
#+-----------+---------------------+------+-----+---------+----------------+
# Adding
# 	Need username
# 		Check using AJAX whether username exists
# 		Can do this when box loses focus
# 	Need password
# 		Use dictionary code to generate a new password
# 		Store Encrypted password (can always generate a new one)
# 	Timezone
# 		Use list of timezones as input (generate on the fly)
# 	Email
# 	IT
# 		Should be set to 0 unless user is IT user (tick box)
# Updating
# 	Can't change username (only delete user)
# 	Updating passwords (use same code to make a new password)
# 	Same code to list timezones
# 	Can update email and IT status
# Deleting
# 	Consider whether user's projects should be deleted
#

use strict;
use DBI;
use CGI;
use CGI::Carp qw(fatalsToBrowser);
use CGI::Session;
use CGI::Cookie;
use Data::Dumper;
use DateTime::TimeZone;
use Crypt::GeneratePassword qw(word chars);
use AppConfig;
use IO::Socket::INET;

my $cgi = new CGI;
my $type = $cgi->param('type');
my $action = $cgi->param('action');
my $uname = $cgi->param('uname');
my $email = $cgi->param('email');
my $uit = $cgi->param('it');
$uit = 0 if !$uit;
my $time_zone = $cgi->param('time_zone');
my $passwd = $cgi->param('password');
my $pre = $cgi->param('pre');

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

# Need to be either IT to run this script
if ( $user_priv{'it'} < 1 ){
 
	 # log error to VIPARD log file
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

# make timezone list
my @tz = DateTime::TimeZone->all_names();

############
# Interfaces
############

if ($type eq "nu"){

 # get all users
 my $query = "select u_auto, username from users where delstat = 0;";
 my %users = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($query)};
 $users{0} = "-- Select username --";

# New Users

 print $cgi->start_multipart_form(
  -method=>'POST',
  -action=>'/viparcgi/vipar_manageusers.cgi',
  -name=>'newuser',
  -id=>'newuser',
  );

 print $cgi->h2("Add New User");
 print "<table><tr>";
 print "<td colspan=\"4\">";
 print $cgi->h2("Username");
 print $cgi->textfield( -name=>'uname', -id=>"unamenewuser", -size=>50, -maxlength=>50, -onblur=>"checku(this.value,'checku');", -onkeyup=>"limchar(this);");
 print $cgi->textfield( -name=>'unamenewuserlim', -id=>"unamenewuserlim", -size=>2, -readonly=>1, -value=>50 );
 print "<br><div id=\"checku\">\n";
 print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
 print "</div>";
 print "</td><td></td></tr><tr><td colspan=\"4\">";
 print $cgi->checkbox( -name=>'it', -value=>1, -id=>"itnewuser", -label=>'Admin user' );
 print "</td><td>";
 print $cgi->h2("Generate a password <img src='/viparimages/refresh_small.png' onclick=\"newpass('newp1','newuser');\" />");
 print "<div id=\'newp1\'>";
 print $cgi->textfield( -name=>'password', -id=>"passwordnewuser", -size=>50, -maxlength=>50 );
 print "</div>";
 print "</tr><td colspan=\"4\">";
 print $cgi->h2("Email address");
 print $cgi->textfield( -name=>'email', -id=>"emailnewuser", -size=>50, -maxlength=>50, -onkeyup=>"limchar(this);");
 print $cgi->textfield( -name=>'emailnewuserlim', -id=>"emailnewuserlim", -size=>2, -readonly=>1, -value=>50 );
 print "</td><td>";
 print $cgi->h2("Timezone");
 print $cgi->popup_menu( -name=>'time_zone', -id=>'time_zonenewuser', -values=>\@tz );
 print $cgi->hidden(-name=>'action', -default=>"new");
 print "</td></tr><td></td><td style=\"text-align:right\"><br>";
 print $cgi->button(-name=>"sub_newuser", -value=>"Submit", -onclick=>"check_user('newuser');");
 print "</td><td></td><td><br>\n";
 print $cgi->button(-value=>"Reset", -onclick=>"new_user();");
 print "</td><td></td></tr></table><br>";

 print $cgi->end_multipart_form();


# Update Users

 print $cgi->start_multipart_form(
  -method=>'POST',
  -action=>'/viparcgi/vipar_manageusers.cgi',
  -name=>'upuser',
  -id=>'upuser',
  );

 print $cgi->hr();

 print $cgi->h2("Update User");
 print $cgi->h2("Username");
 print $cgi->popup_menu( -name=>'uname', -id=>'unameupuser', -values=>[sort { $users{$a} cmp $users{$b} } keys %users], -labels=>\%users, -onchange=>"get_uinfo(this.value,'uinfo');" );
 print $cgi->hidden(-name=>'action',-default=>"update");
 print "<div id=\"uinfo\"></div><br>";

 print $cgi->end_multipart_form();

# Remove Users

 print $cgi->start_multipart_form(
  -method=>'POST',
  -action=>'/viparcgi/vipar_manageusers.cgi',
  -name=>'remuser',
  -id=>'remuser',
  );
 
 print $cgi->hr();
 
 print $cgi->h2("Remove User");
 print $cgi->h2("Username");
 print $cgi->popup_menu( -name=>'uname', -id=>'unameremuser', -values=>[sort { $users{$a} cmp $users{$b} } keys %users], -labels=>\%users, -onchange=>"get_submit_u(this.value,'udel');" );
 print $cgi->hidden(-name=>'action',-default=>"delete");
 print "<div id=\"udel\"></div>";

 print $cgi->end_multipart_form();
 print $cgi->br();
 print $cgi->hr();
 
 }
elsif ( $type eq "np" ){
 my $minlen = 10;
 my $maxlen = 10;
 my @set = ('a'..'z','A'..'Z',2..9);
 my $characters = "O o l I";
 my $pass = &word($minlen,$maxlen);
 my $pw_id = "password$pre";
 print $cgi->textfield( -name=>'password', -id=>"$pw_id", -size=>50, -maxlength=>50, -value=>"$pass" );
 }
elsif ( $type eq "uu" ){
 unless ($uname == 0) {
  my @userdata = $dbh->selectrow_array("select it, password, email, time_zone from users where u_auto = \"$uname\" and delstat = 0");
  print "<table><tr><td colspan=\"4\">";
  print $cgi->checkbox( -name=>'it', -id=>"itupuser", -label=>'Admin user', -checked=>$userdata[0], -value=>1 );
  print "</td><td>";
  print $cgi->h2("Generate a password <img src='/viparimages/refresh_small.png' onclick=\"newpass('newp2','upuser');\" /><img src='/viparimages/undo.png' onclick=\"reset_pass();\" />");
  print "<div id=\'newp2\'>";
  print $cgi->textfield( -name=>'password', -id=>"passwordupuser", -size=>50, -maxlength=>50, -value=>"$userdata[1]" );
  print "</div>";
  print $cgi->hidden(-name=>'password_orig', -id=>"password_orig", -default=>"$userdata[1]" );
  print "</tr><td colspan=\"4\">";
  print $cgi->h2("Email address");
  print $cgi->textfield( -name=>'email', -id=>"emailupuser", -size=>50, -maxlength=>50, -value=>$userdata[2], -onkeyup=>"limchar(this);" );
  my $val = 50 - length($userdata[2]);
  print $cgi->textfield( -name=>'emailupuserlim', -id=>"emailupuserlim", -size=>2, -readonly=>1, -value=>$val );
  print "</td><td>";
  print $cgi->h2("Timezone");
  print $cgi->popup_menu( -name=>'time_zone', -id=>"time_zoneupuser", -value=>\@tz, -default=>$userdata[3] );
  print "</td></tr><td></td><td style=\"text-align:right\"><br>";
  print $cgi->button(-name=>"sub_upuser", -value=>"Submit", -onclick=>"check_user('upuser');");
  print "</td><td></td><td><br>\n";
  print $cgi->button(-value=>"Reset", -onclick=>"new_user();");
  print "</td><td></td></tr></table><br>";
  }
 }
elsif ( $type eq "ru" ){
 unless ($uname == 0) {
  print "<br>";
  print "<table><tr><td>";
  print $cgi->button(-name=>"sub_remuser", -value=>"Submit", -onclick=>"check_user('remuser');");
  print "</td><td>";
  print $cgi->button(-value=>"Reset", -onclick=>"new_user();");
  print "</td></tr></table>";
  }
 }
elsif ( $type eq "cu" ){
 # check if a user exists with this name
 $uname =~ s/\s+//g;
 if ($uname eq ""){
  print "<span class=\"warn\">Username cannot be blank</span>";
  print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
  }
 else {
  # Note that this does not take delstat in to account and will complain even if "deleted" users share the same name
  # the db admin can remove users with the new name BUT as the db is InnoDB this will remove any data for that user
  my $check = $dbh->selectrow_array("select username from users where username = \"$uname\"");
  if ($check) {
   print "<span class=\"warn\">A current or old user exists with this name</span>";
   print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>0);
   }
  else {
   print $cgi->hidden(-name=>'csubmit',-id=>"csubmit",-default=>1);
   }
  }
 }

# disconnect query user
$dbh->disconnect();

############
# Submission
############

if ($action){

 print $cgi->start_html(
        -title=>'ViPAR Web based Analysis Portal - User Management Event',
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

 $dbh->do("lock table users WRITE");
 
 if ( $action eq "new" ){
  my $itu = $uit == 1 ? "YES" : "NO";
  print "New user added:<br><br>Username = $uname<br>email = $email<br>Admin user = $itu<br>Timezone = $time_zone<br>Password = $passwd";
  $dbh->do("insert into users (username,email,it,time_zone,password) VALUES (\"$uname\",\"$email\",$uit,\"$time_zone\",\"$passwd\")");
  }
 elsif ( $action eq "update" ){
  my $uname_name = $dbh->selectrow_array("select username from users where u_auto = $uname and delstat = 0");
  my $itu = $uit == 1 ? "YES" : "NO";
  print "User $uname_name updated:<br><br>Username = $uname_name<br>email = $email<br>Admin user = $itu<br>Timezone = $time_zone<br>Password = $passwd";
  $dbh->do("update users set email=\"$email\", it=$uit, time_zone=\"$time_zone\", password=\"$passwd\" where u_auto = $uname");
  }
 elsif ( $action eq "delete" ){
  my $uname_name = $dbh->selectrow_array("select username from users where u_auto = $uname and delstat = 0");
  print "User $uname_name deleted<br><br>This username cannot be reused until it is permanently deleted from the database by your system administrator.";
  $dbh->do("update users set delstat=1 where u_auto = $uname");
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

