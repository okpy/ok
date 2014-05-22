$(window).load(function() {
    $("button").click(function(evt){
    	$(evt.target).siblings().closest(".solution").slideToggle('hide');
    });
});