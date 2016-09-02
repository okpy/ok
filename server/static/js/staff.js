function listIncreasePagination(list, amount) {
	if (list) {
		list.page += amount;
		list.update()
	}
}

// initialize datepicker
jQuery(document).ready(function($){
  // $('.datepicker').datetimepicker({
  // 	format:'YYYY-MM-DD hh:mm:ss',
  // });
});

