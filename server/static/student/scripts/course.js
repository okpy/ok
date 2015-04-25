$(document).ready(function() {

    $('.flip').on('click',function() {
        $('.blob-more').removeClass('flipped');
    });
    $('.blob-action').on('click',function() {
        console.log("GOTCHA")
//        $('.flip').click();
//        $(this).parent().parent().children('.blob-more').addClass('flipped');
        openDetails($(this));
    });
    $('.sidebars .close').on('click',function() {
        closeDetails();
    });
    $('.cover').on('click',function() {
        $('.sidebars .close').click();
    });
});

function openDetails(element) {
    $('.wrap-container').addClass('active');
    var blob = $(element).parent();
    $('.sidebar').attr('color', blob.attr('color'));
}

function closeDetails() {
    $('.wrap-container').removeClass('active');
}