// <= IE8 Doesn't have indexOf. This patch isn't used currently.
var indexOf = function(needle) {
    if(typeof Array.prototype.indexOf === 'function') {
        indexOf = Array.prototype.indexOf;
    } else {
        indexOf = function(needle) {
            var i = -1, index = -1;

            for(i = 0; i < this.length; i++) {
                if(this[i] === needle) {
                    index = i;
                    break;
                }
            }

            return index;
        };
    }

    return indexOf.call(this, needle);
};

// Customize the time format.
moment.locale('en', {
    // customizations
    calendar : {
        lastDay : '[Yesterday at] LT',
        sameDay : '[Today at] LT',
        nextDay : '[Tomorrow at] LT',
        lastWeek : '[Last] dddd [at] LT',
        nextWeek : 'dddd [at] LT',
        sameElse : 'L [at] LT'
    }
});
