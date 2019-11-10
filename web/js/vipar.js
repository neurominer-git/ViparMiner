//Browser Support Code
function ajaxFunction(div,size){
var ajaxRequest;  // The variable that makes Ajax possible!
try{
// Opera 8.0+, Firefox, Safari
 ajaxRequest = new XMLHttpRequest();
 } catch (e){
 // Internet Explorer Browsers
 try{
  ajaxRequest = new ActiveXObject("Msxml2.XMLHTTP");
  } catch (e){
  try{
   ajaxRequest = new ActiveXObject("Microsoft.XMLHTTP");
   } catch (e){
   // Something went wrong
   alert("You're using an unsupported browser!");
   return false;
   }
  }
 }

 // Create a function that will receive data sent from the server
 ajaxRequest.onreadystatechange = function(){
  // readyState can be processing downloading or complete
  // When readyState changes onreadystatechange executes
  //var ajaxDisplay = document.getElementById(div);
  if(ajaxRequest.readyState == 4){
   // Get the data from the server's response stored in responseText
   $("#" + div).html(ajaxRequest.responseText)
   //ajaxDisplay.innerHTML = ajaxRequest.responseText;
   }
  else{
   if (size){
    $("#" + div).html('<img src="/viparimages/loading_small.gif">');
    //ajaxDisplay.innerHTML = '<img src="/viparimages/loading_small.gif">';
    }
   else {
    $("#" + div).html('<img src="/viparimages/loading.gif">');
    //ajaxDisplay.innerHTML = '<img src="/viparimages/loading.gif">';
    }
   }
  }
 return(ajaxRequest);
 }

function projheader(proj,type){
 var ajaxRequest = ajaxFunction('runres');
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?proj="+proj+"&type="+type+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_project.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null);
 }

function getruninfo(proj,type){
 var ajaxRequest = ajaxFunction('display');
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type="+type+"&proj="+proj+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_project.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null);
 }

function getprojdates(proj,type){
 var ajaxRequest = ajaxFunction('display');
 var date = new Date();
 var timestamp = date.getTime();
 //document.getElementById('files').innerHTML = "";
 // use the ajaxRequest object to actually post something to the server
 var query = "?proj="+proj+"&type="+type+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_project.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null);
 }

function getprojdatesshared(proj,type){
 var ajaxRequest = ajaxFunction('display');
 var date = new Date();
 var timestamp = date.getTime();
 //document.getElementById('files').innerHTML = "";
 // use the ajaxRequest object to actually post something to the server
 var query = "?proj="+proj+"&type="+type+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_project.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null);
 }


function codelib(proj,type){
 var ajaxRequest = ajaxFunction('display');
 var date = new Date();
 var timestamp = date.getTime();
 //document.getElementById('files').innerHTML = "";
 // use the ajaxRequest object to actually post something to the server
 var query = "?proj="+proj+"&type="+type+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_project.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null);
 }

function getprojruntimes(proj,rundate){
 var ajaxRequest = ajaxFunction('fileman');
 var date = new Date();
 var timestamp = date.getTime();
 document.getElementById('files').innerHTML = "";
 // use the ajaxRequest object to actually post something to the server
 var query = "?proj="+proj+"&rdate="+rundate+"&type=rt&time="+timestamp;

 ajaxRequest.open('GET', '/viparcgi/vipar_project.cgi'+query, true);
// ajaxRequest.open('GET', '/viparcgi/vipar_project.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null);
 }

function getprojruntimesshared(proj,rundate){
 var ajaxRequest = ajaxFunction('fileman');
 var date = new Date();
 var timestamp = date.getTime();
 document.getElementById('files').innerHTML = "";
 // use the ajaxRequest object to actually post something to the server
 var query = "?proj="+proj+"&rdate="+rundate+"&type=rtshared&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_project.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null);
 }
 

function getprojfiles(proj,rundate,runtime){
 var ajaxRequest = ajaxFunction('files');
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?proj="+proj+"&rdate="+rundate+"&rtime="+runtime+"&type=f&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_project.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null);
 }

function getcodelibs(proj,lib){
 var ajaxRequest = ajaxFunction('files');
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?proj="+proj+"&lib="+lib+"&type=gcl&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_project.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null);
 }

function shareruntime(proj,runtime,rundate,val){
 var ajaxRequest = ajaxFunction('fileman');
 // use the ajaxRequest object to actually post something to the server
 var query = "?proj="+proj+"&rtime="+runtime+"&share="+val+"&type=shrt";
 ajaxRequest.open('GET', '/viparcgi/vipar_project.cgi'+query, false);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null);
 getprojruntimes(proj,rundate);
 }
 

function delruntime(proj,runtime,rundate){
 var yorn = confirm("Are you sure you want to delete this run?\n\nNote that all files are still retained on the server");
 if (yorn){
  var ajaxRequest = ajaxFunction('fileman');
  var date = new Date();
  var timestamp = date.getTime();
  // use the ajaxRequest object to actually post something to the server
  var query = "?proj="+proj+"&rtime="+runtime+"&type=drt&time="+timestamp;
  ajaxRequest.open('GET', '/viparcgi/vipar_project.cgi'+query, false);
  ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
  ajaxRequest.send(null);
  getprojruntimes(proj,rundate);
  }
 else {
  getprojruntimes(proj,rundate);
  return false;
  }
 }

function delcodelib(proj,file,lib){
 var yorn = confirm("Are you sure you want to delete this code library?\n\nNote that all files are still retained on the server");
 if (yorn){
  var ajaxRequest = ajaxFunction('files');
  var date = new Date();
  var timestamp = date.getTime();
  // use the ajaxRequest object to actually post something to the server
  var query = "?proj="+proj+"&lib="+lib+"&file="+file+"&type=dcl&time="+timestamp;
  ajaxRequest.open('GET', '/viparcgi/vipar_project.cgi'+query, false);
  ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
  ajaxRequest.send(null);
  getcodelibs(proj,lib);
  }
 else {
  getcodelibs(proj,lib);
  return false;
  }
 }

function sitestatsum(){
 var ajaxRequest = ajaxFunction('runres');
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=ss&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_home.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null);
 }

function new_proj(){
 var ajaxRequest = ajaxFunction('runres');
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=np&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_manageprojects.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null);
 }

function new_user(){
 var ajaxRequest = ajaxFunction('runres');
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=nu&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_manageusers.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null);
 }

function new_vardd(){
 var ajaxRequest = ajaxFunction('runres');
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=nv&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_managevariables.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null);
 }

function new_res(){
 var ajaxRequest = ajaxFunction('runres');
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=nr&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_manageresources.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null);
 }

function do_cert(){
 var ajaxRequest = ajaxFunction('runres');
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=cert&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_certification.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null);
 }

function upcert(check,rid){
 var ajaxRequest = ajaxFunction('scert');
 var date = new Date();
 var timestamp = date.getTime();
 var sname = document.getElementById("sname").value;
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=cu&check="+check+"&rsname="+rid+"&sname="+sname+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_certification.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null);
 }

function newpass(div,pre){
 var ajaxRequest = ajaxFunction(div,'1');
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=np&pre="+pre+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_manageusers.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function get_uinfo(val,div){
 var ajaxRequest = ajaxFunction(div);
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=uu&uname="+val+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_manageusers.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function get_sinfo(val,div){
 var ajaxRequest = ajaxFunction(div);
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=si&sname="+val+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_managestudies.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function get_minfo(val,div){
 var ajaxRequest = ajaxFunction(div);
 var date = new Date();
 var timestamp = date.getTime();
 var sname = document.getElementById("sname").value;
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=mi&sname="+sname+"&mname="+val+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_managevariables.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function get_vinfo(val,div){
 var ajaxRequest = ajaxFunction(div);
 var date = new Date();
 var timestamp = date.getTime();
 var sname = document.getElementById("sname").value;
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=vi&sname="+sname+"&vname="+val+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_managevariables.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function get_dtinfo(val,div){
 var ajaxRequest = ajaxFunction(div);
 var date = new Date();
 var timestamp = date.getTime();
 var sname = document.getElementById("sname").value;
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=dti&sname="+sname+"&dtname="+val+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_managevariables.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function get_ddinfo(val,div){
 var ajaxRequest = ajaxFunction(div);
 var date = new Date();
 var timestamp = date.getTime();
 var sname = document.getElementById("sname").value;
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=ddi&sname="+sname+"&ddname="+val+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_managevariables.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function get_mvd(val,div){
 var ajaxRequest = ajaxFunction(div);
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=mvd&sname="+val+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_managevariables.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function get_mvd_info(val,val2,div){
 var ajaxRequest = ajaxFunction(div);
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=mvdi&mvd="+val+"&sname="+val2+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_managevariables.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function get_dtddinfo(val,val2,div){
 var ajaxRequest = ajaxFunction(div);
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=mvdi&mvd=dt&ddname="+val+"&sname="+val2+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_managevariables.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function get_ssr(val,div){
 var ajaxRequest = ajaxFunction(div);
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=ssr&sname="+val+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_manageresources.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function get_scert(val,div){
 var ajaxRequest = ajaxFunction(div);
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=cd&sname="+val+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_certification.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function get_ssr_info(val,val2,div){
 var ajaxRequest = ajaxFunction(div);
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=ssri&ssr="+val+"&sname="+val2+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_manageresources.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function get_stinfo(val,div){
 var ajaxRequest = ajaxFunction(div);
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=sti&stname="+val+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_manageresources.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function get_sp(val,div){
 var ajaxRequest = ajaxFunction(div);
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=npi&sname="+val+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_manageprojects.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function get_srvinfo(val,div){
 var ajaxRequest = ajaxFunction(div);
 var date = new Date();
 var timestamp = date.getTime();
 var sname = document.getElementById("sname").value;
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=srvi&srvport="+val+"&sname="+sname+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_manageresources.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function get_rsinfo(val,div){
 var ajaxRequest = ajaxFunction(div);
 var date = new Date();
 var timestamp = date.getTime();
 var sname = document.getElementById("sname").value;
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=rsi&rsname="+val+"&sname="+sname+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_manageresources.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function get_pinfo(val,div){
 var ajaxRequest = ajaxFunction(div);
 var date = new Date();
 var timestamp = date.getTime();
 var sname = document.getElementById("sname").value;
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=pi&pname="+val+"&sname="+sname+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_manageprojects.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function get_vtype(val,div,val2){
 var ajaxRequest = ajaxFunction(div,1);
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=vt&vtype="+val+"&ftype="+val2+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_managevariables.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null);
 }

function adduprem_studyu(formname,val) {
 var form = document.getElementById(formname);
 var el = document.createElement("input");
 el.type = "hidden";
 el.name = "uprem";
 el.value = val;
 form.appendChild(el);
 wopen('newwindow',300,300);
 form.target = 'newwindow';
 form.submit();
 setTimeout(new_study,2000);
 }

function get_submit_u(val,div){
 var ajaxRequest = ajaxFunction(div);
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=ru&uname="+val+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_manageusers.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function get_submit_s(val,div){
 var ajaxRequest = ajaxFunction(div);
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=rs&sname="+val+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_managestudies.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function get_submit_m(val,div,s){
 var ajaxRequest = ajaxFunction(div);
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=rm&mname="+val+"&sname="+s+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_managevariables.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function get_submit_v(val,div,s){
 var ajaxRequest = ajaxFunction(div);
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=rv&vname="+val+"&sname="+s+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_managevariables.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function get_submit_dt(val,div,s){
 var ajaxRequest = ajaxFunction(div);
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=rdt&dtname="+val+"&sname="+s+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_managevariables.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function get_submit_dd(val,div,s){
 var ajaxRequest = ajaxFunction(div);
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=rdd&ddname="+val+"&sname="+s+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_managevariables.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function get_submit_st(val,div,s){
 var ajaxRequest = ajaxFunction(div);
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=rst&stname="+val+"&sname="+s+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_manageresources.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function get_submit_srv(val,div,s){
 var ajaxRequest = ajaxFunction(div);
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=rsrv&srvport="+val+"&sname="+s+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_manageresources.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function get_submit_rs(val,div,s){
 var ajaxRequest = ajaxFunction(div);
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=rrs&rsname="+val+"&sname="+s+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_manageresources.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function get_submit_p(val,div,s){
 var ajaxRequest = ajaxFunction(div);
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=rp&pname="+val+"&sname="+s+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_manageprojects.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function checku(val,div){
 var ajaxRequest = ajaxFunction(div,1);
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=cu&uname="+val+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_manageusers.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function changeverrun(ver,proj){
 var ajaxRequest = ajaxFunction('verdiv');
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?ver="+ver+"&proj="+proj+"&type=cvr&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_project.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null);
 }

function new_study(){
 var ajaxRequest = ajaxFunction('runres');
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=ns&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_managestudies.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null);
 }

function checks(val,div){
 var ajaxRequest = ajaxFunction(div,1);
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=cs&sname="+val+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_managestudies.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function checkm(val,div){
 var ajaxRequest = ajaxFunction(div,1);
 var date = new Date();
 var timestamp = date.getTime();
 var sname = document.getElementById('sname').value;
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=cm&sname="+sname+"&mname="+val+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_managevariables.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function checkv(val,div){
 var ajaxRequest = ajaxFunction(div,1);
 var date = new Date();
 var timestamp = date.getTime();
 var sname = document.getElementById('sname').value;
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=cv&sname="+sname+"&vname="+val+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_managevariables.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function checkdt(val,div){
 var ajaxRequest = ajaxFunction(div,1);
 var date = new Date();
 var timestamp = date.getTime();
 var sname = document.getElementById('sname').value;
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=cdt&sname="+sname+"&dtname="+val+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_managevariables.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function checkdd(val,div){
 var ajaxRequest = ajaxFunction(div,1);
 var date = new Date();
 var timestamp = date.getTime();
 var sname = document.getElementById('sname').value;
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=cdd&sname="+sname+"&ddname="+val+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_managevariables.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

// Checks for duplicate site shortnames in manageresources.cgi
function checkst(val,div){
 var ajaxRequest = ajaxFunction(div,1);
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=cst&stname="+val+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_manageresources.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

// Converts Country to 3 letter code shortnames in manageresources.cgi
function c2c(val,div){
 var ajaxRequest = ajaxFunction(div,1);
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=c2c&ctname="+val+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_manageresources.cgi'+query, false);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

// Checks for duplicate ports in manageresources.cgi
function checksrv(val,div){
 var ajaxRequest = ajaxFunction(div,1);
 var date = new Date();
 var timestamp = date.getTime();
 var sname = document.getElementById('sname').value;
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=csrv&sname="+sname+"&srvport="+val+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_manageresources.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

// Checks for duplicate resources in manageresources.cgi
function checkrs(val,div){
 var ajaxRequest = ajaxFunction(div,1);
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=crs&rsname="+val+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_manageresources.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

// Checks for duplicate project names in manageprojects.cgi
function checkproj(val,div){
 var ajaxRequest = ajaxFunction(div,1);
 var date = new Date();
 var timestamp = date.getTime();
 // use the ajaxRequest object to actually post something to the server
 var query = "?type=cp&pname="+val+"&time="+timestamp;
 ajaxRequest.open('GET', '/viparcgi/vipar_manageprojects.cgi'+query, true);
 ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
 ajaxRequest.send(null); 
 }

function search(proj){
 var term = document.getElementById('search').value;
 //if (term == ""){
 // alert("Please enter a search term(s) into the box provided");
 // return false;
 // }
 //else { 
  var ajaxRequest = ajaxFunction('fileman');
  var date = new Date();
  var timestamp = date.getTime();
  document.getElementById('files').innerHTML = "";
  // use the ajaxRequest object to actually post something to the server
  var query = "?proj="+proj+"&search="+term+"&type=s&time="+timestamp;
  ajaxRequest.open('GET', '/viparcgi/vipar_project.cgi'+query, true);
  ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
  ajaxRequest.send(null);
 // }
 }

function message(user,proj){
 var mes = document.getElementById('message').value;
 if (mes == ""){
  alert("Please enter a message into the box provided");
   return false;	
  }
 else { 
 var ajaxRequest = ajaxFunction('fileman');
  var date = new Date();
  var timestamp = date.getTime();
  var query = "?proj="+proj+"&message="+mes+"&type=addm&rtime="+timestamp;
  ajaxRequest.open('GET', '/viparcgi/vipar_project.cgi'+query, true);
  ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
  ajaxRequest.send(null);

 }
}

// Changed by RF on 28/05/13
// This function used to be used for Select All
// However it uses the name of the checkbox group rather than the id
// Therefore it doesn't work for the management interface as both the new and update checkbox groups have the same name
//function sa(saobj,sid){
// var saval = saobj.checked;
// var sobj = document.getElementsByName(sid);
// for (i = 0; i < sobj.length; i++){
//  sobj[i].checked = saval;
//  }
// }

function sa(saobj,fid,sid){
 var saval = saobj.checked;
 var fobj = document.getElementById(fid);
 var vobj = fobj.elements[sid];
 for (i = 0; i < vobj.length; i++){
  if (vobj[i].disabled == false){
   vobj[i].checked = saval;
   }
  }
 }

function wopen(name, w, h){
 w += 32;
 h += 96;
 var wleft = (screen.width - w) / 2;
 var wtop = (screen.height - h) / 2;
 if (wleft < 0) {
  w = screen.width;
  wleft = 0;
  }
 if (wtop < 0) {
  h = screen.height;
  wtop = 0;
  }
 var win = window.open('',name,'width='+w+',height='+h+','+'left='+wleft+',top='+wtop+','+'location=no,menubar=no,status=no,toolbar=no,scrollbars=yes');
 win.resizeTo(w, h);
 win.moveTo(wleft, wtop);
 win.focus();
 }

function upfile(p,rd,rt){
 document.uploadfile.submit();
 }

function uplib(p,l){
 document.uploadfile.submit();
 }

function reset_pass() {
 document.getElementById('passwordupuser').value = document.getElementById('password_orig').value;
 }

function blank_date(val){
 var obj = document.getElementById(val);
 if (obj.value == "YYYY-MM-DD"){
  obj.value = "";
  }
 else if (obj.value == ""){
  obj.value = "YYYY-MM-DD";
  }
 }

function check_user(val) {

 // submit needs to be positive
 if ((document.getElementById('csubmit').value == 0) && (val == "newuser")){
  document.getElementById('checku').innerHTML = "<span class=\"warn\">Please fix username</span><input type=\"hidden\" name=\"csubmit\" value=\"0\" id=\"csubmit\" />";
  return false;
  }
 // all fields must have something in them
 var warning = "";
 if (document.getElementById("uname"+val).value == ""){
  warning = warning + "Username cannot be blank\n";
  }
 // uname must not equal 0
 if (document.getElementById("uname"+val).value == 0){
  warning = warning + "Please select a username from the list\n";
  }

 if (val != "remuser"){ 
  if (document.getElementById("email"+val).value == ""){
   warning = warning + "Email cannot be blank\n";
   }
  if (document.getElementById("password"+val).value == ""){
   warning = warning + "Password cannot be blank\n";
   }
  }

 if (warning == ""){
  var form = document.getElementById(val);
  wopen('newwindow',300,300);
  form.target = 'newwindow';
  form.submit();
  setTimeout(new_user,2000);
  return true;
  }
 else {
  alert(warning);
  return false;
  }
 
 }

function check_study(val) {

 // submit needs to be positive
 if ((document.getElementById('csubmit').value == 0) && (val == "newstudy")){
  document.getElementById('checks').innerHTML = "<span class=\"warn\">Please fix studyname</span><input type=\"hidden\" name=\"csubmit\" value=\"0\" id=\"csubmit\" />";
  return false;
  }

 // all fields must have something in them
 var warning = "";
 if (val != "remstudy"){
  if (document.getElementById("sdesc"+val).value == ""){
   warning = warning + "Description cannot be blank\n";
   }
  }

 if (warning == ""){
  var form = document.getElementById(val);
  wopen('newwindow',300,300);
  form.target = 'newwindow';
  form.submit();
  setTimeout(new_study,2000);
  return true;
  }
 else { 
  alert(warning);
  return false;
  }
 }

function check_mis(val) {

 // submit needs to be positive
 if ((document.getElementById('csubmit').value == 0) && (val == "newmis")){
  document.getElementById('checkm').innerHTML = "<span class=\"warn\">Please fix missing value</span><input type=\"hidden\" name=\"csubmit\" value=\"0\" id=\"csubmit\" />";
  return false;
  }

 var form = document.getElementById(val);
 wopen('newwindow',300,300);
 form.target = 'newwindow';
 form.submit();
 setTimeout(new_vardd,2000);
 return true;
 }

function check_var(val) {

 // submit needs to be positive
 if ((document.getElementById('csubmit').value == 0) && (val == "newvar")){
  document.getElementById('checkv').innerHTML = "<span class=\"warn\">Please fix variable name</span><input type=\"hidden\" name=\"csubmit\" value=\"0\" id=\"csubmit\" />";
  return false;
  }
 // all fields must have something in them
 var warning = "";
 if (document.getElementById("vname"+val).value == ""){
  warning = warning + "Variable name cannot be blank\n";
  }
 // vname must not equal 0
 if (document.getElementById("vname"+val).value == 0){
  warning = warning + "Please select a variable from the list\n";
  }

 if (val != "remvar"){ 
  if (document.getElementById("vtype"+val).value == 0){
   warning = warning + "Please select a data type from the list\n";
   }
  else {
   var vt = document.getElementById("vtype"+val).value;
   if ((vt == 2) || (vt == 3)){ // continuous or date
    if (document.getElementById("vt_min"+val).value == ""){
     warning = warning + "The min value cannot be blank\n";
     }
    if (document.getElementById("vt_max"+val).value == ""){
     warning = warning + "The max value cannot be blank\n";
     }
    }
   if (vt == 1){ // categorical
    var vt_minval = document.getElementById("vt_min"+val).value;
    if (vt_minval == ""){
     warning = warning + "Please provide the required categories for this variable\n";
     }
    // check that each looks like what we are expecting
    var patt=/^\d+=".+"$/;
    var vt_minval2 = vt_minval.replace(/",/g,"\"\"\,");
    vt_minval2 = vt_minval2.replace(/\n/g,"");
    vt_mins = vt_minval2.split("\",");
    for(i=0; i<vt_mins.length; i++) {
     if (!patt.test(vt_mins[i])){
      warning = warning + "Your category "+vt_mins[i]+" is not defined properly\n";
      }
     }
    }
   if (vt == 3){ // date
    var patt=/\d\d\d\d-\d\d-\d\d/;
    if ( ! patt.test(document.getElementById("vt_min"+val).value) ){
     warning = warning + "Please add a valid from date in the correct format\n";
     }
    if ( ! patt.test(document.getElementById("vt_max"+val).value) ){
     warning = warning + "Please add a valid to date in the correct format\n";
     }
    }
   }
  }
 
 if (warning == ""){
  var form = document.getElementById(val);
  wopen('newwindow',300,300);
  form.target = 'newwindow';
  form.submit();
  setTimeout(new_vardd,2000);
  return true;
  }
 else {
  alert(warning);
  return false;
  }
 }

function check_dt(val) {

 // submit needs to be positive
 if ((document.getElementById('csubmit').value == 0) && (val == "newdt")){
  document.getElementById('checkdt').innerHTML = "<span class=\"warn\">Please fix name</span><input type=\"hidden\" name=\"csubmit\" value=\"0\" id=\"csubmit\" />";
  return false;
  }
 // all fields must have something in them
 var warning = "";
 if (val != "remdt"){
  if (document.getElementById("dtname"+val).value == ""){
   warning = warning + "Name cannot be blank\n";
   }
  }

// Will need to check that at least one variable is added to the data dictionary

 if (warning == ""){
  var form = document.getElementById(val);
  wopen('newwindow',300,300);
  form.target = 'newwindow';
  form.submit();
  setTimeout(new_vardd,2000);
  return true;
  }
 else {
  alert(warning);
  return false;
  }

 }

function check_dd(val) {

 // submit needs to be positive
 if ((document.getElementById('csubmit').value == 0) && (val == "newdd")){
  document.getElementById('checkdd').innerHTML = "<span class=\"warn\">Please fix version</span><input type=\"hidden\" name=\"csubmit\" value=\"0\" id=\"csubmit\" />";
  return false;
  }
 // all fields must have something in them
 var warning = "";
 if (val != "remdd"){
  if (document.getElementById("ddname"+val).value == ""){
   warning = warning + "Version cannot be blank\n";
   }
  // ddname must not equal 0
  if (document.getElementById("ddname"+val).value <= 0){
   warning = warning + "Version must be greater than 0\n";
   }
  if (document.getElementById("dddate"+val)){
   if (document.getElementById("dddate"+val).value == ""){
    warning = warning + "Date cannot be blank\n";
    }
   }
  }

// Will need to check that at least one variable is added to the data dictionary

/* if ((val == "upuser")||(val == "newuser")){
  if (document.getElementById("email"+val).value == ""){
   warning = warning + "Email cannot be blank\n";
   }
  if (document.getElementById("password"+val).value == ""){
   warning = warning + "Password cannot be blank\n";
   }
  }*/

 if (warning == ""){
  var form = document.getElementById(val);
  wopen('newwindow',300,300);
  form.target = 'newwindow';
  form.submit();
  setTimeout(new_vardd,2000);
  return true;
  }
 else {
  alert(warning);
  return false;
  }

 }

function check_st(val) {

 // submit needs to be positive
 if ((document.getElementById('csubmit').value == 0) && (val == "newst")){
  document.getElementById('cstdiv').innerHTML = "<span class=\"warn\">Please fix site name</span><input type=\"hidden\" name=\"csubmit\" value=\"0\" id=\"csubmit\" />";
  return false;
  }
 // all fields must have something in them
 var warning = "";
 if (val != "remst"){
  if (document.getElementById("stinst"+val).value == ""){
   warning = warning + "Institution cannot be blank\n";
   }
  // ctname must not equal 0
  if (document.getElementById("ctname"+val).value <= 0){
   warning = warning + "You must select a Country\n";
   }
  }

 if (warning == ""){
  var form = document.getElementById(val);
  wopen('newwindow',300,300);
  form.target = 'newwindow';
  form.submit();
  setTimeout(new_res,2000);
  return true;
  }
 else {
  alert(warning);
  return false;
  }
 }

function check_srv(val) {

 // submit needs to be positive
 if ((document.getElementById('csubmit').value == 0) && (val == "newsrv")){
  document.getElementById('csrvdiv').innerHTML = "<span class=\"warn\">Please fix port number</span><input type=\"hidden\" name=\"csubmit\" value=\"0\" id=\"csubmit\" />";
  return false;
  }
 // all fields must have something in them
 var warning = "";
 if (val != "remsrv"){
  if (document.getElementById("srvport"+val).value == ""){
   warning = warning + "Port cannot be blank\n";
   }
  // stname must not equal 0
  if (document.getElementById("stname"+val).value <= 0){
   warning = warning + "You must select a Site\n";
   }
  if (document.getElementById("rhost"+val).value == ""){
   warning = warning + "You must enter a Remote Host\n";
   }
  if (document.getElementById("rport"+val).value == ""){
   warning = warning + "You must enter a Remote Port\n";
   }
  if (isNaN(document.getElementById("rport"+val).value)){
   warning = warning + "Remote Port must be a number\n";
   }
  if (document.getElementById("ruser"+val).value == ""){
   warning = warning + "You must enter a Remote User\n";
   }
  }

 if (warning == ""){
  var form = document.getElementById(val);
  wopen('newwindow',300,300);
  form.target = 'newwindow';
  form.submit();
  setTimeout(new_res,2000);
  return true;
  }
 else {
  alert(warning);
  return false;
  }
 }

function check_rs(val) {

 // submit needs to be positive
 if ((document.getElementById('csubmit').value == 0) && (val == "newrs")){
  document.getElementById('crsdiv').innerHTML = "<span class=\"warn\">Please fix resource name</span><input type=\"hidden\" name=\"csubmit\" value=\"0\" id=\"csubmit\" />";
  return false;
  }
 // all fields must have something in them
 var warning = "";
 if (val != "remrs"){
  if (document.getElementById("rsname"+val).value == ""){
   warning = warning + "Resource name cannot be blank\n";
   }
  // srvport must not equal 0
  if (document.getElementById("srvport"+val).value <= 0){
   warning = warning + "You must select a Server\n";
   }
  // ddname must not equal 0
  if (document.getElementById("ddname"+val).value <= 0){
   warning = warning + "You must select a Data Dictionary\n";
   }
  }

 if (warning == ""){
  var form = document.getElementById(val);
  wopen('newwindow',300,300);
  form.target = 'newwindow';
  form.submit();
  setTimeout(new_res,2000);
  return true;
  }
 else {
  alert(warning);
  return false;
  }
 }

function check_proj(val) {

 // submit needs to be positive
 if ((document.getElementById('csubmit').value == 0) && (val == "newproj")){
  document.getElementById('cprojdiv').innerHTML = "<span class=\"warn\">Please fix project name</span><input type=\"hidden\" name=\"csubmit\" value=\"0\" id=\"csubmit\" />";
  return false;
  }
 // all fields must have something in them
 var warning = "";
 if (val != "remproj"){
  if (document.getElementById("pname"+val).value == ""){
   warning = warning + "Project name cannot be blank\n";
   }
  // short description should exist
  if (document.getElementById("psdesc"+val).value <= 0){
   warning = warning + "You must provide a short description\n";
   }
  // at least one variable must be selected
  var fobj = document.getElementById(val);
  var vobj = fobj.elements['variable'];
  var vcheck = false;
  for (i = 0; i < vobj.length; i++){
   if (vobj[i].checked){ vcheck = true; }
   }
  if (!vcheck){
   warning = warning + "You must select at least one variable\n";
   }
  // at least one user must be selected
  var uobj = document.getElementById("unamea"+val);
  var ucheck = false;
  for (i = 0; i < uobj.options.length; i++){
   if (uobj.options[i].selected){ ucheck = true; }
   }
  if (!ucheck){
   warning = warning + "You must select at least one analyst user\n";
   }
  // make sure the guest users aren't the same as the analyst users
  var uobja = document.getElementById("unamea"+val);
  var uobjg = document.getElementById("unameg"+val);
  var ucheckag = false;
  for (i = 0; i < uobja.options.length; i++){
   if ((uobja.options[i].selected) && (uobjg.options[i].selected)){ ucheckag = true; }
   }
  if (ucheckag){
   warning = warning + "You have the same user(s) in your analysts and guests\n";
   }
  

  }

 if (warning == ""){
  var form = document.getElementById(val);
  wopen('newwindow',300,300);
  form.target = 'newwindow';
  form.submit();
  setTimeout(new_proj,2000);
  return true;
  }
 else {
  alert(warning);
  return false;
  }
 }


function rs_syntax(val) {
 var warning = "";
 if (document.getElementById("rsnamerssyn").value == 0){
  warning = warning + "You must select a Resource\n";
  }

 if (warning == ""){
  var form = document.getElementById(val);
  wopen('newwindow',300,300);
  form.target = 'newwindow';
  form.submit();
  setTimeout(new_res,2000);
  return true;
  }
 else {
  alert(warning);
  return false;
  }
 }

function x_syntax(val) {
 var warning = "";
 if (document.getElementById("srvportxsyn").value == 0){
  warning = warning + "You must select a Server\n";
  }

 if (warning == ""){
  var form = document.getElementById(val);
  wopen('newwindow',300,300);
  form.target = 'newwindow';
  form.submit();
  setTimeout(new_res,2000);
  return true;
  }
 else {
  alert(warning);
  return false;
  }
 }

/*
useful code for using a button to post to a new window
  var form = document.getElementById(val);
  wopen('newwindow',800,500);
  form.target = 'newwindow';
  form.submit();
*/


function stopruntime(proj,runtime,rundate){
 var yorn = confirm("Are you sure you want to stop this run?\n\nNote that all files are still retained on the server");
 if (yorn){
  var ajaxRequest = ajaxFunction('fileman');
  var date = new Date();
  var timestamp = date.getTime();
  // use the ajaxRequest object to actually post something to the server
  var query = "?proj="+proj+"&rtime="+runtime+"&type=srt&time="+timestamp;
  ajaxRequest.open('GET', '/viparcgi/vipar_project.cgi'+query, false);
  ajaxRequest.setRequestHeader("Cache-Control","no-cache, private, max-age=0");
  ajaxRequest.send(null);
  getprojruntimes(proj,rundate);
  }
 else {
  getprojruntimes(proj,rundate);
  return false;
  }
 }

function limchar(obj) {
var id = obj.id + "lim";
var len = obj.value.length;
var mlen = obj.maxLength;
var count = mlen - len;
document.getElementById(id).value = count;
}

function statsinfo(cur) {
$('#statwrap').children().hide();
$("#"+cur+"_info").show();
$("#"+cur+"_info").css('visibility', 'visible');
}
