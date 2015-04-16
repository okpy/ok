$(document).ready(function() {
    $('.flip').on('click',function() {
        $('.blob-more').removeClass('flipped');
    });
    $('.blob-action').on('click',function() {
//        $('.flip').click();
//        $(this).parent().parent().children('.blob-more').addClass('flipped');
        $('.container-fluid').addClass('active');
        var blob = $(this).parent();
        $('.sidebar').attr('color', blob.attr('color'));
    });
    $('.sidebars .close').on('click',function() {
        $('.container-fluid').removeClass('active');
    });
    $('.cover').on('click',function() {
        $('.sidebars .close').click();
    });
});