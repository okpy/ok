app.directive('snippet', function() {
        "use strict";
        return {
            restrict: 'E',
            templateUrl: 'static/partials/snippet.html',
            link: function(scope, elem, attrs) {
              scope.contents = scope.contents.split('\n');
            }
        };
    });

app.directive('diff', function() {
        "use strict";
        return {
            restrict: 'E',
            templateUrl: 'static/partials/diff.html',
        };
    });

app.directive('group', function() {
        "use strict";
        return {
            restrict: 'E',
            templateUrl: 'static/partials/group.html',
        };
    });

app.directive('comments', function() {
        "use strict";
        return {
            scope: false,
            restrict: 'E',
            templateUrl: 'static/partials/comment-viewer.html',
        };
    });

