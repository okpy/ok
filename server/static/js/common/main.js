app.directive('snippet', function() {
        "use strict";
        return {
            restrict: 'E',
            templateUrl: '/static/partials/common/snippet.html',
            link: function(scope, elem, attrs) {
              scope.contents = scope.contents.split('\n');
            }
        };
    });

app.directive('diff', function() {
        "use strict";
        return {
            restrict: 'E',
            templateUrl: '/static/partials/common/diff.html',
        };
    });

app.directive('group', function() {
        "use strict";
        return {
            restrict: 'E',
            templateUrl: '/static/partials/common/group.html',
        };
    });

app.directive('comments', function() {
        "use strict";
        return {
            scope: false,
            restrict: 'E',
            templateUrl: '/static/partials/common/comment-viewer.html',
        };
    });

app.directive('datatableSetup', function () {
    return { link: function (scope, elm, attrs) { console.log(Sortable.init());  } }
});
