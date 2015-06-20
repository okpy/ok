app.directive('snippet', function() {
        "use strict";
        return {
            restrict: 'E',
            templateUrl: '/static/partials/common/snippet.html',
            link: function(scope, elem, attrs) {
                if (scope.contents) {
                  scope.contents = scope.contents.split('\n');
                }
            }
        };
    });

app.directive('diff', function() {
        "use strict";
        return {
            restrict: 'E',
            templateUrl: '/static/partials/admin/diff.html',
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
            templateUrl: '/static/partials/admin/comment-viewer.html',
        };
    });

app.directive('datatableSetup', function () {
    return { link: function (scope, elm, attrs) { console.log(Sortable.init());  } }
});
