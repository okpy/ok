window.paceOptions = {
  startOnPageLoad: false,
  ajax: {
    trackMethods: ['GET', 'POST', 'DELETE', 'PUT'],
    trackWebSockets: true,
    ignoreURLs: []
  },
  restartOnPushState: false,
  eventLag: false // disabled
};

if (typeof HTMLElement.prototype.removeClass !== "function") {
    HTMLElement.prototype.removeClass = function(remove) {
        var newClassName = "";
        var i;
        var classes = this.className.split(" ");
        for(i = 0; i < classes.length; i++) {
            if(classes[i] !== remove) {
                newClassName += classes[i] + " ";
            }
        }
        this.className = newClassName;
    }
}

$('body').on('click', 'button[data-confirm]', function(e) {
  e.preventDefault();

  var form = $(this).parents('form');
  var confirmText = $(this).data('confirm');

  swal({
    title: confirmText,
    showCancelButton: true,
    confirmButtonText: "Yes, I'm sure!",
    closeOnConfirm: true
  }, function(isConfirm){
      if (isConfirm) form.submit();
  });
})

// From: http://davidwalsh.name/javascript-debounce-function
function debounce(func, wait, immediate) {
    var timeout;
    return function() {
        var context = this, args = arguments;
        var later = function() {
            timeout = null;
            if (!immediate) func.apply(context, args);
        };
        var callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func.apply(context, args);
    };
};
