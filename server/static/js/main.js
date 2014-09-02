var app = angular.module('okpy', ['ngResource', 'ui.router']);
// TODO https://github.com/chieffancypants/angular-loading-bar
// http://ngmodules.org/modules/MacGyver
// https://github.com/localytics/angular-chosen

app.config(['$stateProvider', '$urlRouterProvider',
  function($stateProvider, $urlRouterProvider, $locationProvider) {
    $urlRouterProvider.otherwise("/submission/");

    var submissions = {
      name: 'submission',
      abstract: true,
      url: '/submission',
      templateUrl: 'static/partials/submission.base.html',
    }

    var submissionList = {
      name: 'submission.list',
      url: '/',
      templateUrl: 'static/partials/submission.list.html',
      controller: "SubmissionListCtrl"
    }

    var submissionDetail = {
      name: 'submission.detail',
      url: '/:submissionId',
      templateUrl: 'static/partials/submission.detail.html',
      controller: "SubmissionDetailCtrl"
    }

    var assignments = {
      name: 'assignment',
      abstract: true,
      url: '/assignment',
      templateUrl: 'static/partials/assignment.base.html',
    }

    var assignmentList = {
      name: 'assignment.list',
      url: '/',
      templateUrl: 'static/partials/assignment.list.html',
      controller: "AssignmentListCtrl"
    }

    var assignmentDetail = {
      name: 'assignment.detail',
      url: '/:assignmentId',
      templateUrl: 'static/partials/assignment.detail.html',
      controller: "AssignmentDetailCtrl"
    }

    $stateProvider.
      state(submissions).
      state(submissionList).
      state(submissionDetail).
      state(assignments).
      state(assignmentList).
      state(assignmentDetail)
      ;
  }]);

app.factory('Submission', ['$resource',
    function($resource) {
      return $resource('api/v1/submission', {format: "json"}, {
        query: {
          isArray: true,
          transformResponse: function(data) {
            return JSON.parse(data).data.results;
          }
        },
        get: {
          isArray: false,
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        }
      });
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
      return $resource('api/v1/assignment/:id', {
        format: "json",
      }, {
        query: {
          isArray: true,
          transformResponse: function(data) {
            return JSON.parse(data).data.results;
          }
        },
        get: {
          isArray: false,
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        }
      });
    }
  ]);

function transformSubmission(data) {
  data.submitter_s = function() {
    return data.submitter || "Anonymous";
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
