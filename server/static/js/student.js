jQuery(document).ready(function($){
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
