
window.paceOptions = {
  startOnPageLoad: false,
  ajax: true,
  document: false, // disabled
  eventLag: false // disabled
};
var tnow = moment();

jQuery(document).ready(function($){

    $('time').each(function(i, e) {
        var time = moment($(e).attr('datetime'));
        var localTime  = moment.utc(time);
        $(e).html(time.format('MM/DD h:m A'));
    });
    $('timefromnow').each(function(i, e) {
        var due = moment($(e).attr('datetime'));
        var localTime  = moment.utc(due);
        var diff = moment.duration(due.diff(tnow)).humanize()
        $(e).html(diff);
    });

});
