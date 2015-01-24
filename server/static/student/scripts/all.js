$(document).ready(function() {

	// checkpoints
	// function onPageLoad() {
	// 	hideLoader()
	// 	checkForAlerts();
	//
	// 	// addSortable();
	// 	fixSortable();
	// }

	// loading functions

	// function loadGroup(id) {
	// 	// load group information - return first person name, second person name, assignment name, creation date
	// 	return ['Alvin Wan','Angie Jodjana','Ant Project','Jan. 16']
	// }

	// function loadMore(id) {
	// 	// load assignment information
	// }

	// function loadSubmissions(id) {
	// 	// load list of submissions for assignment - for each submission, return uploader, date, and ID
	// 	return [['scheme.py','code herEE']]
	// }

	// function loadSubmission(id) {
	// 	// load submission information - return grader, date, and code-file pairs
	// 	return []
	// }

	// function loadBackups(id) {
	// 	return []
	// }

	// // loader

	// function showLoader() {
	// 	$('.loader').removeClass('hide');
	// }

	// function hideLoader() {
	// 	$('.loader').addClass('done hide');
	// 	setTimeout(function() {
	// 		$('.loader').removeClass('done')
	// 	},800)
	// }

	// // alerts

	// function checkForAlerts() {
	// 	if (alertExists()) {
	// 		activateAlert();
	// 	}
	// }

	// $('.close').on('click',function() {
	// 	deactivateAlert();
	// })

	// function alertExists() {
	// 	return $('.alert').length != 0;
	// }

	// function activateAlert(color) {
	// 	color = typeof color != 'undefined' ? color : 'red';
	// 	$('.alert').removeClass('red green').addClass('active '+color);
	// 	setTimeout(deactivateAlert,5000);
	// }

	// function deactivateAlert() {
	// 	$('.alert').removeClass('active');
	// }

	// function notify(message,color) {
	// 	fields = ['alert-info'];
	// 	data = [message];
	// 	insertData(fields,data);
	// 	activateAlert(color);
	// }

	// // popups

	// $('.view-group').on('click',function() {
	// 	$(this).parents('.assign').addClass('s');
	// 	popup(popupGroup,$(this).attr('id'));
	// });

	// $('.view-submissions').on('click',function() {
	// 	$(this).parents('.assign').addClass('s');
	// 	popup(popupSubs,$(this).attr('id'));
	// });

	// $('.view-backups').on('click',function() {
	// 	$(this).parents('.assign').addClass('s');
	// 	popup(popupBackups,$(this).attr('id'));
	// })

	// $('.popup .close').on('click',function() {
	// 	hidePopups();
	// });

	// $('.popups').on('click',function() {
	// 	hidePopups();
	// })

	// function popup(func,id) {
	// 	showLoader();
	// 	func(id);
	// }

	// function popupGroup(id) {
	// 	data = loadGroup(id);
	// 	fields = ['first-member','second-member','assign-name','creation-date'];
	// 	insertData(fields,data);

	// 	showPopups('group');

	// 	// setTimeout(hideLoader,1000); // change to hideLoader() in production!
	// 	hideLoader();
	// }

	// function popupSubs(id) {
	// 	data = loadSubmissions(id);
	// 	fields = ['assign-name','creation-date'];
	// 	insertData(fields,data);

	// 	// add rows of new data

	// 	showPopups('submissions');

	// 	// setTimeout(hideLoader,1000); // change to hideLoader() in production!
	// 	hideLoader();
	// }

	// function popupBackups(id) {
	// 	data = loadBackups(id);
	// 	fields = ['assign-name','creation-date'];
	// 	insertData(fields,data);

	// 	// add rows of new data

	// 	showPopups('backups');

	// 	// setTimeout(hideLoader,1000); // change to hideLoader() in production!
	// 	hideLoader();
	// }

	// function showPopups(popup) {
	// 	$('.popups').addClass('active');
	// 	$('.popup').removeClass('active');
	// 	$('.popup.'+popup).addClass('active').removeClass('hide');
	// }

	// function hidePopups() {
	// 	$('.assign').removeClass('s');
	// 	$('.popups').removeClass('active');
	// 	$('.popup').removeClass('active');
	// 	setTimeout(function() {
	// 		$('.popup').addClass('hide');
	// 	},400);
	// }

	// function insertData(fields,data) {
	// 	for (i=0;i<fields.length;i++) {
	// 		$('.'+fields[i]).html(data[i]);
	// 	}
	// }

	// // function addSortable() {
	// // 	$( ".sortable" ).sortable();
	// // }

	// // assignment views

	// $('.view-submission').on('click',function() {
	// 	viewSubmission($(this).parent().attr('id'));
	// })

	// $('.assign-expand').on('click',function() {

	// 	parent = $(this).parent();
	// 	more = parent.find('.assign-more');
	// 	p = $(this).find('p');

	// 	more.toggleClass('active');
	// 	if (p.html() == 'Expand') {
	// 		if (more.html().length == 0) {
	// 			showMore(parent.attr('id'));
	// 		}
	// 		scrollto = parent.offset().top+$('.main').scrollTop();
	// 		$('.main').animate({scrollTop:scrollto}, 400);
	// 		p.html('Collapse');
	// 	} else {
	// 		p.html('Expand');
	// 	}
	// });

	// $('.block-back').on('click',function() {
	// 	updateAside();
	// 	updateSection();
	// })

	// function showMore(id) {
	// 	showLoader();

	// 	hideLoader();
	// }

	// function viewSubmission(id) {
	// 	showLoader();
	// 	hidePopups();
	// 	data = loadSubmission(id);

	// 	// setTimeout(function() {
	// 		hideLoader();
	// 		scrollToTop();
	// 		setTimeout(hideMores,400);
	// 		setTimeout(function() {
	// 			updateAside();
	// 			updateSection();
	// 		},800)
	// 	// },1000); // remove OUTER setTimeout wrapper in production!

	// }

	// function hideMores() {
	// 	$('.assign-more').removeClass('active');
	// 	$('.assign-expand p').html('Expand');
	// }

	// function updateAside() {
	// 	$('aside').toggleClass('new');
	// }

	// function updateSection() {
	// 	$('section').toggleClass('new');
	// }

	// function scrollToTop() {
	// 	$('.main').animate({scrollTop:0}, 400);

	// }

	// // code

	// $('.file').on('click',function() {
	// 	that = $(this);
	// 	selectFile(that);
	// 	viewFile(that);
	// });

	// function selectFile(that) {
	// 	showOnly('.file',that);
	// }

	// function viewFile(that) {
	// 	id = that.attr('id')
	// 	showOnly('code',$('code[id="'+id+'"]'));
	// 	showOnly('.comments-cont',$('.comments-cont[id="'+id+'"]'));
	// }

	// function showOnly(c,that) {
	// 	$(c).removeClass('active');
	// 	that.addClass('active');
	// }

	// // groups

	// $('.leave-group').on('click',function() {
	// 	hidePopups();
	// 	notify('<b>Confirmation</b> Left group successfully!','green');
	// });

	// $('.remove-user').on('click',function() {
	// 	hidePopups();
	// 	notify('<b>Success</b> Member "Johnny Appleseed" successfully removed from group. T_T','green')
	// });

	// $('.pop-item').on('mouseup',function() {
	// 	that = $(this)
	// 	setTimeout(function() {
	// 		renumber(that.parent());
	// 	},100);
	// });

	// function renumber(list) {
	// 	i = 0;
	// 	list.children('.pop-item:not(.ui-sortable-placeholder)').each(function() {
	// 		$(this).children('.item-no').html(i);
	// 		i++;
	// 	});
	// }

	// function fixSortable() {
	// 	$('.sortable').each(function() {
	// 		that = $(this)
	// 		children = that.children();
	// 		l = children.length;
	// 		h = that.children('*:first-child').height();
	// 		h = h > 0 ? h : 53;
	// 		that.css('min-height',h*l);
	// 		that.attr('number',l)
	// 	});
	// }

	// menu

	$('.show-menu').on('click',function() {
		showMenu();
	})

	$('.close-menu').on('click',function() {
		hideMenu();
	})

	$('.menu-cover').on('click',function() {
		hideMenu();
	})

	function showMenu() {
		$('.menu').addClass('active');
		$('.menu-cover').addClass('active');
		$('html').addClass('active');
	}

	function hideMenu() {
		$('.menu').removeClass('active');
		$('.menu-cover').removeClass('active');
		$('html').removeClass('active');
	}

	// onPageLoad();
})
