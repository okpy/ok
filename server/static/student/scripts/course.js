$(document).ready(function() {
    $('.flip').on('click',function() {
        $(this).parent().parent().removeClass('flipped');
    });
    $('.blob-action').on('click',function() {
        $(this).parent().parent().children('.blob-more').addClass('flipped');
    });
});