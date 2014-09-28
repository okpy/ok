var app = angular.module('dashboard', ['ngResource', 'ui.router']);

app.directive('assignmentModule', function() {
        return {
            restrict: 'E',
            templateUrl: '/static/partials/dashboard/assignment.moduledash.html',
        };
    });

app.directive('assignmentList', function() {
        return {
            restrict: 'E',
            templateUrl: '/static/partials/dashboard/assign.list.html',
        };
    });

app.directive('submissionModule', function() {
        return {
            restrict: 'E',
            templateUrl: '/static/partials/dashboard/submission.module.html',
        };
    });

app.directive('submissionList', function() {
        return {
            restrict: 'E',
            templateUrl: '/static/partials/dashboard/submission.list.html',
        };
    });
