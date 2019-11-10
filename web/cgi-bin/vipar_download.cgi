#!/usr/bin/perl

use strict;
use DBI;
use CGI;
use CGI::Carp qw(fatalsToBrowser);
use CGI::Session;
use Digest::MD5 qw(md5_hex);
use AppConfig;
use File::Util;
use File::Path;
use File::DirList;
use File::MimeInfo::Magic qw(magic mimetype);
use IO::Socket::INET;

# Check for Cookie or err
my $cgi = new CGI;
my $sid = $cgi->cookie("VIPAR_CGISESSID") || &err_login();

my $session = CGI::Session->load($sid);
&err_login() if $session->is_expired();
$session->expire('+1h');
my $uid = $session->param("userid");
my %cookies = fetch CGI::Cookie;
my $cookie = $cookies{'VIPAR_CGISESSID'};
$cookie->expires('+1h');

my $form = new CGI;

my $vd = $form->param('vd');
my $p = $form->param('p');
my $d = $form->param('d');
my $t = $form->param('t');
my $f = $form->param('f');
my $l = $form->param('l');
my $filelocation = $ENV{'VIPAR_ROOT'}."/projects";
my $filepath = "$filelocation\/project_$p\/$d\/$t\/$f";
$filepath = "$filelocation\/project_$p\/codelibs/$l"."libs\/$f" if $l;

my $ext = "txt";
if ($f =~ /\w+\.(\w+)$/){
 $ext = $1;
 }

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

# connect to DB
my $dsn = "dbi:mysql:".$dbconfig->get("database_name");
my $dbuser = $dbconfig->get("database_queryuser");
my $dbpass = $dbconfig->get("database_querypass");
my %attr = (
        RaiseError => 1,
        AutoCommit => 0
        );
my $dbh = DBI->connect($dsn, $dbuser, $dbpass, \%attr);

# get details from vipar_config table
my $stmt = "select v_key,v_value from vipar_config where v_key in ('server_servername','server_execport','execkey')";
my %config = map { $_->[0], $_->[1]} @{$dbh->selectall_arrayref($stmt)};

if (!keys %config)  #if nothing returned
{
        print $cgi->header();
        print $cgi->start_html(
                -title=>'Virtual Pooling and Analysis of Research data - ViPAR - site down!',);
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

# get the project name
$stmt="select project from projects where p_auto = $p";
my ($project) = $dbh->selectrow_array($stmt);

# get the user name
$stmt="select username from users where u_auto = $uid";
my ($user) = $dbh->selectrow_array($stmt);

#log error to VIPARD log file
my $sock = IO::Socket::INET->new(PeerAddr => $servername,
                                 PeerPort => $execport,
                                 Proto     => 'tcp') or die "can't connect to VIPARD: $!";
#print "Successfully connected to $server:$port\n";
$sock->autoflush(1);

# list of banned file extensions that are not allowed to be downloaded
# ensure lowercase for patternmatch
my @banned = qw(rdata sas sas7bcat);

if ($vd eq "d"){
 if (grep { lc($ext) eq $_ } @banned){
  #send exec key for verification
  print $sock "$execkey\n";
  print $sock "log\n"; #send log command  
  print $sock "warning\n"; #send log level
  print $sock "Download request for banned filename $f from project $project sub analysis $d > $t from user '$user', from IP address ".$cgi->remote_host()."\n"; #uid
  $sock->close();

  print $cgi->header();
  print $cgi->start_html();
  print "<p style=\"font-size:10px;font-family:verdana,geneva,sans-serif;color:red;\">This is a banned filename ($f) for download, this incident has been reported</p>";
  $cgi->end_html();
 
  $dbh->disconnect();
 
  exit(1);
  }

 my $content = &content_type(lc($ext));
 # establish magic type
 my $magic = magic($filepath) ? magic($filepath) : mimetype($filepath);
 # check that $content and $magic concur (someone may be masking a txt file as a PDF to get around the file size limitations)
 # get file size
 my ($fs) = File::Util->new();
 my $size = $fs->size($filepath);
 #check size
 my $oksize = &check_size($magic,$size);

 #send exec key for verification
 print $sock "$execkey\n";
 print $sock "log\n"; #send log command  
 print $sock "warning\n"; #send log level
 print $sock "Download request for $f from project $project sub analysis $d > $t from user '$user', from IP address ".$cgi->remote_host()." file type ($magic) size $oksize\n"; #uid
 $sock->close();

 open(DLFILE, "<$filepath");
 my @fileholder = <DLFILE>;
 close (DLFILE);

 print "Content-Type:$content\n";
 print "Content-Disposition:attachment;filename=\"$f\"\n\n";
 print @fileholder;
 }
elsif ($vd eq "v") {
 
# check magic bits correspond to the extension MIME type (someone may be masking a txt file as a PDF to get around the file size limitations)
# use File::Type; my $ft = File::Type->new(); my $type_from_file = $ft->checktype_filename("ViPAR_schema_140614.png");
# check file size against accepted file sizes
# add warning messages to logged message

#send exec key for verification
 print $sock "$execkey\n";
 print $sock "log\n"; #send log command  
 print $sock "warning\n"; #send log level
 print $sock "View request for $f from project $project sub analysis $d > $t from user '$user', from IP address ".$cgi->remote_host()."\n"; #uid
 $sock->close();

 $| = 1;
 print $cgi->header(
  -Pragma=>'no-cache',
  -Cache_Control=>'no-store,no-cache,must-revalidate,post-check=0,pre-check=0'
  );
 print $cgi->start_html(
  -title=>'Virtual Pooling and Analysis of Research - ViPAR',
  -style=>{'src'=>"/viparstyle/vipar.css"},
  -script=>[ {-type=>'text/javascript',-src=>'/viparjs/jquery-1.4.2.js'}, {-type=>'text/javascript',-src=>'/viparjs/view.js'} ]
   );
 # make a temporary folder
 my $stub = "tmp_" . md5_hex(localtime());
 my $tmp = $ENV{'VIPAR_ROOT'}."/web/images/tempimg/$stub";
 mkdir($tmp);
 # convert -density 300 plsregression.pdf -resize 25% a.png
 if ($ext eq "pdf"){
  system("/usr/bin/convert -density 300 $filepath -resize 25% $tmp/$f.png");
  }
 # convert text:SAS.log.txt runlog.png
 elsif (($ext eq "txt") || ($ext eq "log")){
  system("/usr/bin/convert -font Courier text:$filepath $tmp/$f.png");
  }
 # convert rose.jpg rose.png
 # png jpeg jpg tiff bmp gif
 else {
  system("/usr/bin/convert $filepath $tmp/$f.png");
  }
 # display the images with an overlay
 my $list = File::DirList::list($tmp, 'nc', 1, 1, 0);
 foreach my $file (@{$list}){
  my $fn = $file->[13];
  next if $fn eq "..";
  print "<div id=\"container\">";
  print "<div id=\"main_image\"><img src=\"/viparimages/tempimg/$stub/$fn\"></div>";
  print "<div id=\"overlay_image\"><img src=\"/viparimages/blankcanvas.png\"></div>";
  print "</div>";
  }
 print $cgi->end_html();
 # delete the data
 sleep(2);
 #rmtree( $tmp );
 }
else {
 print $cgi->header();
 }

sub content_type {
my $ext = shift;
my $type = "";
my %mime_hash = ();
$mime_hash{'323'} = "text/h323";
$mime_hash{'acx'} = "application/internet-property-stream";
$mime_hash{'ai'} = "application/postscript";
$mime_hash{'aif'} = "audio/x-aiff";
$mime_hash{'aifc'} = "audio/x-aiff";
$mime_hash{'aiff'} = "audio/x-aiff";
$mime_hash{'asf'} = "video/x-ms-asf";
$mime_hash{'asr'} = "video/x-ms-asf";
$mime_hash{'asx'} = "video/x-ms-asf";
$mime_hash{'au'} = "audio/basic";
$mime_hash{'avi'} = "video/x-msvideo";
$mime_hash{'axs'} = "application/olescript";
$mime_hash{'bas'} = "text/plain";
$mime_hash{'bcpio'} = "application/x-bcpio";
$mime_hash{'bin'} = "application/octet-stream";
$mime_hash{'bmp'} = "image/bmp";
$mime_hash{'c'} = "text/plain";
$mime_hash{'cat'} = "application/vnd.ms-pkiseccat";
$mime_hash{'cdf'} = "application/x-cdf";
$mime_hash{'cer'} = "application/x-x509-ca-cert";
$mime_hash{'class'} = "application/octet-stream";
$mime_hash{'clp'} = "application/x-msclip";
$mime_hash{'cmx'} = "image/x-cmx";
$mime_hash{'cod'} = "image/cis-cod";
$mime_hash{'cpio'} = "application/x-cpio";
$mime_hash{'crd'} = "application/x-mscardfile";
$mime_hash{'crl'} = "application/pkix-crl";
$mime_hash{'crt'} = "application/x-x509-ca-cert";
$mime_hash{'csh'} = "application/x-csh";
$mime_hash{'css'} = "text/css";
$mime_hash{'dcr'} = "application/x-director";
$mime_hash{'der'} = "application/x-x509-ca-cert";
$mime_hash{'dir'} = "application/x-director";
$mime_hash{'dll'} = "application/x-msdownload";
$mime_hash{'dms'} = "application/octet-stream";
$mime_hash{'do'} = "text/plain";
$mime_hash{'doc'} = "application/msword";
$mime_hash{'dot'} = "application/msword";
$mime_hash{'dvi'} = "application/x-dvi";
$mime_hash{'dxr'} = "application/x-director";
$mime_hash{'eps'} = "application/postscript";
$mime_hash{'etx'} = "text/x-setext";
$mime_hash{'evy'} = "application/envoy";
$mime_hash{'exe'} = "application/octet-stream";
$mime_hash{'fif'} = "application/fractals";
$mime_hash{'flr'} = "x-world/x-vrml";
$mime_hash{'gif'} = "image/gif";
$mime_hash{'gtar'} = "application/x-gtar";
$mime_hash{'gz'} = "application/x-gzip";
$mime_hash{'h'} = "text/plain";
$mime_hash{'hdf'} = "application/x-hdf";
$mime_hash{'hlp'} = "application/winhlp";
$mime_hash{'hqx'} = "application/mac-binhex40";
$mime_hash{'hta'} = "application/hta";
$mime_hash{'htc'} = "text/x-component";
$mime_hash{'htm'} = "text/html";
$mime_hash{'html'} = "text/html";
$mime_hash{'htt'} = "text/webviewhtml";
$mime_hash{'ico'} = "image/x-icon";
$mime_hash{'ief'} = "image/ief";
$mime_hash{'iii'} = "application/x-iphone";
$mime_hash{'ins'} = "application/x-internet-signup";
$mime_hash{'isp'} = "application/x-internet-signup";
$mime_hash{'jfif'} = "image/pipeg";
$mime_hash{'jpe'} = "image/jpeg";
$mime_hash{'jpeg'} = "image/jpeg";
$mime_hash{'jpg'} = "image/jpeg";
$mime_hash{'js'} = "application/x-javascript";
$mime_hash{'latex'} = "application/x-latex";
$mime_hash{'lha'} = "application/octet-stream";
$mime_hash{'lsf'} = "video/x-la-asf";
$mime_hash{'lsx'} = "video/x-la-asf";
$mime_hash{'lzh'} = "application/octet-stream";
$mime_hash{'m13'} = "application/x-msmediaview";
$mime_hash{'m14'} = "application/x-msmediaview";
$mime_hash{'m3u'} = "audio/x-mpegurl";
$mime_hash{'man'} = "application/x-troff-man";
$mime_hash{'mdb'} = "application/x-msaccess";
$mime_hash{'me'} = "application/x-troff-me";
$mime_hash{'mht'} = "message/rfc822";
$mime_hash{'mhtml'} = "message/rfc822";
$mime_hash{'mid'} = "audio/mid";
$mime_hash{'mny'} = "application/x-msmoney";
$mime_hash{'mov'} = "video/quicktime";
$mime_hash{'movie'} = "video/x-sgi-movie";
$mime_hash{'mp2'} = "video/mpeg";
$mime_hash{'mp3'} = "audio/mpeg";
$mime_hash{'mpa'} = "video/mpeg";
$mime_hash{'mpe'} = "video/mpeg";
$mime_hash{'mpeg'} = "video/mpeg";
$mime_hash{'mpg'} = "video/mpeg";
$mime_hash{'mpp'} = "application/vnd.ms-project";
$mime_hash{'mpv2'} = "video/mpeg";
$mime_hash{'ms'} = "application/x-troff-ms";
$mime_hash{'mvb'} = "application/x-msmediaview";
$mime_hash{'nws'} = "message/rfc822";
$mime_hash{'oda'} = "application/oda";
$mime_hash{'p10'} = "application/pkcs10";
$mime_hash{'p12'} = "application/x-pkcs12";
$mime_hash{'p7b'} = "application/x-pkcs7-certificates";
$mime_hash{'p7c'} = "application/x-pkcs7-mime";
$mime_hash{'p7m'} = "application/x-pkcs7-mime";
$mime_hash{'p7r'} = "application/x-pkcs7-certreqresp";
$mime_hash{'p7s'} = "application/x-pkcs7-signature";
$mime_hash{'pbm'} = "image/x-portable-bitmap";
$mime_hash{'pdf'} = "application/pdf";
$mime_hash{'pfx'} = "application/x-pkcs12";
$mime_hash{'pgm'} = "image/x-portable-graymap";
$mime_hash{'pko'} = "application/ynd.ms-pkipko";
$mime_hash{'pma'} = "application/x-perfmon";
$mime_hash{'pmc'} = "application/x-perfmon";
$mime_hash{'pml'} = "application/x-perfmon";
$mime_hash{'pmr'} = "application/x-perfmon";
$mime_hash{'pmw'} = "application/x-perfmon";
$mime_hash{'png'} = "image/png";
$mime_hash{'pnm'} = "image/x-portable-anymap";
$mime_hash{'pot,'} = "application/vnd.ms-powerpoint";
$mime_hash{'ppm'} = "image/x-portable-pixmap";
$mime_hash{'pps'} = "application/vnd.ms-powerpoint";
$mime_hash{'ppt'} = "application/vnd.ms-powerpoint";
$mime_hash{'prf'} = "application/pics-rules";
$mime_hash{'ps'} = "application/postscript";
$mime_hash{'pub'} = "application/x-mspublisher";
$mime_hash{'qt'} = "video/quicktime";
$mime_hash{'r'} = "text/plain";
$mime_hash{'R'} = "text/plain";
$mime_hash{'ra'} = "audio/x-pn-realaudio";
$mime_hash{'ram'} = "audio/x-pn-realaudio";
$mime_hash{'ras'} = "image/x-cmu-raster";
$mime_hash{'rgb'} = "image/x-rgb";
$mime_hash{'rmi'} = "audio/mid";
$mime_hash{'roff'} = "application/x-troff";
$mime_hash{'rtf'} = "application/rtf";
$mime_hash{'rtx'} = "text/richtext";
$mime_hash{'sas'} = "text/plain";
$mime_hash{'scd'} = "application/x-msschedule";
$mime_hash{'sct'} = "text/scriptlet";
$mime_hash{'setpay'} = "application/set-payment-initiation";
$mime_hash{'setreg'} = "application/set-registration-initiation";
$mime_hash{'sh'} = "application/x-sh";
$mime_hash{'shar'} = "application/x-shar";
$mime_hash{'sit'} = "application/x-stuffit";
$mime_hash{'snd'} = "audio/basic";
$mime_hash{'spc'} = "application/x-pkcs7-certificates";
$mime_hash{'spl'} = "application/futuresplash";
$mime_hash{'src'} = "application/x-wais-source";
$mime_hash{'sst'} = "application/vnd.ms-pkicertstore";
$mime_hash{'stl'} = "application/vnd.ms-pkistl";
$mime_hash{'stm'} = "text/html";
$mime_hash{'svg'} = "image/svg+xml";
$mime_hash{'sv4cpio'} = "application/x-sv4cpio";
$mime_hash{'sv4crc'} = "application/x-sv4crc";
$mime_hash{'swf'} = "application/x-shockwave-flash";
$mime_hash{'t'} = "application/x-troff";
$mime_hash{'tar'} = "application/x-tar";
$mime_hash{'tcl'} = "application/x-tcl";
$mime_hash{'tex'} = "application/x-tex";
$mime_hash{'texi'} = "application/x-texinfo";
$mime_hash{'texinfo'} = "application/x-texinfo";
$mime_hash{'tgz'} = "application/x-compressed";
$mime_hash{'tif'} = "image/tiff";
$mime_hash{'tiff'} = "image/tiff";
$mime_hash{'tr'} = "application/x-troff";
$mime_hash{'trm'} = "application/x-msterminal";
$mime_hash{'tsv'} = "text/tab-separated-values";
$mime_hash{'txt'} = "text/plain";
$mime_hash{'uls'} = "text/iuls";
$mime_hash{'ustar'} = "application/x-ustar";
$mime_hash{'vcf'} = "text/x-vcard";
$mime_hash{'vrml'} = "x-world/x-vrml";
$mime_hash{'wav'} = "audio/x-wav";
$mime_hash{'wcm'} = "application/vnd.ms-works";
$mime_hash{'wdb'} = "application/vnd.ms-works";
$mime_hash{'wks'} = "application/vnd.ms-works";
$mime_hash{'wmf'} = "application/x-msmetafile";
$mime_hash{'wps'} = "application/vnd.ms-works";
$mime_hash{'wri'} = "application/x-mswrite";
$mime_hash{'wrl'} = "x-world/x-vrml";
$mime_hash{'wrz'} = "x-world/x-vrml";
$mime_hash{'xaf'} = "x-world/x-vrml";
$mime_hash{'xbm'} = "image/x-xbitmap";
$mime_hash{'xla'} = "application/vnd.ms-excel";
$mime_hash{'xlc'} = "application/vnd.ms-excel";
$mime_hash{'xlm'} = "application/vnd.ms-excel";
$mime_hash{'xls'} = "application/vnd.ms-excel";
$mime_hash{'xlt'} = "application/vnd.ms-excel";
$mime_hash{'xlw'} = "application/vnd.ms-excel";
$mime_hash{'xof'} = "x-world/x-vrml";
$mime_hash{'xpm'} = "image/x-xpixmap";
$mime_hash{'xwd'} = "image/x-xwindowdump";
$mime_hash{'z'} = "application/x-compress";
$mime_hash{'zip'} = "application/zip";

$type = $mime_hash{$ext};
return($type);
}

sub check_size {
my $type = shift;
my $size = shift;
my $msg = "OK";
# default max size for undefined MIME
my $default = 1000000;
#  make ahash storing the mime types and the allowed file size limits
my %sizehash = ();
# PDF PS EPS => 1M
$sizehash{'application/pdf'} = 1000000;
$sizehash{'application/postscript'} = 1000000;
# TXT, XML, RTF => 500K
# csv, text, log, r, R
$sizehash{'text/plain'} = 500000;
$sizehash{'text/html'} = 500000;
# ZIP => 10M
# tar, gz
$sizehash{'application/zip'} = 10000000;
$sizehash{'application/x-gzip'} = 10000000;
$sizehash{'application/x-tar'} = 10000000;
# PNG, GIF TIFF, TIF, BMP, JPG, JPEG => 3M
$sizehash{'image/jpeg'} = 3000000;
$sizehash{'image/bmp'} = 3000000;
$sizehash{'image/png'} = 3000000;
$sizehash{'image/svg+xml'} = 3000000;
$sizehash{'image/gif'} = 3000000;
$sizehash{'image/tiff'} = 3000000;
# doc etc
$sizehash{'application/vnd.ms-excel'} = 1000000;
$sizehash{'application/vnd.ms-word'} = 1000000;
$sizehash{'application/x-ole-storage'} = 1000000;
$sizehash{'application/msword'} = 1000000;

if (defined $sizehash{$type}){
 $msg = "NOT_OK" if $size > $sizehash{$type};
 }
else {
 $msg = "NOT_OK" if $size > $default;
 }

return($msg);
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

sub ban {
my $f = shift;


}
