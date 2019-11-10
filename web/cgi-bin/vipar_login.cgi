#!/usr/bin/perl

use strict;
use CGI;
use CGI::Carp qw(fatalsToBrowser);
use CGI::Session;
use DBI;
use AppConfig;
use IO::Socket::INET;

my $cgi = new CGI;

my $user = $cgi->param('user');
my $pass = $cgi->param('pass');

#&sitedown() unless $user =~ m/richard/;  # uncomment for when you wish to disable logins while performing maintenance
#&sitedown();  # uncomment for when you wish to disable logins while performing maintenance

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
my $dbh = DBI->connect($dsn, $dbuser, $dbpass, \%attr);

#get details and check VIPARD is running
my $stmt = "select v_key,v_value from vipar_config where v_key in ('server_servername','server_execport','execkey')";
my %config = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($stmt)};

if (!keys %config)  #if nothing returned
{
	print $cgi->header();
	print $cgi->start_html(
		-title=>'Virtual Pooling and Analysis of Research data - ViPAR',);
	print "<p style=\"font-size:20px;font-family:verdana,geneva,sans-serif;color:red;\">Virtual Pooling and Analysis of Research data - VIPARD is not currently running. Please contact the site administrators</p>";
	$cgi->end_html();

	$dbh->disconnect();

	exit(1);
}


$stmt="select email from users where username='viparadmin'";
my ($email) = $dbh->selectrow_array($stmt);
my $servername = $config{"server_servername"};
my $execport = $config{"server_execport"};
my $execkey = $config{"execkey"};

# Now we authenticate the user
$stmt = "select u_auto from users where username = '$user' and password = '$pass' and delstat = 0";
my $query = $dbh->prepare($stmt);
$query->execute();
my $uid = $query->fetchrow_array();
$query->finish();
$dbh->disconnect();

&err_login if (!$uid);

# now the person has been authenticated
# make a session cookie
my $session = new CGI::Session("driver:File", undef, {Directory=>'/tmp'});
$session->expire('+1h');
my $cookie = $cgi->cookie(
	-name=>'VIPAR_CGISESSID',
	-value=> $session->id(),
	-expires=> '+1h'
	);

# send the cookie to the browser
print $cgi->header( -cookie=>$cookie, -charset=>'utf-8' );

# put some info in to the session
$session->param("userid",$uid);

#log warning-level to VIPARD log file
my $sock = IO::Socket::INET->new(PeerAddr => $servername,
                         PeerPort => $execport,
                         Proto     => 'tcp') or die "can't connect to VIPARD: $!";
$sock->autoflush(1);        

#send exec key for verification
print $sock "$execkey\n";
print $sock "log\n"; #send log command	
print $sock "warning\n"; #send log level
print $sock "Successful login for user '$user', from IP address ".$cgi->remote_host()."\n"; #uid
$sock->close();
	
# redirect to the project management interface
print $cgi->start_html(
	-head => $cgi->meta({
		-http_equiv => 'Refresh',
		-content => '0;URL=/viparcgi/vipar_home.cgi'
		})
	);
print $cgi->end_html();

sub err_login
{
	#log error to VIPARD log file
	my $sock = IO::Socket::INET->new(PeerAddr => $servername,
                                 PeerPort => $execport,
                                 Proto     => 'tcp') or die "can't connect to VIPARD: $!";
	$sock->autoflush(1);        
	
	#send exec key for verification
	print $sock "$execkey\n";
	print $sock "log\n"; #send log command	
	print $sock "error\n"; #send log level
	print $sock "Failed login attempt for user '$user', from IP address ".$cgi->remote_host()."\n"; #uid
	$sock->close();

	print $cgi->header();
	print $cgi->start_html(
		-title=>'Virtual Pooling and Analysis of Research - ViPAR',
		-style=>{'src'=>"/viparstyle/vipar.css"}
	);
	my $url = '/vipar';
	print "<script>alert(\"You have entered an incorrect username or password. Please try again (note, failed attempts are logged for security purposes). If you have any further problems, please contact the site administrators on $email.\");</script>";
	print $cgi->end_html();
	
	print "<meta http-equiv=\"refresh\" content=\"0;URL=$url\">\n";
	
	exit(1);
 }

sub sitedown {
 print $cgi->header( -charset=>'utf-8' );
 print $cgi->start_html(
	-title=>'Virtual Pooling and Analysis of Research data - ViPAR - Site Down',
	-style=>{'src'=>"/viparstyle/vipar.css"}
	);
 print "<p class='sitedown'>The site is down while I reload data for Australia.<br><br>Please check back later.<br><br>Work should completed by 8:00am GMT 04/04/2017<br><br>Apologies for the inconvenience.<br>Richard</p>";
 print $cgi->end_html();
 exit(1);
 }
