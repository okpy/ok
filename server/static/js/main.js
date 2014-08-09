var app = angular.module('okpy', ['ngResource', 'ngRoute']);

app.config(['$routeProvider',
  function($routeProvider) {
    $routeProvider.
      when('/', {
        templateUrl: 'static/partials/submissions_list.html',
        controller: 'SubmissionListCtrl'
      }).
      otherwise({
        redirectTo: '/'
      });
  }]);

app.factory("Submission", function($resource) {
  return $resource("/api/v1/submission/:id", {format: "raw"});
});

app.controller("SubmissionListCtrl", function($scope, Submission) {
  Submission.query(function (data) {
    console.log(data);
    console.log($scope);
    $scope.submissions = data;
  });
});


