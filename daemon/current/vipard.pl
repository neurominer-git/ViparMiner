#!/usr/bin/perl

#  VIPAR daemon 
#
#  Kim Carter and Richard Francis, 2014
#  26/06/2015 - RF added relational database code
#  05/03/2017 - RF added RAM usage optimisation
#  
#  version 2.1.0 - RAM usage optimisation
#

# Includes
use threads;
use threads::shared;
use AppConfig;
use strict;
#use warnings;
use Proc::Daemon;
use Fcntl qw/ :flock /;  # for exclusive locking of log files
use Fcntl qw(O_WRONLY);  # 
use Log::Dispatch;
use Log::Dispatch::File; 
use Log::Dispatch::FileShared; #for shared flocking
use Date::Format;
use Log::Dispatch::File::Rolling; #for shared flocking
use Log::Dispatch::FileRotate;
use IO::Compress::Gzip qw(gzip $GzipError);
use IO::Uncompress::Gunzip qw(gunzip $GunzipError);
use MIME::Lite;
use Data::Dumper;
use POSIX qw(getpid);
use DBI;
use IO::Socket::INET;
use DateTime;
use Misc::Stopwatch;
use File::Util;
use File::Copy;

#Global shared variables
my $execpool :shared = shared_clone({});
my %glob :shared = ();
my %pollthreadhash :shared = ();
my %execthreadhash : shared = ();

##########
#
# DEFINE VARIABLES
#
##########
$ENV{'VIPAR_ROOT'}="/usr/local/vipar";
my $db_file = $ENV{'VIPAR_ROOT'}."/daemon/current/db.conf";
my $vipard_file =  $ENV{'VIPAR_ROOT'}."/daemon/current/vipard.conf";
my $filepath = $ENV{'VIPAR_ROOT'}."/projects";
my $dpid = $ENV{'VIPAR_ROOT'}."/daemon/current/vipard.pid";

if ($#ARGV!=0)
{
	die "usage perl vipard.pl <start|stop>\n";
}
elsif($ARGV[0] eq "start")
{
	#die "VIPARD is already running\n";
	##########
	#
	# CHECK IF DAEMON IS RUNNING
	#
	##########
	if (-e "$dpid")  #check if lock file exists
	{
		my $lockpid = `cat $dpid`; #check if process if running	
		my $ex = kill 0, $lockpid;
		if ($ex)
		{
			print "VIPAR daemon is already running\n";
			exit(0);
		}
		else
		{
			print "VIPAR daemon appears to have stopped running ... removing $dpid \n";
			unlink("$dpid");
		}
	}
}
elsif($ARGV[0] eq "stop")
{
	if (-e "$dpid")  #check if lock file exists
	{
		my $lockpid = `cat $dpid`; #check if process if running	

		#print "Lockpid = $lockpid\n";		
		my $newexists = kill 0, $lockpid;		
		if ($newexists == 0)
		{
			#not running
			print "VIPAR daemon is not currently running\n";
			unlink("$dpid");
		}
		else
		{
			$newexists = kill 1, $lockpid;
			#print "VIPRD status: $newexists\n";
			print "VIPAR daemon is now stopped\n";
			unlink("$dpid");
		}
	}
	else
	{
		print "VIPAR daemon is not currently running\n";
	}
	exit(0);
}
else
{
	die "usage perl vipard.pl <start|stop>\n";
}

# START THE DAEMON
print "Starting VIPAR daemon\n";

##########
#
# LOAD CONFIG
#
##########

my $config = AppConfig->new({ERROR  => \&config_error});
my $dbconfig = AppConfig->new({ERROR  => \&dbconfig_error});

sub config_error()
{
	die "Config error with vipard.conf: Unknown or incorrect variable $_\n";
}

sub dbconfig_error()
{
        die "Config error with db.conf: Unknown or incorrect variable $_\n";
}

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

#define config vars
$config->define("file_logfile=<undef>");
$config->define("file_loglevel=<undef>");
$config->define("server_polling=<undef>");
$config->define("server_pollmode=<undef>");
$config->define("server_execport=<undef>");
$config->define("server_servername=<undef>");
$config->define("server_sshpath=<undef>");
$config->define("server_smtphost=<undef>");
$config->define("server_smtpport=<undef>");
$config->define("server_smtpuser=<undef>");
$config->define("server_smtppass=<undef>");
$config->define("stats_r=<undef>");
$config->define("stats_matlab=<undef>");
$config->define("stats_stata=<undef>");
$config->define("stats_sas=<undef>");


# read configuration file
$dbconfig->file($db_file);

#check all DB options are set
my %conf = $dbconfig->varlist("database_*");
foreach my $c (keys %conf)
{
        if ( !defined($dbconfig->get($c)) )
        {
                die "Option $c not set in config file $db_file ... exiting\n";
        }
}

# read configuration file
$config->file($vipard_file);

#check all vipard options are set
%conf = $config->varlist("file_*|server_*");
if (!defined($config->get("server_smtphost")))   #if no smtpserver defined, set it to none
{
	$config->set("server_smtphost","none");
}
if (!defined($config->get("server_smtpport")))   #if no smtpport defined, set it to 25
{
	$config->set("server_smtpport","25");
}


#++ need to sanitise this input as some of it is inserted into a table and could contain dodgy code
foreach my $c (keys %conf)
{
	if ( !defined($config->get($c)) )
	{
		if ($c ne "server_smtpuser" && $c ne "server_smtppass")
		{
			die "Option $c not set in config file $vipard_file ... exiting\n";
		}
	}
}

#check at least one STATS options is set
if ( !defined($config->get("stats_r")) &&  !defined($config->get("stats_stata")) && !defined($config->get("stats_sas")) && !defined($config->get("stats_matlab")) )
{
	die "At least one Stats Option must be set in config file $vipard_file ... exiting\n";
}
else
{  #check the binaries exist
	if (defined($config->get("stats_r"))) 
	{
		unless (-e $config->get("stats_r"))
		{
			die "Unable to locate R binary at ".$config->get("stats_r")."\n";
		}
	}
	
	 if (defined($config->get("stats_stata")))
        {
                unless (-e $config->get("stats_stata")) 
                {
                        die "Unable to locate Stata binary at ".$config->get("stats_stata")."\n";
                }
        }

	if (defined($config->get("stats_sas"))) 
        {
                unless (-e $config->get("stats_sas")) 
                {
                        die "Unable to locate SAS binary at ".$config->get("stats_sas")."\n";
                }
        }
	if (defined($config->get("stats_matlab"))) 
        {
                unless (-e $config->get("stats_matlab")) 
                {
                        die "Unable to locate MATLAB binary at ".$config->get("stats_matlab")."\n";
                }
        }
}

#Explicit check for poor config
if ($config->get("server_polling") <1)  #ie check every second)
{
	die "Please check server polling interval is a valid number of seconds ... exiting\n";
}

#check if output projects filepath is writeable!
open(FILE,">$filepath/.dummy") || die "Unable to write to FILEPATH - $filepath - set by VIPAR_ROOT in Apache ENV config - please check ownership permissions before starting VIPAR";
close(FILE);
unlink("$filepath/.dummy");

#Load the config into the VIPAR database
#note assumes that this structure already exists
my $dsn = "dbi:mysql:".$dbconfig->get("database_name");
my $dbuser = $dbconfig->get("database_adminuser");
my $dbpass = $dbconfig->get("database_adminpass");
my %attr = (
	RaiseError => 0,
	AutoCommit => 0,
	PrintError => 0
	);

# connect to the database
my $dbh = DBI->connect($dsn, $dbuser, $dbpass, \%attr) || die "\nCould not connect to the MySQL VIPAR database in config file - please check the database name and whether MySQL daemon is running: $DBI::errstr";

my $stmt = "select study,resource,server.port from server,resources where server.sv_auto=resources.server and resources.delstat=0";
my $query = $dbh->prepare($stmt);
$query->execute() or die "Error retrieving resources details from mysql database: $DBI::errstr";

my %sites=();
while (my @data = $query->fetchrow_array())
{
	# site resource = port
	$sites{$data[0]}{$data[1]} = $data[2];

}
$query->finish();

# check if any sites are available, if not, don't start daemon
# This will always happen on a fresh install
#--CHECK THAT THIS IS DISABLED IN NEWEST VERSION
if (scalar(keys %sites) <1)
{
	#$dbh->disconnect();	
	print "Warning: No resources (or servers) are configured in the database - please configure these in the portal, then restart VIPAR daemon\n";
}
#--CHECK THAT THIS IS DISABLED IN NEWEST VERSION


#delete existing
$stmt = "delete from vipar_config";
$query = $dbh->prepare($stmt);
$query->execute() or die "Error removing data from table vipar_config: $DBI::errstr";
$dbh->commit;

#generate random exec_key - used as check point incase a local attack/process tries to send data to socket server
my $exec_key = generate_random_string(20);

$stmt = "insert into vipar_config (v_section,v_key,v_value) values ('server','execkey','$exec_key')";
$query = $dbh->prepare($stmt);
$query->execute() or die "Error inserting data into table vipar_config: $DBI::errstr";
$dbh->commit;

# Set all vipard options in database - with empty for optional
if (!defined($config->get("server_smtpuser")))
{
	$config->set("server_smtpuser","");
}
if (!defined($config->get("server_smtppass")))
{
        $config->set("server_smtppass","");
}

%conf = $config->varlist("server_*");
foreach my $c (keys %conf)
{
	
	$stmt = "insert into vipar_config (v_section,v_key,v_value) values ('server','$c','".$config->get($c)."')";
	$query = $dbh->prepare($stmt);
	$query->execute() or die "Error inserting data into table vipar_config: $DBI::errstr";
	$dbh->commit;
}

# Set all vipard options in database
%conf = $config->varlist("file_*");
foreach my $c (keys %conf)
{
        $stmt = "insert into vipar_config (v_section,v_key,v_value) values ('file','$c','".$config->get($c)."')";
        $query = $dbh->prepare($stmt);
        $query->execute() or die "Error inserting data into table vipar_config: $DBI::errstr";
        $dbh->commit;
}

# Set all stats vipard options in database
%conf = $config->varlist("stats_*");
foreach my $c (keys %conf)
{
	if (defined($config->get($c)) && $config->get($c) ne "") # insert stats if not empty
	{ 
        	$stmt = "insert into vipar_config (v_section,v_key,v_value) values ('stats','$c','".$config->get($c)."')";
	        $query = $dbh->prepare($stmt);
        	$query->execute() or die "Error inserting data into table vipar_config: $DBI::errstr";
	        $dbh->commit;
	}
}

$dbh->disconnect();

##########
#
# START DAEMON
#
##########

#fork and daemon
my $pid = fork ();
if ($pid < 0)
{
	#fork failure
	die "fork: $!";  
}
elsif ($pid)
{
	#in child, exiting
	exit 0;
}

my $continue = 1;

# start logging
#my $log = new Log::Dispatch(callbacks => sub { my %h=@_; return Date::Format::time2str('%B %e %T', time)." [$$]: ".$h{message}."\n"; });
my $log = new Log::Dispatch();
my $loglevel = "error";
#get loglevel from config 
if ($config->get("file_loglevel") eq "WARNING" || $config->get("file_loglevel") eq "warning")
{
	$loglevel = "warning";
}
elsif ($config->get("file_loglevel") eq "DEBUG" || $config->get("file_loglevel") eq "debug")
{
	$loglevel = "debug";
}

#$log->add( Log::Dispatch::FileShared->new( name => 'file1', min_level => $loglevel, mode => '>>', filename  => $config->get("file_logfile"), callbacks => sub { my %h=@_; return Date::Format::time2str('%B %e %T', time)." [$$]: ".$h{message}."\n"; } ));

#logrotation - every week
$log->add( Log::Dispatch::FileRotate->new( name => 'file1',filename  => $config->get("file_logfile"),min_level => $loglevel,mode => '>>',DatePattern => '0:0:1:0:0:0:0',max=>52,callbacks => sub { my %h=@_; return Date::Format::time2str('%B %e %T', time)." ".$h{message}."\n"; } ));

$log->error("Starting VIPAR daemon:  ".localtime());

$log->error("Loglevel = $loglevel");

#signal captures
$SIG{HUP}  = sub { $log->warning("Stopping VIPAR daemon:  ".localtime()."\n"); $continue = 0; };
$SIG{INT}  = sub { $log->warning("VIPAR daemon Caught SIGINT:  exiting gracefully"); $continue = 0; };
$SIG{QUIT} = sub { $log->warning("VIPAR daemon Caught SIGQUIT:  exiting gracefully"); $continue = 0; };
$SIG{TERM} = sub { $log->warning("VIPAR daemon Caught SIGTERM:  exiting gracefully"); $continue = 0; };
$SIG{CHLD} = 'IGNORE'; #prevents defunct finished exec processes
##Note you can't capture KILL signal

#write PID lock
open(OUT,">$dpid") or die "Unable to create lock file .... exiting\n";
print OUT "".getpid();
close(OUT);

# creating object interface of IO::Socket::INET modules which internally does
# socket creation, binding and listening at the specified port address.
# flush after every write
$| = 1;
my ($socket,$client_socket);
my ($peeraddress,$peerport);

#non-blocking tcp port binding
$socket = new IO::Socket::INET (
	LocalHost => "127.0.0.1",
	LocalPort => $config->get("server_execport"),
	Proto => 'tcp',
	Listen => 10,
	Blocking => 0,  
	Reuse => 1
) or die "ERROR in binding to socket  : $!\n";

#main daemon
my $starttime = time(); #in epoch seconds
my $polling = $config->get("server_polling");
my $pollmode = $config->get("server_pollmode");

my %procpool = ();
while ($continue) {
	#so we don't overload the system
	#select(undef, undef, undef, 0.1);  # sleep 1/5th second
	sleep(1);

	#processpool - not really required to print, but useful for debugging
	#if ((time()-$starttime) % 5 == 0)
	#{
	#	my @pp = keys %procpool;
	#	$log->warning("PP = ".($#pp+1));
	#}

	#poll for site updates
	if ((time()-$starttime) % $polling == 0)
	{
		if (scalar(keys %sites) >=1) # found at least 1 site to check
		{
			#$log->warning("Polling ".time()."  $starttime\n");
			$log->warning("Checking ".scalar(keys %sites)." sites configured in VIPAR database");
			# for each study
			foreach my $s (keys %sites)
			{
				# for each resource
				foreach my $r (keys %{$sites{$s}})
				{
					if ($pollmode == 0) # poll in serial
					{
						my $t = threads->create(\&check_site_status,$r,$sites{$s}{$r},$s); 
						$t->join(); #wait for thread to finish
					}
					else #poll in parallel
					{
						threads->create(\&check_site_status,$r,$sites{$s}{$r},$s)->detach; 
					}
				}
			}	
		} # site check
	}

	#non-blocking client accept
	if (my $c = $socket->accept)
	{
		# RF - just wondering if a thread can be used here instead of a fork to run process_client_requests
		my $pid = fork();
		die "Cannot fork: $!" unless defined($pid);
		if ($pid == 0) # in child
		{
			process_client_requests($c);
			exit(0);
		}
		else  #parent
		{
			$log->debug("Parent ".$$." has started child $pid");
		}		
	}
}

##########
#
# SHUTDOWN
#
##########

# connect to the database
$dbh = DBI->connect($dsn, $dbuser, $dbpass, \%attr) || die "Could not connect to VIPAR database in config file: $DBI::errstr";

#delete config to ensure site knows daemon not running
$stmt = "delete from vipar_config";
$query = $dbh->prepare($stmt);
$query->execute() or die "Error removing site data from table vipar_config: $DBI::errstr";
$dbh->commit;
$dbh->disconnect();

#exiting daemon
#$log->warning("Exiting gracefully");
##########
#
# PROCESS CLIENT REQUESTS
#
##########

sub process_client_requests
{
#	local $SIG{CHLD} = ''; #ree
	my $c = shift;
	my $clientpid = $$;
	my $peeraddress = $c->peerhost();
	my $peerport = $c->peerport();
	$log->debug("Process ".$$." accepted New Client Connection From : $peeraddress, $peerport");

	my $cont=1;

	#receive exec key from client
	my $resp = <$c>;
	chomp($resp);
	if ($resp eq $exec_key)
	{
		#read command from client - log or exec
		my $command = <$c>;
		chomp($command);

		if ($command eq "stopexec")    ## STOPEXEC (running job) REQUESTED
		{
			$log->debug("Client validated From : $peeraddress, $peerport with STOPEXEC request");
			#print "Client validated From : $peeraddress, $peerport with STOPEXEC request\n";
			my @data;
			while(my $l = <$c>)
			{	
				chomp($l);			
				push @data,$l;
			}
					
			my $uid = $data[0];
			my $rtime = $data[1];
			
			# connect to the database
			my $dbh = DBI->connect($dsn, $dbuser, $dbpass, \%attr);
			if (!$dbh)
			{
				$log->error("Could not connect to VIPAR database in config file: $DBI::errstr - aborting STOPEXEC request");
			}
			else #connected
			{
				my $stmt = "select run_status from run_time where rt_auto=$rtime";
				$dbh->do("lock tables run_time write");

				my $query = $dbh->prepare($stmt);
				$query->execute();
				my ($killpid) = $query->fetchrow_array();
				$query->finish();
				if ($killpid eq "" || $killpid == 0) #error'd somewhere
				{
					$log->warning("Cannot complete STOPEXEC for user $uid for runtime rt_auto=$rtime (job not found or may have finished)");
					$dbh->do("update run_time set run_status=-1 where rt_auto=$rtime");
				}
				else
				{
					#check if the process exists first
					my $exists = kill 0, $killpid;
					if ($exists)
					{
						#send kill SIGKILL to exec pid
						system("\\kill -9 $killpid");
						$log->warning("Successfully completed STOPEXEC for user $uid ");
						$dbh->do("update run_time set run_status=-1 where rt_auto=$rtime");
					}
					else
					{
						$log->warning("Cannot complete STOPEXEC for user $uid for runtime rt_auto=$rtime (job not found or may have finished)");
						$dbh->do("update run_time set run_status=-1 where rt_auto=$rtime");
					}
				
				}
				$dbh->do("unlock tables");
				$dbh->commit;
				$dbh->disconnect();
			}
		}
		elsif ($command eq "log")    ## LOG REQUESTED
		{
			$log->debug("Client validated From : $peeraddress, $peerport with LOG request");
			#print "Client validated From : $peeraddress, $peerport with LOG request\n";
			my @data;
			while(my $l = <$c>)
			{	
				chomp($l);			
				push @data,$l;
			}
					
			my $level = $data[0]; #receive level 
		
			my $logdata = $data[1];  #receive message
			
			if ($level eq "error")
			{
				$log->error($logdata);
			}
			elsif ($level eq "warning")
			{
				$log->warning("$logdata");
			}
		}
		elsif ($command eq "exec")  # EXEC requested
		{
			$log->debug("Client validated From : $peeraddress, $peerport with EXEC request");

			#now receive data from client (R script, SQL code etc)			
			my @data;
			while(my $l = <$c>)
			{	
				chomp($l);			
				push @data,$l;
			}

			my $emailstring="";
	
			my $uid = $data[0];
			my $project = $data[1];
			my $aname = $data[2];
			# removal of dodgy characters in aname and desc is done in vipar_analyse.cgi
			#$aname=~s/[][&;`'\\"|*?~<>^(){}\$\n\r#@]\///g if $aname ne ""; # remove potential problem characters
			#$aname=~s/ /_/g if $aname ne "";

			my $desc = $data[3];
                        #$desc=~s/[][&;`'\\"|*?~<>^(){}\$\n\r#@]\///g if $desc ne ""; # remove potential problem characters

			#update glob with aname (in case we need to kill it later)
			$execpool->{$clientpid} = $aname;

			# Read in the databases to use 
			my @resources = split(',',$data[4]);

			# Read in the variable names of the data
			# vipar_analyse.cgi has put this in the form e.g DEMOG.SEX
			# need to make sure that the right variables are retrieved from the right tables
			my @variables = split(',',$data[5]);

			# Read in the user's stats package preference
			my $stats = $data[6];

			# where clause data
			# first split by :::: then by ::: then replace \t with \n
			$log->debug("where clause  data: $data[7]");
			my %where = ();
			my $wherestr = "Where clause:\n";
			foreach ( split(/----/,$data[7]) ){
			 if (m/(.+):::(.+)/){
			  my $t = $1;
			  my $w = $2;
			  $where{$t} = $w;
			  $wherestr .= "$t: $w\n";
			  }
			 }

			# Read in the user's syntax
			my $syntax = "";
			for (my $i=8; $i<=$#data; $i++)
			{
				$syntax = $syntax.$data[$i]."\n";
			}
			$syntax =~ s/\r//g; #strip windows \r

			# Store run related data for the email and log files
			my $runlog = "";
			my $string = "";

			# connect to the database
			my $dbh = DBI->connect($dsn, $dbuser, $dbpass, \%attr);
			if (!$dbh)
			{
				$log->error("Could not connect to VIPAR database in config file: $DBI::errstr - aborting EXEC request");
			}
			else 
			{

				# Get the timezone and email address for this user
				my ($uname,$tz,$email) = $dbh->selectrow_array("select username,time_zone,email from users where u_auto = $uid");

				my ($pname,$sname,$sid) = $dbh->selectrow_array("select p.project,s.study,p.study from projects as p, study as s where p.study = s.st_auto and p_auto = $project");

				# Get the current time in the relevant timezone
				my $dt = DateTime->now();
				$dt->set_time_zone( $tz );

				# Get the current date based on the current timezone
				my @currdate = ($dt->day(),$dt->month_abbr(),$dt->year());
				my @currtime = ($dt->hour(),sprintf("%02d",$dt->minute()),sprintf("%02d",$dt->second()));

				####if aname is blank, switch to current date/time
				if ($aname eq "")
				{
					$aname = "".join(" ",@currdate)." ".join(":",@currtime);
				}

				$emailstring.="<BR>Analysis name: <b>$aname</b>";
				$emailstring.="<BR>Description: <b>$desc</b>" if $desc ne "";
				$emailstring.="<BR>Resources: <b>$data[4]</b>";
				$emailstring.="<BR>Variables :<b>$data[5]</b>";
				$emailstring.="<BR>$wherestr";
				$emailstring.="<BR>Stats package: <b>".uc($data[6])."</b>";

				$string = "\nAnalysis initiated by $uname on " . join(" ",@currdate) . " " . join(":",@currtime) . " ($tz)";
				$log->warning($string);

				# Configure the working directory

				# Make the basename for the project directory
				my $project_dir = "$filepath/project_$project";
				mkdir("$project_dir") if ! -e $project_dir;

				# Make a folder for the current date
				my $date = join("_",@currdate);
				my $rundir = "$project_dir/$date";
				mkdir("$rundir") if ! -e $rundir;
		
				# Now make a folder for this analysis based on the current time
				my $time = join("_",@currtime);
				$time .= "_$aname" if $aname ne "";
				my $workingdir = "$rundir/$time";
				if (-e $workingdir) #hit 2 jobs running at the same time, potentially within the same project
				{
					$workingdir = "$rundir/$time".$dt->microsecond();

					if (-e $workingdir)  # still the same time
					{
						$workingdir = "$rundir/$time"."_".int(rand(100)); #add a random number to the job
					}
				}
				mkdir("$workingdir");
		
				#this is required within the fork, otherwise all fifo's get the same random tag
				srand(); 
				my $tag = generate_random_string(10);

#++ $fpath made elsewhere but needs to include $tag
				my $batchcode = "$workingdir/user_syntax.txt";
				my $batchcodem = "$workingdir/user_syntax.m";
				my $errorfile = "$workingdir/errors.txt";
				my $runfile = "$workingdir/runfile.txt";

				open(STATUS, ">$workingdir/state.txt");
				print STATUS "R\n";
				close(STATUS);

				$runlog .= "$string\n\nProject:   $pname\nResources: " . join(",",@resources) . "\nVariables:    " . join(",",@variables) . "\n\n";

				# Log the run so that it appears in the file manager
				# see if current date exists in the run_date table

				#lock table while we do this step
				$dbh->do("lock tables run_date write, run_time write");

				my ($dateid) = $dbh->selectrow_array("select rd_auto from run_date where run_date = \'$date\'");
				if (!defined($dateid) || $dateid eq "" || $dateid==-1 ) # new date
				{
					$dbh->do("insert into run_date (run_date) VALUES (\'$date\')") or $log->debug("$DBI::errstr");
					$dbh->commit;
#++ why isn't this $dbh->last_insert_id( undef, undef, undef, undef );
					($dateid) = $dbh->selectrow_array("select rd_auto from run_date where run_date = \'$date\'");
				}

				# log the run, setting run_status to the client exec process PID
				#++ need to sanitise some of this input to avoid malicious code
				$dbh->do("insert into run_time (project,run_date,user,run_time,exclude,run_status,description) VALUES ($project,$dateid,$uid,\'$time\',0,$clientpid,\"$desc\")");
				$dbh->commit;
			
				$dbh->do("unlock tables");

#++ why isn't this $dbh->last_insert_id( undef, undef, undef, undef );
#++ should move unlock tables statement below this
#++ should also put the specified table in the last_insert_id, although I think this might not have an affect in MySQL
				my $timeid = $dbh->selectrow_array("select rt_auto from run_time where project=$project and run_date=$dateid and user=$uid and run_time=\"$time\"");

				$log->warning("$uname has initiated analysis run $time (run_time job $timeid)");

				my $s_tab = &relquery(\@resources,\@variables,$sid,\%where,$dbh);

				#setup handlers from here in case someone wants to kill a 'hanged' job
				##Note: SIGKILL cannot nomally be trapped by perl
				$SIG{HUP}  = &gracefulexit($workingdir,$clientpid,$project,$dateid,$uid,$time,$s_tab,$tag);
				$SIG{INT}  = &gracefulexit($workingdir,$clientpid,$project,$dateid,$uid,$time,$s_tab,$tag);
				$SIG{QUIT} = &gracefulexit($workingdir,$clientpid,$project,$dateid,$uid,$time,$s_tab,$tag);
				$SIG{TERM} = &gracefulexit($workingdir,$clientpid,$project,$dateid,$uid,$time,$s_tab,$tag);

#my $dumpdata = Dumper($s_tab);
#$log->error("$dumpdata");

				#put run syntax into DB
				my $quoted_syntax = $dbh->quote($syntax);
			
				#print "insert into run_syntax (run_time,syntax) VALUES ($timeid,$quoted_syntax)\n";
				$dbh->do("insert into run_syntax (run_time,syntax) VALUES ($timeid,$quoted_syntax)");
				$dbh->commit;

				#prepare the query string for data retrieval
#++ not needed as creted as part of the relcode
				#my $querystmt = "select sql_no_cache " . join(",",@variables) . " from ";	

				#need to get server resources for each database
				my %svs = ();
				foreach my $r (@resources)
				{
#++ not sure why this is "LIKE $r"
# should be = 
# changed
					#my $sv = $dbh->selectrow_array("select port from server,resources where server.sv_auto=resources.server and resources.resource like '".$r."'");
					$svs{$r} = $dbh->selectrow_array("select port from server,resources where server.sv_auto=resources.server and resources.resource = '$r'");
				}
		
# RELCODE_START
				# For the non-relational data @resources doubles as the names of the country AND the table names to pull data from
				# For the relational data the @resources only gives the names of the country the keys in $relstmts contains the table names
				# s_tab contains tableidx => variables
				#                         => resources to query and statement to use for each resource (nonrel table name varies cf rel where table name is the same therefore need custom query for each resource)
				#my $mysql_add = "";
				#my $s_tab = $studyname eq "minerva" ? &relquery(\@resources,\@variables) : &nonrelquery(\@resources,\@variables,$mysql_add);

				#finished with the database
				#$dbh->disconnect();

				# Time the whole process
				my $sw = Misc::Stopwatch->new()->start();

				#print "$peeraddress,$peerport Retrieving data\n";
				# Depending on POLL mode, connect to each database or site in order / or in parallel threads

				my $err = "";
				#my $dsnexec = "dbi:mysql:$sname:127.0.0.1:";
				my $dsnexec = "dbi:mysql:";
				my $dbuserexec = $dbconfig->get("database_remotequeryuser");
				my $dbpassexec = $dbconfig->get("database_remotequerypass");
				my %threads = ();

				# write an initial summary of the analysis	
				open(VIPOUT,">$workingdir/vipar_log.txt");
				print VIPOUT "Analysis name: $aname\n";
				print VIPOUT "Description: $desc\n";
				print VIPOUT "Resources: $data[4]\n";
				print VIPOUT "Variables: $data[5]\n";
				print VIPOUT "$wherestr\n";
				print VIPOUT "STATS:".uc($data[6])."\n";
				close(VIPOUT);

				if ($pollmode == 0) # poll in serial
				{

# makefifo gets all the data for a particular table from each resource and makes a fifo
# in a relational context there are multiple tables but in a non-relational context this only relates to a single process
# I guess pollmode here is only useful in a relational context

					$log->warning("Retrieving data in serial");			
					foreach my $t (keys %{$s_tab})
					{
						$threads{$t} = threads->create("makefifo",\%{$s_tab->{$t}},$dbuserexec,$dbpassexec,$dsnexec,\%svs,$workingdir,$tag,$clientpid,$project,$dateid,$uid,$time,$data[6]);
						# maybe could add a thread->join here
					}

				}
				else #poll in parallel
				{
#++ gets data for a particular table for all sites and makes a fifo

					$log->warning("Retrieving data in parallel");
					foreach my $t (keys %{$s_tab})
					{
						$threads{$t} = threads->create("makefifo",\%{$s_tab->{$t}},$dbuserexec,$dbpassexec,$dsnexec,\%svs,$workingdir,$tag,$clientpid,$project,$dateid,$uid,$time,$data[6]);
					}


				}

#++ checks the status of running threads and recieves any errors
				# as the data can take time to be available
				# need to wait for the FIFOs to be made
				# this also means that the data has been retrieved as this is created before the FIFO is
				# need a way here to check that the thread responsible for a particular FIFO hasn't died
				open(VIPOUT,">>$workingdir/vipar_log.txt");
				foreach my $t (keys %{$s_tab}){
				 my $thr = $threads{$t};
				 my $tname = $s_tab->{$t}->{'name'};
				 my $tfpath = "$workingdir/fifo_$tag\_$tname.txt";
				 my $wait = 0;
				 while ($wait == 0){
				  # if the thread has finished then something went wrong so check errval and add to $err
				  if ($thr->is_joinable()){
				   $thr->join();
				   my $errval = $thr->error();
				   $err .= $errval ? "thread handling $tname failed: $errval\n" : "thread handling $tname failed without error message\n";
				   print VIPOUT "$tname data retrieval failed from all sites see runlog.txt\n";
				   unlink($tfpath);
				   $wait++;
				   }
				  # if the thread is still running then check to see if it has made the FIFO yet
				  # if it has then increment wait
				  elsif ($thr->is_running()){
				   if (-p $tfpath){
				    print VIPOUT "$tname data retrieved from all sites\n";
				    $wait++;
				    }
				   }
				  }
				 }
				close(VIPOUT);

				# this is the total time for all data being retrieved or the creation of the fifos
		 		$sw->stop();
				$log->warning("Elapsed time for data retrieval = ".$sw->elapsed());

				$emailstring.="<BR><BR>Time to retrieve data: <b>".sprintf("%.1f",$sw->elapsed())." secs</b>";

				if ($err ne "") {
				 $log->error("Unable to retrieve data from all sites ($err) - cancelling further");

#++ errors reported in retrieval so tidy up

				 # Tidy up running threads
				 # tidy up successfully made FIFOs
				 foreach my $t (keys %{$s_tab}){
				  my $tname = $s_tab->{$t}->{'name'};
				  my $tfpath = "$workingdir/fifo_$tag\_$tname.txt";
				  unlink($tfpath);
				  my $thr = $threads{$t};
				  $thr->kill('KILL')->detach() if ($thr->is_joinable()); # can't detach a joined thread which will be the one that failed!
				  }

				 $log->error("Running threads killed and detached");

				 # update the database
				 $dbh->do("update run_time set run_status=-1 where rt_auto=$timeid");
				 $dbh->commit;

				 # make a log file for this run
				 open(LOG,">$workingdir/runlog.txt") || die "Can't open log file: $!\n\n";
				 print LOG "Analysis failed to complete: $err\n";
				 close(LOG);

				 open(STATUS, ">$workingdir/state.txt");
				 print STATUS "E\n";
				 close(STATUS);

				 my $emsg = MIME::Lite->new(
					To      => $email,
					Subject =>"VIPAR: Analysis completed",
					From    =>'portal@viparproject.org',
					Type    =>'multipart/related'
					); MIME::Lite->new();

				 $emsg->attach(
					Type => 'text/html',
					Data => qq{
				 	<body>
					<p>Dear $uname<br><BR>
					This is a notification that your analysis task <b>$aname</b> unfortunately did not complete successfully.<BR>$emailstring<br><br>Please login to the VIPAR portal for more details.</p></body>},
					);

				 if ($config->get("server_smtphost") eq "none"){ #no mail server set
				  #no email is sent, as no server is defined)
				  $log->debug("Analysis finished, but no email server defined to notify user");
				  }
				 else {	#smtp server is defined, so try sending to it
				  if ($config->get("server_smtpuser") ne "" && $config->get("server_smtppass") ne ""){
				   $emsg->send('smtp',$config->get("server_smtphost"),Port=>$config->get("server_smtpport"),Timeout=>60,AuthUser=>$config->get("server_smtpuser"),AuthPass=>$config->get("server_smtppass"));
				   }
				  else {
				   $emsg->send('smtp',$config->get("server_smtphost"),Port=>$config->get("server_smtpport"),Timeout=>60);
				   }
				  }
				 } # end dealing with errors

				else { # no errors retrieving data or making fifo, continue to executing stats
				 $log->warning("Client $clientpid (port $peerport) executing stats program");

=cut
#++ This is not relevant in a relational context
# However the total for each site and grand total plus times are contained in the return value of makefifo
# Need to find a way to get these back
=cut

				 open(VIPOUT,">>$workingdir/vipar_log.txt");
				 print VIPOUT "Time to retrieve data: ".sprintf("%.1f",$sw->elapsed())."\n";
				 print VIPOUT "\nExecuting stats program\n";
# irrelevant in a relational context	print VIPOUT "Total records retrieved: $gktest\n";
				 close(VIPOUT);

				 # make syntax file for whatever stats package is required
				 my $runsyntax = "";
				 my $statasyntax = "";
				 if ($stats eq "r") {
				  $runsyntax = &syntax_R($syntax,$workingdir,$tag,$s_tab);
				  }
	#*# these subs for stata and sas need to be implemented 
				 elsif ($stats eq "sas") {
				  #$runsyntax = &syntax_sas($syntax,$fpath,$workingdir,@variables);
				  $runsyntax = &syntax_sas($syntax,$workingdir,$tag,$s_tab);
				  }
				 elsif ($stats eq "stata") {
		 		  #$runsyntax = &syntax_stata11($syntax,$fpath,$workingdir,@variables);
		 		  ($runsyntax,$statasyntax) = &syntax_stata($syntax,$workingdir,$tag,$s_tab,$config->get("stats_stata"));
				  }
				 elsif ($stats eq "spss"){} # not implemented
				 elsif ($stats eq "matlab") {
				  $runsyntax = &syntax_MATLAB($syntax,$workingdir,$tag,$s_tab);
				  }
				 else {
				  $log->error("No such stats package - $stats - please check configuration file");
				  }

				 # Output syntax to file
				 open(OUT,">$batchcode");
				 print OUT $runsyntax;
				 close(OUT);

#++ here exec_stats takes in the fpath but in a relational context there are multiple paths so not relevant here
#			 	 my $temp = threads->create(\&exec_stats,$fpath,$stats,$project,$workingdir,$project_dir,$errorfile,$batchcode,$batchcodem,$tag);
#				 my $temp = threads->create(\&exec_stats,$stats,$project,$workingdir,$project_dir,$errorfile,$batchcode,$batchcodem,$tag);
#				 $temp->detach();
# Currently not going to execute as a thread. Want to test this first
# BUT it will eventually have to be in a thread or a fork because there's no way to control the killing of the system command if the user chooses to stop the job. This could leave big RAM jobs running.

				 $ENV{'RLIBS'} = "$project_dir/codelibs/rlibs/";
				 $ENV{'SASLIBS'} = "$project_dir/codelibs/saslibs/";
				 $ENV{'STATALIBS'} = "$project_dir/codelibs/statalibs/";
				 $ENV{'MATLABLIBS'} = "$project_dir/codelibs/matlablibs/";

                        	 if ($stats eq "r") {
				  # Changed on 02/03/17 to allow R commands to be output in the log file for debugging
                                  #system($config->get("stats_r")." CMD BATCH --no-save --vanilla --slave $batchcode $workingdir/R.log.txt");
                                  system($config->get("stats_r")." CMD BATCH --no-save --vanilla $batchcode $workingdir/R.log.txt");
                        	  }
                        	 elsif ($stats eq "spss"){}
				 
                        	 elsif ($stats eq "stata"){

				  my $rstatafifo = "$workingdir/fifo_r2stata.txt";
				  # delete the fifo if it exists
				  unlink("$rstatafifo");

				  # make the do file
				  my $statacode = "$workingdir/r2stata.do";
				  open(OUT,">$statacode");
				  print OUT $statasyntax;
				  close(OUT);
				  # make a thread to run stata
				  my $statathr = threads->create("stata_runstata",$s_tab,$dbuserexec,$dbpassexec,$dsnexec,\%svs,$workingdir,$tag,$clientpid,$project,$dateid,$uid,$time,$data[6],$statacode);
				  # now run R
				  # Changed on 02/03/17 to allow R commands to be output in the log file for debugging
				  #system($config->get("stats_r")." CMD BATCH --no-save --vanilla --slave $batchcode $workingdir/R.log.txt");
				  system($config->get("stats_r")." CMD BATCH --no-save --vanilla $batchcode $workingdir/R.log.txt");
				  # at this point 2 things could have happened
				  # 1. the R code made the minerva df and the fifo and the thread ran stata beautifully
				  # 2. the R code did not make the df or the fifo and the thread is still waiting and needs to be killed
				  # test to see if the fifo was made
				  if (! -p $rstatafifo){
				   $log->error("R failed to make fifo in $clientpid. Killing stata thread");
				   $statathr->kill('SIGHUP')->detach();
				   }
				  else {
				  # print "waiting for stata thr to exit\n";
				   $statathr->join();
				   }
				  # print "ok it is finished now\n";

				  unlink($rstatafifo);
                        	  }
	                         elsif ($stats eq "sas"){
                                  system($config->get("stats_sas")." $batchcode -log $workingdir/SAS.log.txt -print $workingdir/output.txt -sasuser /data/saswork/sastmp/sas$$");
                        	  }
				 elsif ($stats eq "matlab") {
				  copy($batchcode, $batchcodem) or die "Copy to m file failed: $!";
				  
                                  system(join("","echo vipar_proc | sudo -S ",$config->get("stats_matlab")," -nodisplay -nosplash -nodesktop -noFigureWindows -logfile \"$workingdir/MATLAB.log.txt\" -r \"run \"$batchcodem\"; exit; quit\"")); # -nojvm 
                        	  }

				 $log->warning("Process ".$$." finished stats\n");

				 # Now zip the results files
				 my $zipfile = "VIPAR_$pname\_$date\_$time";
				 # explicitly remove fifos before zipping
				 # Tidy up running threads
				 foreach my $t (keys %{$s_tab}){
				  my $tname = $s_tab->{$t}->{'name'};
				  my $tfpath = "$workingdir/fifo_$tag\_$tname.txt";
				  unlink($tfpath);
				  my $thr = $threads{$t};
				  $runlog .= $thr->join();
				  }
				 system("zip -rqj $workingdir/$zipfile $workingdir/*");

				 open(STATUS, ">$workingdir/state.txt");
				 print STATUS "C\n";
				 close(STATUS);

				 # make a log file for this run
				 open(LOG,">$workingdir/runlog.txt") || die "Can't open log file: $!\n\n";
				 print LOG $runlog;
				 close(LOG);

				 #*# need to add here a step to update the run_time table run_status field to 1
				 # have established a new connection as it is closed earlier on

				 # connect to the database
				 my $dbh = DBI->connect($dsn, $dbuser, $dbpass, \%attr);
				 if (!$dbh){
				  $log->error("Could not connect to VIPAR database in config file: $DBI::errstr - unable to finish EXEC job");
				  }
				 else {
#++ should be able to use "update run_time set run_status=0 where rt_auto=$timeid"
#++ should it be update to 0 or 1?
				  $dbh->do("update run_time set run_status=1 where project=$project and run_date=$dateid and user=$uid and run_time=\'$time\'");
				  $dbh->commit;
				  $dbh->disconnect();
				  }
				 my $emsg = MIME::Lite->new(
				  To      => $email,
				  Subject =>"VIPAR: Analysis completed",
				  From    =>'portal@viparproject.org',
				  Type    =>'multipart/related'
				  ); MIME::Lite->new();

				 $emsg->attach(
				  Type => 'text/html',
				  Data => qq{
				   <body>
				   <p>Dear $uname<br><BR>
				   This is a notification that the results of your analysis task <b>$aname</b> are now available at the VIPAR portal. <BR>$emailstring<br></p></body> },
				  );

				 if ($config->get("server_smtphost") eq "none") { #no mail server set
				  #no email is sent, as no server is defined)
				  $log->debug("Analysis finished, but no email server defined to notify user");
				  }
				 else {	#smtp server is defined, so try sending email to it
				  if ($config->get("server_smtpuser") ne "" && $config->get("server_smtppass") ne "") {
				   $emsg->send('smtp',$config->get("server_smtphost"),Port=>$config->get("server_smtpport"),Timeout=>60,AuthUser=>$config->get("server_smtpuser"),AuthPass=>$config->get("server_smtppass"));
				   }
				  else	{
				   $emsg->send('smtp',$config->get("server_smtphost"),Port=>$config->get("server_smtpport"),Timeout=>60);
				   }
				  }

				} # retrieval okay

			$log->debug("Finished client from $peeraddress, $peerport\n");

			} #end database connect okay

		} #end EXEC command
		else 
		{
			$log->error("Invalid command - $command - received from $peeraddress, $peerport\n");
		}	
	}  # end check KEY
	else
	{
		$log->error("Invalid key - $resp - received from $peeraddress, $peerport\n");
	}
}

sub exec_stats
{
	my $fpath = shift;
	my $stats = shift;
	my $project = shift;
	my $workingdir = shift;
	my $projectdir = shift;
	my $errorfile = shift;
	my $batchcode = shift;
	my $batchcodem = shift;
	my $tag = shift;

	my $thr = threads->self();
	my $tid = threads->tid();
	
	$ENV{'RLIBS'} = "$projectdir/codelibs/rlibs/";
	$ENV{'SASLIBS'} = "$projectdir/codelibs/saslibs/";
	$ENV{'STATALIBS'} = "$projectdir/codelibs/statalibs/";
	$ENV{'MATLABLIBS'} = "$projectdir/codelibs/matlablibs/";
	
	#give the main process time to create the thread
	sleep(2); 
		
	$log->warning("Process ".$$.":thread $tid($tag) executing $stats");
	my $wait=0;
	while ($wait==0)
	{
		if (-e $fpath && -p $fpath)
		{
			$wait++;
			# Make some syntax for R to call in batch mode using the file
			# Make a system call to R to run in batch using the syntax
			if ($stats eq "r")
			{
				#print "Running R\n";
				system($config->get("stats_r")." CMD BATCH --vanilla --slave $batchcode $workingdir/R.log.txt");
			}
			elsif ($stats eq "spss"){}
			elsif ($stats eq "stata")
			{
	    			$ENV{'PATH'} = $ENV{'PATH'}.":/usr/local/src/Stata11";
				$ENV{'STATATMP'} = "/data/saswork/statatmp";
				#print "Running STATA\n";
				system("stata-se < $batchcode > $workingdir/STATA.log.txt");
	    		}
	   		elsif ($stats eq "sas")
			{
	    			#print "Running SAS\n";
	    			system($config->get("stats_sas")." $batchcode -log $workingdir/SAS.log.txt -print $workingdir/output.txt -sasuser /data/saswork/sastmp/sas$$");
	    		}
			elsif ($stats eq "matlab") {
				  copy($batchcode, $batchcodem) or die "Copy to m file failed: $!";
                                  system($config->get("stats_matlab")." -nodisplay -nosplash -nodesktop -noFigureWindows -nojvm -logfile '$workingdir/MATLAB.log.txt' -r 'try; run(\"$batchcodem\"); catch; end; quit;'"); # could add 'quit' command after 'end;' w/o ; afterwards 
                        	  }
		}
		else
		{
			sleep(1); #wait for pipe creation
		}
	}
	$execthreadhash{threads->self->tid()} = 0; # update shared thread pool
	$log->warning("Process ".$$.":thread $tid($tag) finished stats\n");

	#finish this thread (important for detached parallel threads)
	threads->exit(0);	#THIS
}



sub check_site_status
{
	my $resource = shift;
	my $port = shift;
	my $sid = shift;

	my $thr = threads->self();
	my $tid = threads->tid();
	
	$log->warning("Process ".$$.":thread $tid checking resource via localhost:$port");

	#Load the config into the VIPAR database
	#note assumes that this structure already exists
	#my $dsn = "dbi:mysql:".$config->get("database_name");

	my $dt = DateTime->now();

        # Get the current date based on the current timezone
        my $datetime = $dt->day().$dt->month_abbr().$dt->year()."-".$dt->hour().":".sprintf("%02d",$dt->minute()).":".sprintf("%02d",$dt->second())."UTC";
	#print "Checking $resource $port at $datetime\n";

	#vipard local connection for updates
        my $ldsn = "dbi:mysql:".$dbconfig->get("database_name");
        my $ldbuser = $dbconfig->get("database_adminuser");
        my $ldbpass = $dbconfig->get("database_adminpass");
        my %lattr = (
                   RaiseError => 0,
                   AutoCommit => 1,
		   PrintError => 0
        );

    	# connect to the database
        my $ldbh = DBI->connect($ldsn, $ldbuser, $ldbpass, \%lattr);
	if (!$ldbh)
	{
		$log->error("Could not connect to local VIPAR database $DBI::errstr - aborting site check");
	}
	else
	{

		# here need to get the tables from the datadictionary for this resource
		my %tables = ();
		my $tstmt = "select dt.tid, dt.name, dd.dd_version, dd.dd_date from dtables as dt, datadictionaries as dd, resources as r where dt.dd_version = dd.dd_auto and r.datadictionary = dd.dd_auto and dt.delstat = 0 and dd.delstat = 0 and r.resource = \"$resource\"";
		my $query = $ldbh->prepare($tstmt);
		$query->execute();
		while (my @row = $query->fetchrow_array()){
			$tables{"$row[2] - $row[3]"}{$row[1]} = $row[0];
		}
		$query->finish();

		# need to get the ID of the resource to store
		my @resid = $ldbh->selectrow_array("select r_auto from resources where resource = \"$resource\"");

		#remote connection
		#my $remotedsn = "dbi:mysql:".$dbconfig->get("database_name").":127.0.0.1:$port";
		#my $remotedsn = "dbi:mysql:$sname:127.0.0.1:$port";
		my $remotedsn = "dbi:mysql:$resource:127.0.0.1:$port";
		my $dbuser = $dbconfig->get("database_remotequeryuser");
		my $dbpass = $dbconfig->get("database_remotequerypass");
		my %attr = (
			PrintError => 0,
			RaiseError => 0,
			AutoCommit => 0,
			
		);

		# connect to the database
		my $error = "Success connecting to remote VIPAR database resource $resource on port $port.";	
		my $remotedbh = DBI->connect($remotedsn, $dbuser, $dbpass, \%attr);
		if (!defined($remotedbh))
		{
			$error = "Could not connect to remote VIPAR database resource $resource on port $port. $remotedsn, $dbuser, $dbpass Error: ".$DBI::errstr;

			#set unavailable using local vipar dbh
			$ldbh->do("update server set available=-1 where port=$port");
			$ldbh->do("update server set Lastcheck=\"$datetime\" where port=$port");
		}
		else
		{
			# first show the server is available
		        $ldbh->do("update server set available=1 where port=$port");
		        $ldbh->do("update server set Lastcheck=\"$datetime\" where port=$port");

			# now get rid of all current entries for this resource
			$ldbh->do("delete from resources_tables where resid=$resid[0]");

			# now get a row count for each table
			# foreach data dictionary
			foreach my $dd (sort {$a cmp $b} keys %tables){
			# 	foreach tablename
			 	foreach my $t (sort {$a cmp $b} keys %{$tables{$dd}}){
					my $stmt = "select count(*) from $t";
					my $query = $remotedbh->prepare($stmt);
					$query->execute();
					my ($rcount) = $query->fetchrow_array();
					$query->finish();
			# 		do a row count and store in server_table as
			# 		sid=serverID, tid=tableID, repstring=string
					my $cstring = "$dd - $t - $rcount records";
					$ldbh->do("insert into resources_tables (resid,tid,cstring) VALUES ($resid[0],$tables{$dd}{$t},\"$cstring\")");  
				}
			}
		}

		$log->warning($error);
	
		$ldbh->disconnect() if defined($ldbh);
		$remotedbh->disconnect() if defined($remotedbh);
	}
	#finish this thread (important for detached parallel threads)
	threads->exit(0); # THIS	
}

sub generate_random_string
{
	my $length_of_randomstring=shift;# the length of 
			 # the random string to generate

	my @chars=('a'..'z','A'..'Z','0'..'9','_');
	my $random_string;
	foreach (1..$length_of_randomstring) 
	{
		# rand @chars will generate a random 
		# number between 0 and scalar @chars
		$random_string.=$chars[rand @chars];
	}
	return $random_string;
}


sub get_site_data  #from remote sites
{
	my $q = shift;
	my $res = shift;
	$q = $q." $res";
	my $port = shift;
	my $tag = shift;
	my $study = shift;

	my $thr = threads->self();
	my $tid = threads->tid();
	
	$log->warning("Process ".$$.":thread $tid retrieving data from $res");

	#my $dsn = "dbi:mysql:$study:127.0.0.1:$port";
	my $dsn = "dbi:mysql:$res:127.0.0.1:$port";
	my $dbuser = $dbconfig->get("database_remotequeryuser");
	my $dbpass = $dbconfig->get("database_remotequerypass");
	my %attr = (
		PrintError => 0,
		RaiseError => 0,
		AutoCommit => 0,
		mysql_read_timeout => 300,
		mysql_connect_timeout => 30
		);
	#note: connection attributes are need to set to zero to prevent thread dying	
	
	# connect to the database
	my $dbhand = DBI->connect($dsn, $dbuser, $dbpass, \%attr);
	if (!defined($dbhand))
	{
		$log->error("Unable to connect to remote site $res");	
		$pollthreadhash{threads->self->tid()} = -1; # returns error to main
	}		
	else
	{
		$log->warning("Running query $q");
		my $query = $dbhand->prepare($q);
		$query->execute();
		my $rcount=0;
		while( my @row = $query->fetchrow_array())
		{
#*#			my $r = "";
#			for(my $i=0; $i<=$#row; $i++)
#			{
#				if ($i == 0)
#				{
#					$r = $r.$row[$i];
#				}
#				else
#				{
#					$r = $r."\t".$row[$i];
#				}
#			}
			#push @Global,$r;			
#		 	$glob{$tag."_".$res."_$rcount"} = $r;
			$rcount++;
		 	$glob{$tag."_".$res."_$rcount"} = join("\t",@row);
		}		
		$dbhand->disconnect();
		$log->warning("Retrieved $rcount records from $res");
		$pollthreadhash{threads->self->tid()} = 0; # update shared thread pool
	}
	#random wait testing
	#sleep(int(rand(20)+10));
	#finish this thread (important for detached parallel threads)
	threads->exit(0);# THIS	
}		

sub syntax_R {
# makes the data object for R
my $user_syntax = shift;
my $workingdir = shift;
my $tag = shift;
my $tab = shift;

# need to get all the types for all selected variables to provide to fread
my %format = (
"Categorical" => "integer",
"Continuous" => "numeric",
"Date" => "character",
"String" => "character"
);

my $Rsyntax = "library(data.table)\nrequire(bit64)\n";
foreach my $t (keys %{$tab}){
 my $tname = $tab->{$t}->{'name'};
 my $tfpath = "$workingdir/fifo_$tag\_$tname.txt";
 #system("cat $tfpath > /tmp/$tname");
 #system2(\"cat $tfpath > /tmp/$tname\")
 my @colClasses = ();
 foreach my $v (sort {$a cmp $b} keys %{ $tab->{$t}->{'vars'} }){
  # add variable type to colClasses
  push @colClasses, $format{ $tab->{$t}->{'vars'}->{$v} };
  }
 my $colClasses_str = "\"" . join("\",\"",@colClasses) . "\"";

 $Rsyntax .= "
 $tname<-fread(\"cat $tfpath\", sep=\"\t\", header = TRUE, data.table = FALSE, showProgress = FALSE, colClasses=c($colClasses_str))
";
#$tname<-fread(\"cat $tfpath\", sep=\"\t\", header = T, data.table = FALSE, showProgress = FALSE)";
#thefifo<-fifo(description=\"$tfpath\")
#open(thefifo)
#$tname<-read.table(thefifo, sep=\"\t\",header=T)
#close(thefifo)";
#library(\"readr\")
#$tname<-read_tsv(thefifo, col_names=TRUE)
 }
$Rsyntax .= "      
setwd(\"$workingdir/\")
$user_syntax";

return($Rsyntax);
}


#call to syntax_MATLAB subroutine with following arguments: $runsyntax = &syntax_MATLAB($syntax,$workingdir,$tag,$s_tab);
#my $s_tab = &relquery(\@resources,\@variables,$sid,\%where,$dbh);
sub syntax_MATLAB {
# returns entire text to put into script file: generates MATLAB syntax to read in data object and prepends to user_syntax
my $user_syntax = shift;
my $workingdir = shift;
my $tag = shift;
my $tab = shift;
# text variable MATLABsyntax
my $MATLABsyntax = ""; # any comments to add to .m file 
foreach my $t (keys %{$tab}){
 my $tname = $tab->{$t}->{'name'};
 my $tfpath = "$workingdir/fifo_$tag\_$tname.txt";
 system("cat $tfpath > /tmp/$tname");

 $MATLABsyntax .= "
$tname = readtable(\'/tmp/$tname\');
if ~isempty($tname) 
	msg = ['Data successfully loaded in MATLAB table of size: ', ''];	
	disp(msg)
	size($tname)
end	
";
#thefifo<-fifo(description=\"$tfpath\")
#open(thefifo)
#$tname<-read.table(thefifo, sep=\"\t\",header=T)
#close(thefifo)";
#library(\"readr\")
#$tname<-read_tsv(thefifo, col_names=TRUE)
 }
$MATLABsyntax .= "      
cd $workingdir/
%-------------start of user syntax from web portal

$user_syntax

%-------------end of user syntax from web portal
exit";
return($MATLABsyntax);
}




sub syntax_stata {
# makes the data object for STATA
my $user_syntax = shift;
my $workingdir = shift;
my $tag = shift;
my $tab = shift;
my $stata_path = shift;
# first need to split the user syntax in to the R syntax and the Stata syntax
my ($r_syntax,$stata_syntax) = split("## END R SYNTAX ##",$user_syntax);
my $rfifo = "$workingdir/fifo_r2stata.txt";
my $statado = "$workingdir/r2stata.do";
my $statalog = "$workingdir/STATA.log.txt";
# initially set up the R syntax to perform the fork
my $runRsyntax = &syntax_R($r_syntax,$workingdir,$tag,$tab);

$runRsyntax .= "

# make sure there is a dataframe called minerva and that there is some data in it
if (exists(\"minerva\") && is.data.frame(get(\"minerva\")) && (nrow(minerva))) {
 print(paste(\"minerva has\", nrow(minerva), \"rows\"))
 # make a text file containing the header names from the minerva dataframe
 write.table(strsplit(unlist(names(minerva)), split=\" \"), file=\"$workingdir/names.txt\", sep = \" \", row.names=FALSE, col.names=FALSE)
 minerva <- lapply(minerva,function(x)gsub(\"^\$\", \".\",x))
 # make a w fifo with blocking enabled until the child reads
 thefifo<-fifo(description=\"$rfifo\", open = \"w\", blocking = TRUE, encoding = getOption(\"encoding\"))
 # write the data in minerva to it
 write.table(minerva, thefifo, sep=\"\t\", row.names=FALSE, quote=FALSE)
 close(thefifo)
 }
quit(save = \"no\", status = 0)
";

my $runstatasyntax = "
cd $workingdir
* get the column headers first
insheet using \"$workingdir/names.txt\", delim(\" \") clear
ds
infile str15(`r(varlist)') using $rfifo in 2/l, pipe clear
$stata_syntax
exit, clear";
#foreach my $t (keys %{$tab}){
 #my $headers = "site" . join(" ",sort {$a cmp $b} keys %{ $tab->{$t}->{'vars'} });
# my $headers = join(" ",sort {$a cmp $b} keys %{ $tab->{$t}->{'vars'} });
# my $tname = $tab->{$t}->{'name'};
# my $tfpath = "$workingdir/fifo_$tag\_$tname.txt";
# $statasyntax .= "
#infile $headers using $tfpath in 2/l, pipe";
# $statasyntax .= "
# $tab->{$t}->{'name'} = \"$workingdir/fifo_$tag\_$tname.txt\"";
# }
# here the user should have supplied syntax to read from the fifo
#$statasyntax .= "

return($runRsyntax,$runstatasyntax);
}

sub syntax_sas {
# makes the data object for SAS
my $user_syntax = shift;
my $workingdir = shift;
my $tag = shift;
my $tab = shift;
my %sasattrib = ();

# need to get all the types for all selected variables
# for string variables the input line needs to have a $ after the variable name
# for date variables the input line needs to have yymmdd10. after the variable name

my %format = (
"Categorical" => "",
"Continuous" => "",
"Date" => "YYMMDD10.",
"String" => "\$"
);

my $sassyntax = "
X 'cd $workingdir';
run;";

foreach my $t (keys %{$tab}){
 my $headers = join(" ",sort {$a cmp $b} keys %{ $tab->{$t}->{'vars'} });
 #my $input = join(" ",sort {$a cmp $b} keys %{ $tab->{$t}->{'vars'} }); # might need to add $ here if variables are characters like site
 # this needs to be better
 # we store the length of numerical data but this varies per variable (e.g. length(max(PID)) is huge compared with length(max(SEX)) which makes it hard to be dynamic
 # unless INFORMAT for each numeric variable is placed on its own line
 # this is similar for the length of character values which can differ per variable
 # dates are easy as they are always 10 in length
 # here we let SAS read in numeric values as it wishes without specifying a length
 # while we could use informat for character variables the syntax ($w.) requires a length (w) which changes per variable
 # date variables do use informat as this is fixed
 # @inarray will contain all variable names and any character variables will have $ after them
 my @inarray = ();
 my @indate = ();
 my @convmissing = ();
 foreach my $v (sort {$a cmp $b} keys %{ $tab->{$t}->{'vars'} }){
  # add variable to input statement
  push @inarray, $v;
  # add a $ if this is a string format variable
  push @inarray, $format{'String'} if $tab->{$t}->{'vars'}->{$v} eq "String";
  # collect all the date variables so that we can use informat
  push @indate, $v if $tab->{$t}->{'vars'}->{$v} eq "Date";
  # make sure that .M (pre-set by ViPAR for any missing values for SAS) is converted to ""
  push @convmissing, "if $v = '.M' then $v = '';" if $tab->{$t}->{'vars'}->{$v} eq "String"; 
  }
 my $input = join(" ",@inarray);
 my $convmissing_str = join("\n",@convmissing);
 my $informat = scalar(@indate) > 0 ? "INFORMAT " . join(" ",@indate) . " $format{'Date'} ;" : " ;";
 my $tname = $tab->{$t}->{'name'};
 my $tfpath = "$workingdir/fifo_$tag\_$tname.txt";

 $sassyntax .= "
filename ififo pipe 'cat $tfpath';
data $tname;
$informat
keep $headers ;
infile ififo DELIMITER='09'x MISSOVER FIRSTOBS=2 lrecl=1024;
input $input;
$convmissing_str
run;";
 }
$sassyntax .= "
$user_syntax";

return($sassyntax);
}

sub syntax_spss {
# makes the data object for SPSS
 my $user_syntax = shift;
 my $tab = shift;
 }

sub relquery {
my $res = shift;
my $vars = shift;
my $studyid = shift;
my $where = shift;
my $dbh = shift;

# get all the variable types based on the study, table and variable names
my $vtypes = $dbh->selectall_hashref("select d.name, v.variable, vt.type from variables_type as vt, variables as v, dtables_variables as dv, dtables as d where d.tid = dv.tid and v.v_auto = dv.vid and v.type = vt.vt_auto and d.study = $studyid",[ qw(name variable) ]);

my %tables = ();
foreach my $vs (@$vars){
 my ($t,$v) = split(/\./,$vs);
 $tables{$t}{'name'} = $t;
 #$tables{$t}{'vars'}{$v}++;
 $tables{$t}{'vars'}{$v} = $vtypes->{$t}->{$v}->{'type'};
 $tables{$t}{'where'} = $where->{$t};
 $tables{$t}{'where'} =~ s/;//g if defined($tables{$t}{'where'});
 $tables{$t}{'where'} =~ s/\t/ AND /g if defined($tables{$t}{'where'});
 }

# Now we have the tables, the variables in those tables, including the linking variable
# Now build the queries for each table for each resource
foreach my $t (keys %tables){
 my $tname = $tables{$t}{'name'};
 # note same statement for each resource as table name is the same
 $tables{$t}{'res'}{$_} = "select sql_no_cache " . join(",",sort {$a cmp $b} keys %{ $tables{$t}{'vars'} }) . " from $tname" foreach @{$res};
 if ( defined($tables{$t}{'where'}) ){ $tables{$t}{'res'}{$_} .= " where $tables{$t}{'where'}" foreach @{$res}; }
 # limits for testing
 #$tables{$t}{'res'}{$_} .= " limit 20000" foreach @{$res};
 }

=cut
# The query pulls the variables from the web query now get the ids of the variables
# The tables containing the variables are obtained and the links involved in the query are found
#       Make a hash here with table id as the key
#       Add the table name in {'name'}
#       Add the variables to the hash {'vars'}

my $dbh = DBI->connect($dsn, $dbuser, $dbpass, \%attr) || die "Could not connect to VIPAR database in config file: $DBI::errstr";
       
#my $stmt = "select dt.tid,name,variable from dtables_variables as dtv,dtables as dt,variables as v where dt.tid = dtv.tid and v.v_auto = dtv.vid and v.study = $studyid and variable in (\"". join("\",\"",@{$vars}) . "\")";
my $stmt = "select dt.tid,name,variable from dtables_variables as dtv,dtables as dt,variables as v where dt.tid = dtv.tid and v.v_auto = dtv.vid and v.study = $studyid and variable in (\"". join("\",\"",@{$vars}) . "\") and dtv.ind = 0";
my $query = $dbh->prepare($stmt);
$query->execute();

# when this sub is run as a thread there needs to be some way of feeding this error back and quitting the thread
if ($query->err){
 $log->error($query->err . " " . $query->errstr);
 } 

while(my @d = $query->fetchrow_array()){
 $tables{$d[0]}{'name'} = $d[1];
 $tables{$d[0]}{'vars'}{$d[2]}++;
 $tables{$d[0]}{'where'} = $where->{$d[1]};
 $tables{$d[0]}{'where'} =~ s/;//g if defined($tables{$d[0]}{'where'});
 $tables{$d[0]}{'where'} =~ s/\t/ AND /g if defined($tables{$d[0]}{'where'});
 }
$query->finish();

# Now we have the selected variables we need to make sure that the linking variable from each table containing selected variables is present in the list of variables to retrieve too
$stmt = "select dt.tid,variable from dtables_variables as dtv,dtables as dt,variables as v where dt.tid = dtv.tid and v.v_auto = dtv.vid and v.study = $studyid and ind = 1 and dt.tid in (". join(",",keys %tables) . ")";

$query = $dbh->prepare($stmt);
$query->execute();
while(my @d = $query->fetchrow_array()){
 $tables{$d[0]}{'vars'}{$d[1]}++;
 }
$query->finish();

# Now we have the tables, the variables in those tables, including the linking variable
# Now build the queries for each table for each resource
foreach my $t (keys %tables){
 my $tname = $tables{$t}{'name'};
 # note same statement for each resource as table name is the same
 $tables{$t}{'res'}{$_} = "select sql_no_cache " . join(",",sort {$a cmp $b} keys %{ $tables{$t}{'vars'} }) . " from $tname" foreach @{$res};
 if ( defined($tables{$t}{'where'}) ){ $tables{$t}{'res'}{$_} .= " where $tables{$t}{'where'}" foreach @{$res}; }
 # limits for testing
 #$tables{$t}{'res'}{$_} .= " limit 20000" foreach @{$res};
 }

=cut

return(\%tables);
}

sub makefifo {
my $tab = shift;
my $dbuser = shift;
my $dbpass = shift;
my $dsn = shift;
my $svs = shift;
my $workingdir = shift;
my $tag = shift;
my $clientpid = shift;
my $project = shift;
my $dateid = shift;
my $uid = shift;
my $time = shift;
my $stats = shift;
my $tname = $tab->{'name'};
my $err = 0;
my $fpath = "$workingdir/fifo_$tag\_$tname.txt";
unlink($fpath);

# signal handler
$SIG{KILL} = &gracefulexit($workingdir,$clientpid,$project,$dateid,$uid,$time,$tab,$tag);
$SIG{HUP}  = &gracefulexit($workingdir,$clientpid,$project,$dateid,$uid,$time,$tab,$tag);
$SIG{INT}  = &gracefulexit($workingdir,$clientpid,$project,$dateid,$uid,$time,$tab,$tag);
$SIG{QUIT} = &gracefulexit($workingdir,$clientpid,$project,$dateid,$uid,$time,$tab,$tag);
$SIG{TERM} = &gracefulexit($workingdir,$clientpid,$project,$dateid,$uid,$time,$tab,$tag);

#my %data_hash = ();
my $data_ref = undef;
my $gzip = IO::Compress::Gzip->new(\$data_ref) or die "IO::Compress::Gzip failed: $GzipError\n";

my $runstats = "";
my $hrcount = 0;

# add the variable names IN THE SAME ORDER AS THE QUERY to the data_hash
#$data_hash{0} = join("\t",sort {$a cmp $b} keys %{ $tab->{'vars'} }) . "\n";
$gzip->print( join("\t",sort {$a cmp $b} keys %{ $tab->{'vars'} }) . "\n" );

my $t = threads->tid();

# get the data for this table from each required resource using the relevant query
foreach my $r (keys %{ $tab->{'res'} }){
 # add the local port for this resource to the dsn
 my $lport = $svs->{$r};
 my $dsnport = $dsn . "$r:127.0.0.1:" . $lport;
 my %attr = (
  PrintError => 0,
  RaiseError => 0,
  AutoCommit => 0,
  mysql_read_timeout => 300,
  mysql_connect_timeout => 120
  );

 $log->warning("Process ".$$.":thread $t retrieving data for $tname from $r");

 my $dbhlvd = DBI->connect($dsnport, $dbuser, $dbpass, \%attr);
 if (!defined($dbhlvd)) {
  $log->error("Unable to connect to remote site $r on port $lport $DBI::errstr");	
  $runstats .= "Unable to connect to remote site $r on port $lport $DBI::errstr\n";
  eval { die "Unable to connect to remote site $r on port $lport $DBI::errstr\n" if !defined($dbhlvd); }; # this is for the benefit of the thread
  threads->exit();
  }

 my $sw = Misc::Stopwatch->new()->start();
 my $stmt = $tab->{'res'}->{$r};
 $log->warning("Running query $stmt");
 my $query = $dbhlvd->prepare($stmt);
 $query->execute();
 my $rcount=0;
 while( my @row = $query->fetchrow_array()){
  $rcount++;
  $hrcount++;
  if(($stats eq "r") || ($stats eq "stata")){ for(@row) { $_ = 'NA' if $_ eq ""; } }
  if($stats eq "sas"){ for(@row) { $_ = '.M' if $_ eq ""; } }
  #$data_hash{$hrcount} = join("\t",@row) . "\n"; # this line produces a lot of warnings about uninitialised values when there is missing data in the dataset
  $gzip->print( join("\t",@row) . "\n" ); # this line produces a lot of warnings about uninitialised values when there is missing data in the dataset
  }
 $query->finish();
 $sw->stop();
 my $time = $sw->elapsed();
 $runstats .= "$rcount records retrieved from $tname on $r in " . sprintf("%6.2f",$time) ." seconds\n";
 $sw->reset();

 $dbhlvd->disconnect();
 }

$gzip->close();
$runstats .= "A total of $hrcount records were retrieved for $tname\n";
 
# make the fifo based on the fpath
unless (-p $fpath) {   # not a pipe
 if (-e _) {        # but a something else
  $log->error("$0: won't overwrite $fpath FIFO - exiting thread\n");
  }
 else {
  require POSIX;
  POSIX::mkfifo($fpath, 0666) or $log->error("can't mknod $fpath: $!");
  }
 }
 
if (-p $fpath) {
 # next line blocks until there's a reader
 #open(TMP,">/tmp/$tname.blah");
 #print TMP $data_hash{$_} foreach (sort {$a <=> $b} keys %data_hash);
 #close(TMP);
 sysopen(FIFO, $fpath, O_WRONLY) or $log->error("can't write $fpath: $!");
 #print FIFO $data_hash{$_} foreach (sort {$a <=> $b} keys %data_hash);
 my $gunzip = IO::Uncompress::Gunzip->new(\$data_ref) or die "IO::Uncompress::Gunzip failed: $GunzipError\n";
 while (my $gzline = $gunzip->getline()){
  print FIFO $gzline;
  }
 $gunzip->close();
 close FIFO;
 $log->warning("Process ".$$.":thread $tag ".threads->self->tid()." wrote $hrcount records to fifo for $tname");
 $data_ref = undef;
 #%data_hash = ();
 }

return($runstats);
}

sub gracefulexit {
my $workingdir = shift;
my $clientpid = shift;
my $project = shift;
my $dateid = shift;
my $uid = shift;
my $time = shift;
my $tab = shift;
my $tag = shift;

my $sub = sub {

$log->warning("Exec process $clientpid killed (or stopped by user):  exiting gracefully");

my $dbh = DBI->connect($dsn, $dbuser, $dbpass, \%attr) || die "Could not connect to VIPAR database in config file: $DBI::errstr";

#set error flag to run_status
$dbh->do("update run_time set run_status=-1 where project=$project and run_date=$dateid and user=$uid and run_time=\'$time\'");

#make sure fifo is deleted
foreach my $t (keys %{$tab}){
 my $fpath = "$workingdir/fifo_$tag\_$t.txt";
 unlink($fpath);
 }

open(STATUS, ">$workingdir/state.txt");
print STATUS "E\n";
close(STATUS);

$dbh->disconnect();

threads->exit(0);
};

return($sub);
}

# sub to run stata
sub stata_runstata {
my $tab = shift;
my $dbuser = shift;
my $dbpass = shift;
my $dsn = shift;
my $svs = shift;
my $workingdir = shift;
my $tag = shift;
my $clientpid = shift;
my $project = shift;
my $dateid = shift;
my $uid = shift;
my $time = shift;
my $stats = shift;
my $batchcode = shift;
my $tname = $tab->{'name'};
my $err = 0;
my $fpath = "$workingdir/fifo_r2stata.txt";

$ENV{'PATH'} = $ENV{'PATH'}.":".File::Util->return_path( $config->get("stats_stata") );
$ENV{'STATATMP'} = "/data/saswork/statatmp";

# signal handler
$SIG{KILL} = &gracefulexit($workingdir,$clientpid,$project,$dateid,$uid,$time,$tab,$tag);
$SIG{HUP}  = &gracefulexit($workingdir,$clientpid,$project,$dateid,$uid,$time,$tab,$tag);
$SIG{INT}  = &gracefulexit($workingdir,$clientpid,$project,$dateid,$uid,$time,$tab,$tag);
$SIG{QUIT} = &gracefulexit($workingdir,$clientpid,$project,$dateid,$uid,$time,$tab,$tag);
$SIG{TERM} = &gracefulexit($workingdir,$clientpid,$project,$dateid,$uid,$time,$tab,$tag);

# wait for fifo to be made
while(! -p "$fpath"){
 #print "waiting for fifo\n";
 sleep(1);
 }
sleep(2);
if (-p "$fpath"){
 #print "here it is\n";
 # run stata
 #print "running stata\n";
 system("export STATATMP=/data/saswork/statatmp;". $config->get("stats_stata")." < $batchcode > $workingdir/STATA.log.txt");
 sleep(1);
 }
#print "stata sub finished\n";
}
