$(document).ready(function() {

	// screens
	screens = 6

	$('.next-screen').on('click',function() {
		nextScreen(get_i());
	});

	$('.prev-screen').on('click',function() {
		prevScreen(get_i());
	});

	function nextScreen(i) {
		if (nextExists()) {
			i++;
			deselectScreen('prev');
			selectScreen(i);
			checkArrows();
		}
	}

	function prevScreen(i) {
		if (prevExists()) {
			i--;
			deselectScreen('next');
			selectScreen(i);
			checkArrows();
		}
	}

	function checkArrows() {
		if (!prevExists()) {
			hidePrev();
		} else {
			showPrev();
		}
		if (!nextExists()) {
			hideNext();
		} else {
			showNext();
		}
	}

	document.onkeydown = checkKey;

	function checkKey(e) {
    	e = e || window.event;
	    switch(e.keyCode) {
	    	case 37:
	    		prevScreen(get_i());
	    	break;
	    	case 39:
	    		nextScreen(get_i());
	    	break;
	    }
	}

	function deselectScreen(c) {
		$('.current').removeClass('current').addClass(c);
	}

	function selectScreen(i) {
		$('section[i="'+i+'"]').removeClass('next prev').addClass('current');
	}

	function hidePrev() {
		$('.arrow.left').addClass('hide');
	}

	function showPrev() {
		$('.arrow.left').removeClass('hide');
	}

	function hideNext() {
		$('.arrow.right').addClass('hide');
	}

	function showNext() {
		$('.arrow.right').removeClass('hide');
	}

	function nextExists() {
		return get_i() < screens ? true : false;
	}

	function prevExists() {
		return get_i() > 1 ? true : false;
	}

	function get_i() {
		return $('.current').attr('i');
	}

	checkArrows();

});
