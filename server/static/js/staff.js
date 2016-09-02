// initialize datepicker
jQuery(document).ready(function($){
  // $('.datepicker').datetimepicker({
  // 	format:'YYYY-MM-DD hh:mm:ss',
  // });

  function updateName(){
    display_name = $('#display_name').val().toLowerCase().split(' ').join('')
    course_offering = $.trim($("#course_link").text())
    $('#name').val(course_offering + '/' + display_name)
  }
  $('#display_name').on('change, keyup', updateName)
});
