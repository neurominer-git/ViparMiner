#!/usr/bin/perl

use strict;
use DBI;
use CGI;
use CGI::Carp qw(fatalsToBrowser);
use CGI::Session;
use CGI::Cookie;

# Check for Cookie or err
my $cgi = new CGI;
my $sid = $cgi->cookie("VIPAR_CGISESSID") || &err_login();

my $session = CGI::Session->load($sid);
&err_login() if $session->is_expired();
$session->expire('-1s');
my %cookies = fetch CGI::Cookie;
my $cookie = $cookies{'VIPAR_CGISESSID'};
$cookie->expires('-1s');
# send the browser cookie back to the browser
print $cgi->header( -cookie=>[$cookie], -charset=>'utf-8' );
print $cgi->start_html(
        -head => $cgi->meta({
                -http_equiv => 'Refresh',
                -content => '0;URL=/vipar'
                })
        );
print $cgi->end_html();

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
