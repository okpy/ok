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

function showElem(selector) {
    if(!$(selector).is(':visible')) {
        $(selector).show();
    }
    $("html, body").animate({ scrollTop: $(selector).offset().top }, 500);
}

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

$('.datetime-picker').datetimepicker({
  format: 'YYYY-MM-DD HH:mm:ss',
  icons: {
	time: 'glyphicon glyphicon-time',
	date: 'glyphicon glyphicon-calendar',
	up: 'glyphicon glyphicon-chevron-up',
	down: 'glyphicon glyphicon-chevron-down',
	previous: 'glyphicon glyphicon-chevron-left',
	next: 'glyphicon glyphicon-chevron-right',
	today: 'glyphicon glyphicon-screenshot',
	clear: 'glyphicon glyphicon-trash',
	close: 'glyphicon glyphicon-remove'
  }
});
