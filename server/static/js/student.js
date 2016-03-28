jQuery(document).ready(function($){
    "use strict";

    /* CSRF protection. The csrf_token variable is set in the
     * 'student/base.html' template.
     */
    $(document).ajaxSend(function(e, xhr, s) {
        if (s.type == 'POST' || s.type == 'PUT') {
            xhr.setRequestHeader('X-CSRF-Token', csrf_token);
        }
    });

    $('.remove-confirm').on('click',function(e){
        e.preventDefault();
        var form = $(this).parents('form');
        var info = form[0][1].value;
        swal({
            title: "Just double checking",
            text: "Are you sure you want to remove " + info + " from the group?",
            showCancelButton: true,
            confirmButtonText: "Yes, I'm sure!",
            closeOnConfirm: true
        }, function(isConfirm){
            if (isConfirm) form.submit();
        });
    })

});
