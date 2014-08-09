var app = angular.module('okpy', ['ngResource', 'ui.router']);
// TODO https://github.com/chieffancypants/angular-loading-bar

app.config(['$stateProvider', '$urlRouterProvider', '$locationProvider',
  function($stateProvider, $urlRouterProvider, $locationProvider, Restangular) {
    $urlRouterProvider.otherwise("/submission");
    
    var submissions = { 
      name: 'submission',
      url: '/submission',
      templateUrl: 'static/partials/submission_list.html',
      controller: "SubmissionListCtrl"
    }

    var submissionsDetail = { 
      name: 'submission.detail', 
      url: '/submission/{submissionId}',
      parent: submissions,
      templateUrl: 'static/partials/submission_detail.html',
      controller: "SubmissionDetailCtrl"
    }

    var assignments = {
      abstract: true,
      name: 'assignment',
      url: '/assignment',
      templateUrl: 'static/partials/assignment_base.html',
      controller: "AssignmentListCtrl"
    }

    var assignmentDetail = {
      name: 'assignment.list',
      url: '',
      templateUrl: 'static/partials/assignment_list.html',
      controller: "AssignmentDetailCtrl"
    }

    var assignmentDetail = {
      name: 'assignment.detail',
      url: '/:assignmentId',
      templateUrl: 'static/partials/assignment_detail.html',
      controller: "AssignmentDetailCtrl"
    }

    $stateProvider.
      state(submissions).
      state(submissionsDetail).
      state(assignmentDetail).
      state(assignments)
      ;
  }]);

app.factory('Submission', ['$resource',
    function($resource) {
      return $resource('api/v1/submission', {format: "raw"});
    }
  ]);

app.controller("SubmissionListCtrl", ['$scope', 'Submission',
  function($scope, Submission) {
    $scope.submissions = Submission.query()
  }]);

app.controller("SubmissionDetailCtrl", ['$scope', '$stateParams',  'Submission',
  function($scope, $stateParams, Submission) {
    $scope.submission = Submission.get({id: $stateParams.submissionId});
  }]);

app.factory('Assignment', ['$resource',
    function($resource) {
      return $resource('api/v1/assignment', {format: "raw"});
    }
  ]);

app.controller("AssignmentListCtrl", ['$scope', 'Assignment',
  function($scope, Assignment) {
    $scope.assignments = Assignment.query()
  }]);

app.controller("AssignmentDetailCtrl", ["$scope", "$stateParams", "Assignment",
    function ($scope, $stateParams, Assignment) {
      $scope.submission = Assignment.get({id: $stateParams.assignmentId});
    }
  ]);


