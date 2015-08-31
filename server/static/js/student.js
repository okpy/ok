
angular.module('ErrorCatcher', [])
  .factory('$exceptionHandler', function () {
      return function errorCatcherHandler(exception, cause) {
          console.error(exception.stack);
          Raven.captureException(exception);
      };
  }).factory('errorHttpInterceptor', ['$q', function ($q) {
        return {
            responseError: function responseError(rejection) {
                Raven.captureException(new Error('HTTP response error'), {
                    extra: {
                        config: rejection.config,
                        status: rejection.status
                    }
                });
                return $q.reject(rejection);
            }
        };
  }]).config(['$httpProvider', function($httpProvider) {
      $httpProvider.interceptors.push('errorHttpInterceptor');
  }]);


var app = angular.module('student', ['ngResource', 'ErrorCatcher', 'ui.router', 'angular-loading-bar', 'ngAnimate', 'ui.bootstrap', 'angularMoment']);

angular.module('student').constant('angularMomentConfig', {
    timezone: 'America/Los_Angeles'
});


angular.module('student').value("RavenConfig", {
  dsn: 'https://edc8538d3d5f47fcb1b14c33d9ae7d8b@app.getsentry.com/36686',
  config: {
  whitelistUrls: ['http://ok-server.appspot.com', 'localhost']
  //Additional config options here
  }
});

app.directive('assignmentDetails', function() {
    return {
        restrict: 'E',
        templateUrl: '/static/partials/student/assignment.detail.html',
    };
});

app.directive('assignmentList', function() {
        return {
            restrict: 'E',
            templateUrl: '/static/partials/student/assignment.dash.html?cache1121',
        };
    });

app.directive('submissionModule', function() {
        return {
            restrict: 'E',
            templateUrl: '/static/partials/admin/submission.module.html',
        };
    });

app.directive('submissionList', function() {
        return {
            restrict: 'E',
            templateUrl: '/static/partials/dashboard/submission.list.html?cacheprevent1021',
        };
    });

app.directive('courseList', function() {
        return {
            restrict: 'E',
            templateUrl: '/static/partials/student/course.list.html',
        };
    });

app.directive('sidebarModule', function() {
        return {
            restrict: 'E',
            templateUrl: '/static/partials/admin/sidebar.module.html',
        };
    });

app.config(['$stateProvider', '$urlRouterProvider',
  function($stateProvider, $urlRouterProvider) {

    var courseLanding = {
      name: 'courseLanding',
      url: '/',
      templateUrl: '/static/partials/student/courseLanding.html',
    }

    var student = {
      name: 'student',
      url: '/course/:courseId',
      templateUrl: '/static/partials/student/student.html',
    }

    var submissions = {
      name: 'submission',
      abstract: true,
      url: '/:courseId/submission',
      templateUrl: '/static/partials/common/submission.base.html',
    }

    var submissionList = {
      name: 'submission.list',
      url: '/',
      templateUrl: '/static/partials/common/submission.list.html?cacheprevent1022',
      controller: "SubmissionListCtrl"
    }

    var submissionDetail = {
      name: 'submission.detail',
      url: '/:submissionId',
      templateUrl: '/static/partials/student/submission.detail.html',
      controller: "SubmissionDetailCtrl"
    }

    var submissionDiff = {
      name: 'submission.diff',
      url: '/:submissionId/diff',
      templateUrl: '/static/partials/student/submission.diff.html?cacheprevent1022',
      controller: "SubmissionDiffCtrl"
    }

    var assignments = {
      name: 'assignment',
      abstract: true,
      url: '/assignment',
      templateUrl: '/static/partials/common/assignment.base.html?cacheprevent1022',
    }

    var assignmentList = {
      name: 'assignment.list',
      url: '/',
      templateUrl: '/static/partials/common/assignment.list.html?cacheprevent1022',
      controller: "AssignmentListCtrl"
    }

    var assignmentDetail = {
      name: 'assignment.detail',
      url: '/:assignmentId',
      templateUrl: '/static/partials/common/assignment.detail.html',
      controller: "AssignmentDetailCtrl"
    }

    var courses = {
      name: 'course',
      abstract: true,
      url: '/course',
      templateUrl: '/static/partials/common/course.base.html',
    }

    var courseList = {
      name: 'course.list',
      url: '/',
      templateUrl: '/static/partials/common/course.list.html',
      controller: "CourseListCtrl"
    }

    var courseDetail = {
      name: 'course.detail',
      url: '/:courseId',
      templateUrl: '/static/partials/common/course.detail.html',
      controller: "CourseDetailCtrl"
    }

    var courseNew = {
      name: 'course.new',
      url: '/new',
      templateUrl: '/static/partials/common/course.new.html',
      controller: "CourseNewCtrl"
    }

    var versions = {
      name: 'version',
      abstract: true,
      url: '/version',
      templateUrl: '/static/partials/common/version.base.html',
    }

    var versionList = {
      name: 'version.list',
      url: '/',
      templateUrl: '/static/partials/common/version.list.html',
      controller: "VersionListCtrl"
    }

    var versionDetail = {
      name: 'version.detail',
      url: '/:versionId',
      templateUrl: '/static/partials/common/version.detail.html',
      controller: "VersionDetailCtrl"
    }

    var versionUpdate = {
      name: 'version.update',
      url: '/:versionId/new',
      templateUrl: '/static/partials/common/version.new.html',
      controller: "VersionNewCtrl"
    }

    var versionNew = {
      name: 'version.new',
      url: '/new',
      templateUrl: '/static/partials/common/version.new.html',
      controller: "VersionNewCtrl"
    }

    var queues = {
      name: 'queue',
      abstract: true,
      url: '/queue',
      templateUrl: '/static/partials/queue/base.html',
    }

    var queueList = {
      name: 'queue.list',
      url: '/',
      templateUrl: '/static/partials/queue/list.html',
      controller: "QueueListCtrl"
    }

    var queueDetail = {
      name: 'queue.detail',
      url: '/:queueId',
      templateUrl: '/static/partials/queue/detail.html',
      controller: "QueueDetailCtrl"
    }

    var loginLanding = {
      name: 'loginLanding',
      url: '/loginLanding',
      templateUrl: '/static/partials/student/loginLanding.html'
    }


    $stateProvider.
      state(courseLanding).
      state(student).
      state(submissions).
      state(submissionList).
      state(submissionDetail).
      state(submissionDiff).
      state(assignments).
      state(assignmentList).
      state(assignmentDetail).
      state(courses).
      state(courseList).
      state(courseNew).
      state(versions).
      state(versionList).
      state(versionDetail).
      state(versionUpdate).
      state(versionNew).
      state(queues).
      state(queueList).
      state(queueDetail).
      state(loginLanding)
      ;

    $urlRouterProvider.otherwise(function ($injector) {
        var $state = $injector.get('$state');
        $state.go('courseLanding');
    });


  }]);
