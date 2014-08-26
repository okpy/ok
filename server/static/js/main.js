var app = angular.module('okpy', ['ngResource', 'ui.router']);
// TODO https://github.com/chieffancypants/angular-loading-bar
// http://ngmodules.org/modules/MacGyver
// https://github.com/localytics/angular-chosen

app.config(['$stateProvider', '$urlRouterProvider',
  function($stateProvider, $urlRouterProvider, $locationProvider) {
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
      name: 'assignment',
      url: '/assignment',
      templateUrl: 'static/partials/assignment_base.html',
      controller: "AssignmentListCtrl"
    }

    var assignmentList = {
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
      state(assignmentList).
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
    $scope.submissions = Submission.query();
  }]);

app.controller("SubmissionDetailCtrl", ['$scope', '$stateParams',  'Submission',
  function($scope, $stateParams, Submission) {
    $scope.submission = Submission.get({id: $stateParams.submissionId});
  }]);

app.factory('Assignment', ['$resource',
    function($resource) {
      return $resource('api/v1/assignment/:id', {format: "raw"});
    }
  ]);

function transformSubmission(data) {
  var old_submitter = data.submitter;
  data.submitter_s = function() {
    return old_submitter || "anonymous";
  }
  return data;
}
app.config(['$httpProvider',
    function($httpProvider) {
      $httpProvider.interceptors.push(['$q',
        function($q) {
          return {
            response: function (response, a) {
              config = response.config;
              if (! (/^api\/v1/).test(config.url)) {
                return response;
              }
              url = config.url.slice(7);

              if (url !== "submission") {
                return response;
              }
              data = response.data;
              if (angular.isArray(data)) {
                console.log("hey");
                angular.forEach(data, transformSubmission);
              }
              else {
                data = transformSubmission(data);
              }
              response.data = data;
              return response;
            }
          }
        }]);
  }]);

app.controller("AssignmentListCtrl", ['$scope', 'Assignment',
  function($scope, Assignment) {
    $scope.assignments = Assignment.query();
  }]);

app.controller("AssignmentDetailCtrl", ["$scope", "$stateParams", "Assignment",
    function ($scope, $stateParams, Assignment) {
      $scope.assignment = Assignment.get({id: $stateParams.assignmentId});
    }
  ]);


app.filter('prettyDate', function() {
  return function(date) {
    return moment(date).format('MMMM Do YYYY, h:mm:ss a');
  }
});
