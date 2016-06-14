function showElem(selector) {
    if(!$(selector).is(':visible')) {
        $(selector).show();
    }
    $("html, body").animate({ scrollTop: $(selector).offset().top }, 500);
}
