<html>
 <head>
  <title>ViPAR Web-based Analysis Portal - Login</title>
  <link rel="stylesheet" type="text/css" href="/viparstyle/vipar.css" />
 </head>
 <body>
  <div class="logindiv">
   <form name="login" method="post" action="/viparcgi/vipar_login.cgi">
    <fieldset>  
     <legend>ViPAR Login</legend>  
     <table>  
      <tr><td><label for="user">Username:</label></td><td colspan="2"><input name="user" type="text" id="user" size="30" /></td></tr>  
      <tr><td><label for="pass">Password:</label></td><td colspan="2"><input name="pass" type="password" id="pass" size="30" /></td></tr>  
      <tr><td></td><td style="text-align:center"><input type="submit" value="LOGIN" /></td><td style="text-align:left"><input type="reset" value="RESET" /></td></tr>  
      <tr><td colspan="3"><br>By using ViPAR you are agreeing to be bound by the <a id="tdpop" href="#"><u>HARMONY ViPAR User Agreement</u>
       <div style="position:absolute; z-index:9;">
<?php
require("/usr/local/vipar/web/html/user_agreement.php");
?>
      </div></a></td></tr>
     </table>
    </fieldset>  
   </form>
  </div>
 </body>
</html>
