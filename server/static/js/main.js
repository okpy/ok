var app = angular.module('okpy', ['ngResource', 'ui.router', 'angular-loading-bar', 'ui.bootstrap', 'angularMoment']);

// http://ngmodules.org/modules/MacGyver

app.directive('snippet', ['$compile', '$location', '$anchorScroll', '$timeout', '$interpolate', function ($compile, $location, $anchorScroll, $timeout, $interpolate) {
        "use strict";
        return {
            restrict: 'E',
            template: '<table class="snippet" ng-transclude></table>',
            replace: true,
            transclude: true,
            link: function (scope, elm, attrs) {
              scope.scrollTo = function(id) {
                console.log("Scrolling to " + id);
                $location.hash(id);
                $anchorScroll();
              }
              var contents = $interpolate(elm.text())(scope).split('\n');
              elm.html("");

              var leftNum = 0;
              var rightNum = 0;
              for (var i = 0; i < contents.length; i++) {
                var content = contents[i];
                var id = attrs.name + "-L"+(i+1);
                var elem = $("<tr id='"+id+"' class='diff-line anchor'>")
                var lineNum = $("<td ng-click='scrollTo(\""+id+"\")' class='diff-line-num diff-line-num-left'>")
                lineNum.text(i + 1);
                var code = $("<td class='diff-line-code'>")
                var span = $("<span>")
                code.addClass('diff-line-code-empty')
                code.append(span);
                span.text(content);
                elem.append(lineNum);
                elem.append(code);
                elm.append(elem);
                hljs.highlightBlock(span[0]);
                $compile(elem)(scope);
              };
              $anchorScroll();
            }
        };
    }]);

app.directive('diff', ['$compile', '$timeout', '$location', '$anchorScroll', '$interpolate', function ($compile, $timeout, $location, $anchorScroll, $interpolate) {
        "use strict";
        return {
            restrict: 'E',
            template: '<table class="diff" ng-transclude></table>',
            replace: true,
            transclude: true,
            link: function (scope, elm, attrs) {

              scope.scrollTo = function(id) {
                console.log("Scrolling to " + id);
                $location.hash(id);
                $anchorScroll();
              }
              var contents = JSON.parse($interpolate(elm.text())(scope));
              elm.html("");

              var leftNum = 0;
              var rightNum = 0;
              for (var i = 0; i < contents.length; i++) {
                var val = contents[i];
                var start = val[0];
                var content = val[0] + val.slice(2);
                var id = attrs.name + "-L"+(i+1);
                var elem = $("<tr id='"+id+"' class='diff-line'>")
                var lineNumLeft = $("<td ng-click='scrollTo(\""+id+"\")' class='diff-line-num diff-line-num-left'>")
                var lineNumRight = $("<td ng-click='scrollTo(\""+id+"\")' class='diff-line-num diff-line-num-right'>")
                var code = $("<td class='diff-line-code'>")
                var showLeft = false;
                var showRight = false;
                if (start == " ") {
                  code.addClass('diff-line-code-empty')
                  showRight = true;
                  showLeft = true;
                } else if (start == "+") {
                  code.addClass('diff-line-code-pos')
                  lineNumRight.addClass('diff-line-num-pos')
                  lineNumLeft.addClass('diff-line-num-pos')
                  showRight = true;
                } else if (start == "-") {
                  code.addClass('diff-line-code-neg')
                  lineNumLeft.addClass('diff-line-num-neg')
                  lineNumRight.addClass('diff-line-num-neg')
                  showLeft = true;
                }
                if (showRight == true) {
                  rightNum++;
                  lineNumRight.text(rightNum);
                }
                if (showLeft == true) {
                  leftNum++;
                  lineNumLeft.text(leftNum);
                }
                code.text(content);
                elem.append(lineNumLeft);
                elem.append(lineNumRight);
                elem.append(code);
                elm.append(elem);
                $compile(elem)(scope);
              };
              $anchorScroll();
            }
        };
    }]);

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

    var submissionDiff = {
      name: 'submission.diff',
      url: '/:submissionId/diff',
      templateUrl: 'static/partials/submission.diff.html',
      controller: "SubmissionDiffCtrl"
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

    var courses = {
      name: 'course',
      abstract: true,
      url: '/course',
      templateUrl: 'static/partials/course.base.html',
    }

    var courseList = {
      name: 'course.list',
      url: '/',
      templateUrl: 'static/partials/course.list.html',
      controller: "CourseListCtrl"
    }

    var courseDetail = {
      name: 'course.detail',
      url: '/:courseId',
      templateUrl: 'static/partials/course.detail.html',
      controller: "CourseDetailCtrl"
    }

    var courseNew = {
      name: 'course.new',
      url: '/new',
      templateUrl: 'static/partials/course.new.html',
      controller: "CourseNewCtrl"
    }

    $stateProvider.
      state(submissions).
      state(submissionList).
      state(submissionDetail).
      state(submissionDiff).
      state(assignments).
      state(assignmentList).
      state(assignmentDetail).
      state(courses).
      state(courseList).
      state(courseNew)
      ;
  }]);

app.factory('Submission', ['$resource',
    function($resource) {
      return $resource('api/v1/submission/:id', {format: "json"}, {
        query: {
          isArray: false
        },
        get: {
          isArray: false,
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        diff: {
          url: 'api/v1/submission/:id/diff',
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
  $scope.itemsPerPage = 20;
  $scope.currentPage = 1;

  $scope.refresh = function(page) {
    Submission.query({
      fields: {
        'created': true,
        'id': true,
        'submitter': {
          'id': true
        },
        'assignment': {
          'name': true,
          'id': true,
        },
      },
      page: page,
      num_page: $scope.itemsPerPage
    }, function(response) {
      $scope.data = response.data;
      $scope.message = response.message;
      if (response.data.page !== $scope.currentPage) {
        $scope.currentPage = response.data.page;
        $scope.pageChange();
      }
    });
  }
  $scope.pageChanged = function() {
    $scope.refresh($scope.currentPage);
  }
  $scope.refresh(1);
  }]);

app.controller("SubmissionDetailCtrl", ['$scope', '$location', '$stateParams',  'Submission',
  function($scope, $location, $stateParams, Submission) {
    $scope.submission = Submission.get({id: $stateParams.submissionId});
  }]);

app.controller("SubmissionDiffCtrl", ['$scope', '$stateParams',  'Submission',
  function($scope, $stateParams, Submission) {
    $scope.diff = Submission.diff({id: $stateParams.submissionId});
  }]);


app.factory('Assignment', ['$resource',
    function($resource) {
      return $resource('api/v1/assignment/:id', {format: "json"}, {
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

app.controller("AssignmentListCtrl", ['$scope', 'Assignment',
  function($scope, Assignment) {
    $scope.assignments = Assignment.query();
  }]);

app.controller("AssignmentDetailCtrl", ["$scope", "$stateParams", "Assignment",
    function ($scope, $stateParams, Assignment) {
      $scope.assignment = Assignment.get({id: $stateParams.assignmentId});
    }
  ]);

app.factory('Course', ['$resource',
    function($resource) {
      return $resource('api/v1/course/:id', {
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
        },
      });
    }
  ]);

app.controller("CourseListCtrl", ['$scope', 'Course',
  function($scope, Course) {
    $scope.courses = Course.query();
  }]);

app.controller("CourseDetailCtrl", ["$scope", "$stateParams", "Course",
    function ($scope, $stateParams, Course) {
      $scope.course = Course.get({id: $stateParams.courseId});
    }
  ]);

// NOT WORKING RIGHT NOW
app.controller("CourseNewCtrl", ["$scope", "Course",
    function ($scope, Course) {
      $scope.course = {};
      $scope.test = {'test':3};

      $scope.save = function() {
        var course = new Course($scope.course);
        course.$save();
      };
    }
  ]);
