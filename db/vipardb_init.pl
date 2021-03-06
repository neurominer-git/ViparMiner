#!/usr/bin/perl

use strict;

# make sure the script is being run by root
die "Error: exiting as not executed by root user\n" if ($<);
print "Please provide the location of your ViPAR root directory (usually /usr/local/vipar): ";
my $vipar = <STDIN>;
chomp $vipar;
# check that the directory location exists
die "Your VIPAR_ROOT directory ($vipar) does not exist. Consult the manual to find out how to reset it\n" if !-e $vipar;
# Need to check that the sql initialisng file exists before we use it
my $vipar_dbinit = "$vipar/db/vipar_initialise.sql";
die "The ViPAR SQL initialising file ($vipar_dbinit) does not exist. Exiting\n" if !-e $vipar_dbinit;

# stop the ViPAR daemon
print "Stopping the ViPAR daemon\n";
system("systemctl stop vipar");
# blank the /etc/xinetd.d/vipar file
# note that this will server to empty the file if it exists and create it if it doesn't exist
# either way the result will be an empty file
print "Emptying Xinetd vipar file\n";
system("cp -f /etc/xinetd.d/vipar /etc/xinetd.d/vipar.old");
open(EMPTY,">/etc/xinetd.d/vipar") || die "Can't empty /etc/xinetd.d/vipar: $!\n\n";
close(EMPTY);
# restart xinetd
print "Restarting xinetd\n";
system("systemctl restart xinetd");
# load the mysql file into the database
print "Initialising the vipar database\nProvide MySQL root user password from the manual (unless you have already changed this) when prompted:\n";
system("mysql -u root -p < $vipar_dbinit");
# restart mysql
print "Restarting mysqld\n";
system("systemctl restart mysqld");
# remove everything from the projects directory
print "Removing files from $vipar/projects\n";
if (-e "$vipar/projects/"){
 system("rm -rf $vipar/projects/*");
 }
# restart the vipar daemon
print "Starting the ViPAR daemon\n";
system("systemctl start vipar");

print "Done! Please open a browser and login as the viparadmin user with the default credentials in the manual\n";

