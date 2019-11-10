#!/usr/bin/perl

use strict;
use DBI;
use CGI;
use CGI::Carp qw(fatalsToBrowser);
use CGI::Session;
use CGI::Cookie;
use File::DirList;
use Data::Dumper;
use File::stat;
use Time::localtime;
use DateTime;
use AppConfig;
use IO::Socket::INET;

my $cgi = new CGI;
my $type = $cgi->param('type');
my $proj = $cgi->param('proj');
my $rdate = $cgi->param('rdate');
my $rtime = $cgi->param('rtime');
my $head = $cgi->param('head');
my $upfile = $cgi->param('upfilehid');
my $uplib = $cgi->param('uplibhid');
my $lib = $cgi->param('lib');
my $search = $cgi->param('search');
my $file = $cgi->param('file');
my $ver = $cgi->param('ver');
my $message = $cgi->param('message');
my $share = $cgi->param('share');

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


my $servername = $config{"server_servername"};
my $execport = $config{"server_execport"};
my $execkey = $config{"execkey"};

# allowed file extensions for viewing
my @extar = qw(pdf png jpeg jpg tiff bmp txt log gif);
my %exts = map {$_ => 1} @extar;

# Get the name and description of the project from the database
my $stmt = "select project,title,description from projects where p_auto = $proj and delstat = 0";
my $query = $dbh->prepare($stmt);
$query->execute();
my ($project,$projtitle,$desc) = "";
while (my @data = $query->fetchrow_array()){
 $project = $data[0];
 $projtitle = $data[1];
 $desc = $data[2];
 }
$query->finish();

my %projects = ();

#get username
my $user_name = "";
my $stmt = "select username from users where u_auto=$uid and delstat = 0";
my $query = $dbh->prepare($stmt);
$query->execute();
while (my @data = $query->fetchrow_array())
{
	$user_name = $data[0];
}


# get user access level for this project
my $user_level=1; #default access
my $stmt = "select user_level from users_projects where user = $uid and project = $proj";
my $query = $dbh->prepare($stmt);
$query->execute();
if ($query->rows() == 0) #user is not a guest or analyst for this analysis
{
	$user_level = 3; #shared only
}
else
{
	while (my @data = $query->fetchrow_array()){
 		$user_level = $data[0];
	 }
}
$query->finish();



print $cgi->header( -cookie=>[$cookie], -charset=>'utf-8' );

TYPE: if ($type eq "h"){
 # Need to set up the page
 # Give the project name and description
 print "<div style=\"float:left\"><img src=\"/viparimages/project.png\"/></div>";
 print "<div><br>";
 print "<table valign=\"top\"><tr class=\"projhead\"><td><b>Project Name:</b></td><td>$project</td></tr>";
 if ($user_level==1)
 {
  print "<tr class=\"projhead\"><td><b>User level:</b></td><td>Analyst</td></tr>";
 }
 elsif ($user_level==2)
 {
   print "<tr class=\"projhead\"><td><b>User level:</b></td><td>Guest</td></tr>";
 }
 else #user_level==3  
 {
   print "<tr class=\"projhead\"><td><b>User level:</b></td><td>None (shared results only)</td></tr>";
 }

 print "<tr class=\"projhead\"><td><b>Project Title:</b></td><td>$projtitle</td></tr></table><br>";
 # Provide a new run button, and upload only if user level = 1 (ie analyst) - not if 2 = guest

 if ($user_level==1)
 {
	print "<img src=\"/viparimages/newrun_small.png\" /><span class=\"link\" onclick=\"getruninfo($proj,'run');\">New Run</span>\n";
   	print "<img src=\"/viparimages/viewfiles_small.png\" /><span class=\"link\" onclick=\"getprojdates($proj,'rd');\">View Files</span>\n";
	print "<img src=\"/viparimages/blue_library.png\" /><span class=\"link\" onclick=\"codelib($proj,'cl');\">Manage Code Libraries</span>\n";
 }
 elsif ($user_level==2)
 {
	print "<img src=\"/viparimages/viewfiles_small.png\" /><span class=\"link\" onclick=\"getprojdates($proj,'rd');\">View Public Files</span>\n";
 }
 else
 {
	print "<img src=\"/viparimages/viewfiles_small.png\" /><span class=\"link\" onclick=\"getprojdatesshared($proj,'rds');\">View Shared Files</span>\n";
 }

 print "</div><br><hr/>\n"; 

 # make a div for the dates this project has a run for
 # display the dates
 print "<div class=\"maindisplay\" id=\"display\">";

 print "<div id='projsum' class='projdesc'><h2>Project Summary</h2>\n"; # fileman 
 print "<table class=\"projhead\">";
 print "<tr><td><b>Project</b></td><td>$project</td></tr>";
 print "<tr><td><b>Title</b></td><td>$projtitle</td></tr>";

 my $stmt = "select u.u_auto,u.username from users as u, users_projects as up where u.u_auto = up.user and project = $proj and delstat = 0";
 my $query = $dbh->prepare($stmt);
 $query->execute();
 print "<tr><td><b>Investigators</b></td><td>";
 my $count=0;	
 while (my @data = $query->fetchrow_array()){
	$count++;
	if ($count==$query->rows())
	{
		print "$data[1]";
	}
	else
	{
		print "$data[1],";
	}

	if ($count>0 && $count%10==0)
	{
		print "<BR>";
	}
	
 }
 print "</td></tr>";

 print "<tr valign=\"top\"><td><b>Description</b></td><td>$desc</td></tr>";
 
 print "</table>";
 print "</div>\n"; 
 print "<BR>";
 print "<div class=\"projdesc\">\n"; 
 print "<h2>Message Board</h2>";

 if ($user_level != 3) #non-project users cannot post to message board (but they can read it)
 {
	print "<input name=\"postmessage\" type=\"text\" id=\"message\" size=\"80\" maxlength=\"255\" /><button class=\"link\" onclick=\"message($uid,$proj);projheader($proj,'h')\">POST</button><BR>\n";
 }

 my $stmt = "select user,date,message from messageboard where project = $proj order by date desc";
 my $query = $dbh->prepare($stmt);
 $query->execute();
 if ($query->rows()==0)
 {
	print "No messages have been posted for this project<BR>";
 }
 else
 {

	 my $count=0;	
	 while (my @data = $query->fetchrow_array()){
		$count++;

		#get username
		my $un = "";
		my $stmt = "select username from users where u_auto=$data[0] and delstat = 0";
		my $query = $dbh->prepare($stmt);
		$query->execute();
		while (my @data2 = $query->fetchrow_array())
		{
			$un = $data2[0];
		}

		print "<small style=\"background-color:#d4d4d4;\">\"$data[2]\" - posted by <b>$un</b> @ $data[1]</small><BR>" if ($count%2==0);
		print "<small>\"$data[2]\" - posted by <b>$un</b> @ $data[1]</small><BR>" if ($count%2==1);
	}
}
	

 }
elsif ($type eq "rd"){
 print "<div>";
 print "<table><tr><td><input name=\"search\" type=\"text\" id=\"search\" size=\"10\" /></td><td><img src=\"/viparimages/search_green.png\" class=\"link\" onclick=\"search($proj);\"/></td></tr></table>\n";
 print "</div>";
 print "<div class=\"fileman\" id=\"fileman\">\n";
 my $stmt = "select distinct rd_auto,run_date.run_date from run_date,run_time where run_time.run_date = run_date.rd_auto and run_time.project = $proj and run_time.exclude = 0 order by rd_auto desc";
 my $query = $dbh->prepare($stmt);
 $query->execute();
 print "<table class=\"files\">";
 while (my @data = $query->fetchrow_array()){
  print "<tr><td class=\"link\"><span class=\"link\" onclick=\"getprojruntimes($proj,$data[0]);\">$data[1]</span></td></tr>\n";
  }
 $query->finish();
 print "</table>";
 print "</div>\n";
 print "<div class=\"spacer\"></div>";
 print "<div class=\"fileman\" id=\"files\"></div>";
 }
elsif ($type eq "rds"){    #for reading shared projects
 #select run_times that are not deleted and are shared
 my $stmt = "select distinct rd_auto,run_date.run_date from run_date,run_time where run_time.run_date = run_date.rd_auto and run_time.project = $proj and run_time.exclude = 0 and run_time.shared=1 order by rd_auto desc";
 my $query = $dbh->prepare($stmt);
 $query->execute();
 if ($query->rows() ==0)
 {
	#print "<table>";
        print "<h2>There are no results currently shared for this project</h2>\n";
	#print "</table>";
        print "</div>";
 }
 else
 { 
# RF 30/10/14
# have removed this as the search function still returns all data rather than just those that are shared. Also the option of deleting a run is provided when it shouldn't be
# need to redo the search code to take the context of the search in to account.
	print "<div style=\"visibility:hidden\">";
	print "<table><tr><td><input name=\"search\" type=\"text\" id=\"search\" size=\"10\" /></td><td><img src=\"/viparimages/search_green.png\" class=\"link\" onclick=\"search($proj);\"/></td></tr></table>\n";
	print "</div>";
	print "<div class=\"fileman\" id=\"fileman\">\n";


 	print "<table class=\"files\">";
	while (my @data = $query->fetchrow_array()){
	  print "<tr><td class=\"link\"><span class=\"link\" onclick=\"getprojruntimesshared($proj,$data[0]);\">$data[1]</span></td></tr>\n";
	}

	print "</table>";
	print "</div>\n";
	print "<div class=\"spacer\"></div>";
	print "<div class=\"fileman\" id=\"files\"></div>";

 }
 $query->finish();

 }
elsif ($type eq "rtshared"){
 my $stmt = "select username,run_date.run_date,run_time,rt_auto,rd_auto,shared,run_status from users,run_date,run_time where users.u_auto = run_time.user and run_time.run_date = run_date.rd_auto and project = $proj and run_time.run_date = $rdate and exclude = 0 and shared=1 and users.delstat = 0 order by rt_auto desc";
 my $query = $dbh->prepare($stmt);
 $query->execute();
 print "<table class=\"files\">";

 my $colspan = $user_level == 1 ? 5 : 3; #no erase and share box for guest
 print "<tr><td colspan=\"$colspan\"><img src=\"/viparimages/back.png\" class=\"link\" onclick=\"getprojdates($proj,'rds');\" />&nbsp;&nbsp;&nbsp;<img src='/viparimages/refresh_small.png' class=\"link\" onclick=\"getprojruntimesshared($proj,'$rdate');\" /></td></tr>\n";

 while (my @data = $query->fetchrow_array()){

    print "<tr class=\"filerow\"><td class=\"link\"><span onclick=\"getprojfiles($proj,\'$data[1]\',\'$data[2]\');\">$data[2]</span></td><td class=\"datetime\">$data[1]</td><td>$data[0]</td></tr>";
  }

  $query->finish();
  print "</table>";
}
elsif ($type eq "rt"){
 # delay for a little bit to allow run deletion, sharing and unsharing code to lock the tables
 sleep(1.5);
 my $stmt = "select username,run_date.run_date,run_time,rt_auto,rd_auto,shared,run_status from users,run_date,run_time where users.u_auto = run_time.user and run_time.run_date = run_date.rd_auto and project = $proj and run_time.run_date = $rdate and exclude = 0 and users.delstat = 0 order by rt_auto desc";
 my $query = $dbh->prepare($stmt);
 $query->execute();
 print "<table class=\"files\">";

 my $colspan = $user_level == 1 ? 5 : 3; #no erase and share box for guest
 print "<tr><td colspan=\"$colspan\"><img src=\"/viparimages/back.png\" class=\"link\" onclick=\"getprojdates($proj,'rd');\" />&nbsp;&nbsp;&nbsp;<img src='/viparimages/refresh_small.png' class=\"link\" onclick=\"getprojruntimes($proj,'$rdate');\" /></td></tr>\n";

 while (my @data = $query->fetchrow_array()){

  if ($data[6] > 1) # still running
  {
    print "<tr class=\"filerow\"><td class=\"link\"><span onclick=\"getprojfiles($proj,\'$data[1]\',\'$data[2]\');\">$data[2] (running) </span></td><td class=\"datetime center\">$data[1]</td><td class=\"center\">$data[0]</td>";
    ## Kim to change "stoprun" javascript call to the right name!
    #print "<td class=\"center\"><img src=\"/viparimages/stop.png\" class=\"link\" onclick=\"stopruntime($proj,$data[3]);getprojruntimes($proj,$data[4]);\" /></td><td></td>";
    print "<td class=\"center\"><img src=\"/viparimages/stop.png\" class=\"link\" onclick=\"stopruntime($proj,$data[3],$data[4]);\" /></td><td></td>";
  }
  elsif ($data[6] == -1) # failed
  {
    print "<tr class=\"filerow\"><td class=\"link\"><span onclick=\"getprojfiles($proj,\'$data[1]\',\'$data[2]\');\">$data[2] (stopped/error)</span></td><td class=\"datetime center\">$data[1]</td><td class=\"center\">$data[0]</td>";
   #only allow erase and share for analysts, not guest  and if not running
   if ($user_level==1)
   {
     print "<td class=\"center\"><img src=\"/viparimages/fail.png\" class=\"link\" onclick=\"delruntime($proj,$data[3],$data[4]);\" /></td>";
     my $shval = $data[5] == 1 ? 0 : 1;
     print "<td>" . $cgi->checkbox(-name=>'share',-checked=>$data[5],-value=>$data[5],-label=>'Sharing',-onclick=>"shareruntime($proj,$data[3],$data[4],$shval);") . "</td>";
   }
  }
  else # OK
  {
    print "<tr class=\"filerow\"><td class=\"link\"><span onclick=\"getprojfiles($proj,\'$data[1]\',\'$data[2]\');\">$data[2]</span></td><td class=\"datetime center\">$data[1]</td><td class=\"center\">$data[0]</td>"; 

   #only allow erase and share for analysts, not guest  and if not running
   if ($user_level==1)
   {
     print "<td class=\"center\"><img src=\"/viparimages/erase_small.png\" class=\"link\" onclick=\"delruntime($proj,$data[3],$data[4]);\" /></td>";
     my $shval = $data[5] == 1 ? 0 : 1;
     print "<td>" . $cgi->checkbox(-name=>'share',-checked=>$data[5],-value=>$data[5],-label=>'Sharing',-onclick=>"shareruntime($proj,$data[3],$data[4],$shval);") . "</td>";
   }
  }
 print "</tr>\n";




  }
 $query->finish();
 print "</table>";
 }
elsif ($type eq "cl"){
 print "<br>";
 print "<div class=\"filemanauto\" id=\"fileman\">\n";
 print "<table class=\"files\">";
 print "<tr><td class=\"link\"><span class=\"link\" onclick=\"getcodelibs($proj,'r');\">R library</span></td></tr>\n";
 print "<tr><td class=\"link\"><span class=\"link\" onclick=\"getcodelibs($proj,'matlab');\">MATLAB library</span></td></tr>\n";
 print "<tr><td class=\"link\"><span class=\"link\" onclick=\"getcodelibs($proj,'sas');\">SAS library</span></td></tr>\n";
 print "<tr><td class=\"link\"><span class=\"link\" onclick=\"getcodelibs($proj,'stata');\">STATA library</span></td></tr>\n";
 print "</table>";
 print "</div>\n";
 print "<div class=\"spacer\"></div>";
 print "<div class=\"fileman\" id=\"files\"></div>";
 }
elsif ($type eq "s"){
 my @searchwords = split(" ",$search);
 if (scalar(@searchwords) == 0){
  print "Please enter some valid characters in the search box";
  }
 else {
   my $srch = "((";
   for my $w (0 .. $#searchwords){
   $srch .= "run_time.run_time LIKE '%$searchwords[$w]%'";
   $srch .= " AND " unless $w == $#searchwords;
   }
   $srch .= ") OR (";
 
for my $w (0 .. $#searchwords){
   $srch .= "run_time.description LIKE '%$searchwords[$w]%'";
   $srch .= " AND " unless $w == $#searchwords;
   }
   $srch .= "))";

 
#  $srch = "((run_time.run_time $srchbit) OR (run_time.description $srchbit))"; #seach analysis name and description
 
  #print "$srch<br>";

  my $stmt = "select username,run_date.run_date,run_time,rt_auto,rd_auto from users,run_date,run_time where users.u_auto = run_time.user and run_time.run_date = run_date.rd_auto and project = $proj and $srch and exclude = 0 and users.delstat = 0 order by rt_auto desc";
#  print "$stmt<br>";

  my $query = $dbh->prepare($stmt);
  $query->execute();
  if ($query->rows() > 0){
   print "<table class=\"files\">";
   while (my @data = $query->fetchrow_array()){
    print "<tr class=\"filerow\"><td class=\"link\"><span onclick=\"getprojfiles($proj,\'$data[1]\',\'$data[2]\');\">$data[2]</span></td><td>$data[1]</td><td>$data[0]</td><td><img src=\"/viparimages/erase_small.png\" class=\"link\" onclick=\"delruntime($proj,$data[3],$data[1]);search($proj);\" /></td>";
    print "</tr>\n";
    }
   $query->finish();
   print "</table>";
   }
  else {
   print "No results found";
   }
  }
 }
elsif ($type eq "addm"){
	my $dt = DateTime->now();

	# Get the current date based on the current timezone
	my $d = "".$dt->day()."_".$dt->month_abbr()."_".$dt->year()."-".$dt->hour().":".sprintf("%02d",$dt->minute()).":".sprintf("%02d",$dt->second());

	#print "message = $message   date = $d   user = $uid";
	
	my $updbuser = $dbconfig->get("database_queryuser");
	my $updbpass = $dbconfig->get("database_querypass");
	
	my %attr = (
	RaiseError => 1,
	AutoCommit => 0
	);
	# connect to the database
	my $updbh = DBI->connect($dsn, $updbuser, $updbpass, \%attr);
	$updbh->do("insert into messageboard (user,project,message,date) VALUES ($uid,$proj,\"$message\",\"$d\")");
	$updbh->disconnect();

 }
elsif ($type eq "f"){
 my $dir = $ENV{'VIPAR_ROOT'}."/projects/project_$proj/$rdate/$rtime";
 my $list = File::DirList::list($dir, 'dM', 1, 1, 0);
 print "<table class=\"files\">";
 foreach my $file (@{$list}){
  next if $file->[13] eq "..";
  # don't display the fifo
  next if $file->[13] =~ /^fifo_/;
  my $ext = "";
  if ($file->[13] =~ /\w+\.(\w+)$/){
   $ext = $1;
   }
  my $size = $file->[7];
  my $unit = "b";
  if ($size >= 1000000000){ $size = $size/1000000000; $unit = "Gb"; }
  elsif ($size >= 1000000){ $size = $size/1000000; $unit = "Mb"; }
  elsif ($size >= 1000){ $size = $size/1000; $unit = "Kb"; }
  print "<tr class=\"filerow\"><td>";
  print $cgi->a( {-href=>"/viparcgi/vipar_download.cgi?vd=v&p=$proj&d=$rdate&t=$rtime&f=".$cgi->escape($file->[13]),-target=>"_blank"}, "<img src=\"/viparimages/eye.png\">") if defined $exts{$ext};
  print "</td><td>";
  print $cgi->a( {-href=>"/viparcgi/vipar_download.cgi?vd=d&p=$proj&d=$rdate&t=$rtime&f=".$cgi->escape($file->[13])}, "<img src=\"/viparimages/save_all.png\">");
  print "</td><td>$file->[13]";
  my @time = split(" ",ctime(stat($dir."/".$file->[13])->mtime));
  print "</td><td class=\"datetime\">$time[3]</td>\n";
  printf "<td class=\"datetime\">%.2f$unit</td></tr>\n",$size;
  }
 print "</table>";

 #only show uploads for analyst level users
 if ($user_level==1)
 {
   print "<div class=\"upload\">";
   print "Upload a file to attach to this run<br>";
   print $cgi->start_multipart_form(
                -method=>'POST',
		-name=>'uploadfile',
		-id=>'uploadfile',
                -action=>'/viparcgi/vipar_project.cgi',
		-target=>'upload_target'
                );
   print "<table><tr><td>";
   print $cgi->filefield( -name=>'file', -default=>'upload a file' );
   print $cgi->hidden( -name=>'proj', -value=>$proj );
   print $cgi->hidden( -name=>'rdate', -value=>$rdate );
   print $cgi->hidden( -name=>'rtime', -value=>$rtime );
   print $cgi->hidden( -name=>'upfilehid', -value=>1 );
   print "</td><td>";
   print $cgi->button( -name=>'up', -value=>'Upload', -onclick=>"document.uploadfile.submit();" );
   print "<iframe id=\"upload_target\" name=\"upload_target\" src=\"\" style=\"width:0;height:0;border:0px solid #fff;\"></iframe>";
   print "</td><td>&nbsp;&nbsp;&nbsp;</td><td><img src='/viparimages/refresh_small.png' class=\"link\" onclick=\"getprojfiles($proj,'$rdate','$rtime');\" /></td><td>click to refresh file list</td></tr></table>";
   print $cgi->end_multipart_form();
   print "</div>";
  }

 }
elsif ($type eq "gcl"){
 sleep(1.5);
 my $dir = $ENV{'VIPAR_ROOT'}."/projects/project_$proj/codelibs/$lib"."libs";
 my $list = File::DirList::list($dir, 'dM', 1, 1, 0);
 print "<table class=\"files\">";
 foreach my $file (@{$list}){
  next if $file->[13] eq "..";
  my $size = $file->[7];
  my $unit = "b";
  if ($size >= 1000000000){ $size = $size/1000000000; $unit = "Gb"; }
  elsif ($size >= 1000000){ $size = $size/1000000; $unit = "Mb"; }
  elsif ($size >= 1000){ $size = $size/1000; $unit = "Kb"; }
  print "<tr class=\"filerow\"><td class=\"link\">";
  print $cgi->a( {-href=>"/viparcgi/vipar_download.cgi?vd=d&p=$proj&l=$lib&f=".$cgi->escape($file->[13])},$file->[13]);
  my @time = split(" ",ctime(stat($dir."/".$file->[13])->mtime));
  print "</td><td class=\"datetime\">$time[0] $time[1] $time[2] $time[4]</td>\n";
  print "<td class=\"datetime\">$time[3]</td>\n";
  printf "<td class=\"datetime\">%.2f$unit</td>",$size;
  print "<td><img src=\"/viparimages/erase_small.png\" class=\"link\" onclick=\"delcodelib($proj,'$file->[13]','$lib');\" /></td></tr>\n";
  }
 print "</table>";

 print "<div class=\"upload\">";
 print "Upload a new <b>".uc($lib)."</b> code library<br>";
 print $cgi->start_multipart_form(
                -method=>'POST',
                -name=>'uploadfile',
                -id=>'uploadfile',
                -action=>'/viparcgi/vipar_project.cgi',
                -target=>'upload_target'
                );
 print "<table><tr><td>";
 print $cgi->filefield( -name=>'file', -default=>'upload a file' );
 print $cgi->hidden( -name=>'proj', -value=>$proj );
 print $cgi->hidden( -name=>'lib', -value=>$lib );
 print $cgi->hidden( -name=>'uplibhid', -value=>1 );
 print "</td><td>";
 print $cgi->button( -name=>'up', -value=>'Upload', -onclick=>"document.uploadfile.submit();" );
 print "<iframe id=\"upload_target\" name=\"upload_target\" src=\"\" style=\"width:0px;height:0px;border:0px solid #fff;\"></iframe>";
 print "</td><td>&nbsp;&nbsp;&nbsp;</td><td><img src='/viparimages/refresh_small.png' class=\"link\" onclick=\"getcodelibs($proj,'$lib');\" /></td><td>click to refresh file list</td></tr></table>";
 print $cgi->end_multipart_form();
 print "</div>";
 }
elsif ($type eq "dcl"){
	#print "erasing code lib\n";
	#Move codelib to deleted folder and

	# $lib just contains the filename
	# use the value of the VIPAR_ROOT and the project name to get the full path
	# find the path of the deleted directory
	my $rootdir = $ENV{'VIPAR_ROOT'}."/projects/project_$proj/codelibs/";
	my $cfile = "$rootdir/$lib"."libs/$file";
	my $ddir = "$rootdir/deleted";
	# move the file to the deleted directory with the current timestamp
 
	my $dt = DateTime->now();

	# Get the current date based on the current timezone
	my $d = "".$dt->day()."_".$dt->month_abbr()."_".$dt->year()."-".$dt->hour().":".sprintf("%02d",$dt->minute()).":".sprintf("%02d",$dt->second());

	#move library to deleted libs and timestamp	
	system("\\mv -f $cfile $ddir/$file.$d");

	#log that libraries are deleted by this user at timestamp
	my $sock = IO::Socket::INET->new(PeerAddr => $servername,
                                 PeerPort => $execport,
                                 Proto     => 'tcp') or die "can't connect to VIPARD: $!";
	$sock->autoflush(1);        
	
	#send exec key for verification
	print $sock "$execkey\n";
	print $sock "log\n"; #send log command	
	print $sock "error\n"; #send log level
	print $sock "$user_name has deleted a code library ($file) in project '$projtitle'";
	$sock->close();

	# return the code back to getcodelibs (bit of a hack but works)
#	$type = "gcl";
#	goto TYPE;
 }

elsif ($type eq "shrt"){
 my $dbuser = $dbconfig->get("database_adminuser");
 my $dbpass = $dbconfig->get("database_adminpass");
 # connect to the database
 my $dbh = DBI->connect($dsn, $dbuser, $dbpass, \%attr);
 $dbh->do("lock tables run_time write");
 $dbh->do("update run_time set shared = $share where rt_auto = $rtime");
 $dbh->do("unlock tables");
 $dbh->disconnect();
}
elsif ($type eq "unshrt"){
 my $dbuser = $dbconfig->get("database_adminuser");
 my $dbpass = $dbconfig->get("database_adminpass");
 # connect to the database
 my $dbh = DBI->connect($dsn, $dbuser, $dbpass, \%attr);
 $dbh->do("lock tables run_time write");
 $dbh->do("update run_time set shared = 0 where rt_auto = $rtime");
 $dbh->do("unlock tables");
 $dbh->disconnect();
}
elsif ($type eq "drt"){ #delete runtime
 my $dbuser = $dbconfig->get("database_adminuser");
 my $dbpass = $dbconfig->get("database_adminpass");
 # connect to the database
 my $dbh = DBI->connect($dsn, $dbuser, $dbpass, \%attr);
 $dbh->do("lock tables run_time write");
 $dbh->do("update run_time set exclude = 1 where rt_auto = $rtime");
 $dbh->do("unlock tables");
 $dbh->disconnect();
 }
elsif ($type eq "srt"){  #Stop runtime
	my $sock = IO::Socket::INET->new(PeerAddr => $servername,PeerPort => $execport,Proto => 'tcp') or die "Lost connection to ViPAR daemon - can't connect to port $execport on $servername: $!";
	#print "Successfully connected to $servername:$execport\n";
	$sock->autoflush(1);        

	#send exec key
	print $sock "$execkey\n";

	#send command
	print $sock "stopexec\n";

	#send data
	print $sock "$uid\n"; #uid
	print $sock "$rtime\n"; #rtime to kill

	$sock->close();
	sleep(1);

 }
elsif ($type eq "run"){

 print $cgi->start_multipart_form(
	-method=>'POST',
	-action=>'/viparcgi/vipar_analyse.cgi',
	-target=>'newwindow',
	-name=>'analyse',
	-id=>'analyse',
	-onsubmit=>"wopen(this.target,300,300);"
	);

 print $cgi->h2("Choose a title for this analysis (40 char max)");
 print $cgi->textfield( -name=>'aname', -id=>'aname', -size=>40, -maxlength=>40, -onkeyup=>"limchar(this);" );
 print $cgi->textfield( -name=>'anamelim', -id=>"anamelim", -size=>2, -readonly=>1, -value=>40 );
 print "<span class=\"medtext\">note: use letters, numbers, hyphen and underscore <strong><span style=\"color:red; text-decoration:underline\">only</span></strong> i.e. A-Z,a-z,0-9,-,_</span><br>";

 print $cgi->h2("Enter a description for this analysis (optional)");
 print $cgi->textfield( -name=>'description', -id=>"desc", -size=>100, -maxlength=>255, -onkeyup=>"limchar(this);" );
 print $cgi->textfield( -name=>'desclim', -id=>"desclim", -size=>3, -readonly=>1, -value=>255 );
 print "<br>";

 # Firstly get all the variables for this project from projects_variables
 my $stmt = "select v.v_auto from variables as v, projects_variables as pv where v.v_auto = pv.variable and v.delstat = 0 and pv.project = '$proj'";
 my $query = $dbh->prepare($stmt);
 $query->execute();
 my %variables = ();
 while (my @data = $query->fetchrow_array()){
  $variables{$data[0]}++;
  }
 $query->finish();

 # establish which data dictionaries contain these variables
 # this is complicated query as the project could have numerous variables spread over a few DDs As the user has selected a particular dd then we only want to see variables from that dd
 # display the data dictionaries
 $stmt = "select DISTINCT dd.dd_auto, dd.dd_version, dd_date from datadictionaries as dd, datadictionaries_variables as ddv where dd.dd_auto = ddv.dd_version and dd.delstat = 0 and variable in (".join(",",keys %variables).")";
 $query = $dbh->prepare($stmt);
 $query->execute();
 my %versions = ();
 while (my @data = $query->fetchrow_array()){
  $versions{$data[0]} = "Version $data[1] - $data[2]";
  }
 $query->finish();
 $versions{0} = "-- Select Version --";

 # print menu for versions
 print $cgi->h2("Select the data dictionary version for this project");
 print $cgi->popup_menu(
  -name=>'version',
  -values=>[sort {$a <=> $b} keys %versions],
  -labels=>\%versions,
  -onchange=>"changeverrun(this.value,$proj);"
  );
 
 print "<div id=\"verdiv\"></div>\n";
 }
elsif ($type eq "cvr"){
 if ($ver > 0){

  # see if this project restricts the resources displayed
  my $stmt = "select res from projects where p_auto = $proj and delstat = 0";
  my $resval = $dbh->selectrow_array($stmt);

  # get all the resources that are either certified for all projects or just this one
  my $stmt = "select r_auto,resource,available from resources as r,server as s,site as si where r.server=s.sv_auto and s.site=si.s_auto and s.delstat = 0 and r.delstat = 0 and si.delstat = 0 and cert>=0 and datadictionary = $ver";

  my $query = $dbh->prepare($stmt);
  $query->execute();
  my %resources = ();
  my %attr_r = ();
  while (my @data = $query->fetchrow_array()){
   if ($resval == 0){ # not restricted to resource
    $resources{$data[1]}++;
    $attr_r{$data[1]} = {'disabled' => 'yes'} if $data[2] != 1;
    }
   else {
    if ($resval == $data[0]){
     $resources{$data[1]}++;
     $attr_r{$data[1]} = {'disabled' => 'yes'} if $data[2] != 1;
     }
    }
   }
  $query->finish();

  # get the variables used for this project
  #$stmt = "select v.v_auto from variables as v, projects_variables as pv where v.v_auto = pv.variable and v.delstat = 0 and pv.project = '$proj'";
  $stmt = "select dt.name, pv.tid, pv.variable, v.variable from variables as v, projects_variables as pv, dtables as dt where v.v_auto = pv.variable and pv.tid = dt.tid and v.delstat = 0 and dt.delstat = 0 and pv.project = '$proj'";
  $query = $dbh->prepare($stmt);
  $query->execute();
  my %vvariables = ();
  my %variables = ();
  while (my @data = $query->fetchrow_array()){
#   $vvariables{$data[0]}++;
   $variables{$data[0]}{"$data[1]_$data[2]"} = $data[3];
   }
  $query->finish();

=cut
  # this needs tidying up as currently there are variables with the same name that exist in different tables (e.g. SITE) and when this selection appears, variables and tables that were not part of the project definition appear

  # use version to get the available variables in the version
  # this is complicated query as the project could have numerous variables spread over a few DDs As the user has selected a particular dd then we only want to see variables from that dd
  $stmt = "select v.variable,v.description,dt.name from variables as v, datadictionaries_variables as dv, dtables as dt, dtables_variables as dtv where dv.variable = v.v_auto and dtv.tid = dt.tid and dtv.vid = v.v_auto and dv.dd_version = $ver and v_auto in (".join(",",keys %vvariables).")";
  $query = $dbh->prepare($stmt);
  $query->execute();
  my %variables = ();
  while (my @data = $query->fetchrow_array()){
   # labelattributes doesn't work as it should
   # title is only assigned to the first label
   # have reported this to CGI bugzilla
   # $variables{$data[0]} = {'title'=>$data[1]};
   $variables{$data[2]}{$data[0]} = $data[1];
   }
  $query->finish();
=cut
=cut
  $stmt = "select v.variable,v.description from variables as v, datadictionaries_variables as dv where dv.variable = v.v_auto and dv.dd_version = $ver and v.delstat = 0 and v_auto in (".join(",",keys %vvariables).")";
  $query = $dbh->prepare($stmt);
  $query->execute();
  my %variables = ();
  while (my @data = $query->fetchrow_array()){
   # labelattributes doesn't work as it should
   # acronym is only assigned to the first label
   # have reported this to CGI bugzilla
   #$variables{$data[0]} = {'acronym'=>$data[1]};
   $variables{$data[0]} = $data[1];
   }
  $query->finish();
=cut
  # Can't do an analysis if there aren't any either variables or resources
  if (!keys %resources || !keys %variables)
  {
	print "<BR><b>No resources/variables are available (ie sites down) or configured for this project - please contact your study administrator</b><br>\n";
  }
  else
  {
  ## use the version to get the resources in the version
  ## again the resources in vresources might be spread over a few data dictionaries so need to only get the ones in the right dd

  print $cgi->h2("Choose resources");
  # For some reason the sa function doesn't like single checkbox values
  # It calls them an input field instead of a node list
  # As a result it can't cycle through the loop in the function which is the whole point
  # So don't display the Select All if there's only one box to select from
  print $cgi->checkbox_group( -name=>'res_sa', -id=>'res_sa', -values=>['Select all'], -columns=>1, -onclick=>"sa(this,'analyse','resources');" ) if scalar(keys %resources) > 1;
  print $cgi->checkbox_group( -name=>'resources', -id=>'resources', -values=>[sort {$a cmp $b} keys %resources], -columns=>5, -attributes=>\%attr_r );

  print $cgi->h2("Choose analysis variables");
  # For some reason the sa function doesn't like single checkbox values
  # It calls them an input field instead of a node list
  # As a result it can't cycle through the loop in the function which is the whole point
  # So don't display the Select All if there's only one box to select from
  print $cgi->checkbox_group( -name=>'ana_sa', -id=>'ana_sa', -values=>['Select all'], -columns=>1, -onclick=>"sa(this,'analyse','variables');" ) if scalar(keys %variables) > 1;

  foreach my $t (sort {$a cmp $b} keys %variables){
   print "<p>$t</p>";
   # labelattributes doesn't work as it should
   # have reported bug to CGI bugzilla
   # print $cgi->checkbox_group( -name=>'variables', -id=>'variables', -values=>[sort {$a cmp $b} keys %variables], -columns=>10, -labelattributes=>\%variables );
   print $cgi->checkbox_group( -name=>'variables', -id=>'variables', -values=>[sort {$variables{$t}{$a} cmp $variables{$t}{$b}} keys %{$variables{$t}}], -labels => \%{$variables{$t}}, -columns=>10 );
   print "<span class=\"medtext\">where:</span>";
   print $cgi->textarea( -name=>"$t\_where", -id=>"$t\_where", -rows=>2, -columns=>50 );
   }

=cut
  print $cgi->checkbox_group( -name=>'ana_sa', -id=>'ana_sa', -values=>['Select all'], -columns=>1, -onclick=>"sa(this,'analyse','variables');" ) if scalar(keys %variables) > 1;
  # labelattributes doesn't work as it should
  # have reported bug to CGI bugzilla
  # print $cgi->checkbox_group( -name=>'fields', -id=>'fields', -values=>[keys %fields], -columns=>10, -labelattributes=>\%fields );
  print $cgi->checkbox_group( -name=>'variables', -id=>'variables', -values=>[sort {$a cmp $b} keys %variables], -columns=>10 );
=cut

  #get details of stats packages from vipar_config table
  my $stmt = "select v_key,v_value from vipar_config where v_key in ('stats_r','stats_matlab','stats_sas','stats_stata')";
  my %config = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($stmt)};


  print $cgi->h2("Choose analysis package");
  my %packages = ();
  $packages{'r'} = 'R' if exists($config{"stats_r"});
  $packages{'matlab'} = 'MATLAB' if exists($config{"stats_matlab"});
  $packages{'sas'} = 'SAS' if exists ($config{"stats_sas"});
  $packages{'stata'} = 'STATA' if exists ($config{"stats_stata"});
  print join(%config,"");

  print $cgi->popup_menu(
	-name=>'package',
	-values=>[sort {$a cmp $b} keys %packages],
	-labels=>\%packages,
	-default=>['r'],
        -onChange=>'statsinfo(this.value);'
	);

  print "<p>See below for how the data will be presented to your selected stats package</p>";
  print $cgi->h2("Type your syntax");
  print $cgi->textarea( -name=>'syntax', -rows=>25, -columns=>100 );
  print $cgi->hidden( -name=>'proj', -value=>$proj );
  print "<div id=\"statwrap\">";
  
 # R info
  print "<div id=\"r_info\">";
  print <<RINFO;
<pre>
Data is retrieved from each selected site for each selected variable from each table.
The data for each table is then presented to R in a dataframe named after the source table
where the header names are the selected variable names.

For example if you select ASD_CODE from ASD_COND and DOB from DEMOG then you will get two dataframes,
ASD_COND and DEMOG and data for the two variables are accessible via ASD_COND\$ASD_CODE and DEMOG\$DOB.
</pre>
RINFO
  print "</div>";
  
  # MATLAB info
  print "<div id=\"matlab_info\" class=\"hidinit\">";
  print <<MATLABINFO;
<pre>
Data is retrieved from each selected site for each selected variable from each table.
Each variable is made available to the MATLAB script below.
Code library can be accessed through the MATLABLIBS environment variable
</pre>
MATLABINFO
  print "</div>";

  # SAS info
  print "<div id=\"sas_info\" class=\"hidinit\">";
  print <<SASINFO;
<pre>
Data is retrieved from each selected site for each selected variable from each table.
The data for each table is then presented to SAS as a standard dataset named after the source table
where the header names are the selected variable names.

For example if you select ASD_CODE from ASD_COND and DOB from DEMOG then you will get two data sets,
ASD_COND and DEMOG and data for the two variables are accessible via ASD_COND\$ASD_CODE and DEMOG\$DOB. 
</pre>
SASINFO
  print "</div>";

  # STATA info
  print "<div id=\"stata_info\" class=\"hidinit\">";
  print <<STATAINFO;
<pre>
Data is retrieved from each selected site for each selected variable from each table.
The data for each table is then separately held in RAM on the server and accessible only by reading
from a "pipe" which acts as a file (but with no data). Once the pipe is read, the data is available, 
but the pipe cannot be read again.

In R and SAS this data would have been pre-read from the pipe and neatly presented in separate objects.
Stata does not possess this functionality natively and while the -infile- function has recently been altered
to read pipes the -merge- and -append- functions do not. Therefore the solution has been to use a hybrid of 
R and Stata.

In the syntax box above you first need to provide R code to perform your data manipulation and merging to create 
a single master dataset in the form of a dataframe called minerva. Then you provide your standard Stata syntax.
You separate the two types of syntax with the following (exactly!):

## END R SYNTAX ##

There's information at the following post regarding the different joins you can achieve using R's -merge- function
and there is also a link to an alternative approach using the sqldf package which is installed: 
http://stackoverflow.com/questions/1299871/how-to-join-merge-data-frames-inner-outer-left-right

In terms of accessing the data in R, as above data is retrieved from each selected site for each selected variable
from each table. The data for each table is then presented to R in a dataframe named after the source table
where the header names are the selected variable names.
 
For example if you select ASD_CODE and CID from ASD_COND and CID and GEST_AGE from BIRTH then you will get two dataframes,
ASD_COND and BIRTH and data for the variables are accessible via e.g. ASD_COND\$ASD_CODE and BIRTH\$GEST_AGE. You can then
merge this data using the common CID variable e.g.

minerva <- merge(ASD_COND,BIRTH,by="CID")

The data contained in minerva will then get passed automatically to Stata.
All data is brought in to Stata as a str15 data type so as part of your Stata syntax you need to loop over your numerical variables
and use -destring- to re-type them to numeric:

foreach var of varlist cid gest_age {
 destring `var', replace
}

</pre>
STATAINFO
  print "</div>";
  

  print "</div>";
  print $cgi->br();
  print $cgi->br();
  print $cgi->submit( -name=>'submit', -value=>'Analyse' );
  print $cgi->reset( -name=>'reset', -value=>'Reset' );
  }


  print $cgi->end_multipart_form();
  }
 }

# File uploading
if ($upfile){
 my $outfile = $ENV{'VIPAR_ROOT'}."/projects/project_$proj/$rdate/$rtime/$file";
 open(OUT,">$outfile") || die "Can't open output file $outfile:$!\n\n";
 binmode OUT;
 print OUT $_ while(<$file>);
 close(OUT);
 }

if ($uplib){
 my $outfile = $ENV{'VIPAR_ROOT'}."/projects/project_$proj/codelibs/$lib"."libs/$file";
 open(OUT,">$outfile") || die "Can't open codelibs output file $outfile:$!\n\n";
 binmode OUT;
 print OUT $_ while(<$file>);
 close(OUT);
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

        if (defined($dbh))
        {
                $dbh->disconnect();
        }
        exit(1);

}

$dbh->disconnect();
