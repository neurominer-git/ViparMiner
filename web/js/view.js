$(document).ready(function() {
$(document).contextmenu( function() {
    return false;
});
document.addEventListener("contextmenu", function(e){
    e.preventDefault();
}, false);
});
