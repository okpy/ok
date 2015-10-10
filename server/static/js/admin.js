var app = angular.module('admin', ['ngResource', 'ui.router', 'angular-loading-bar', 'ngAnimate', 'ui.bootstrap', 'angularMoment', 'ngStorage', 'tableSort']);

app.directive('assignmentModule', function() {
        return {
            restrict: 'E',
            templateUrl: '/static/partials/dashboard/assignment.moduledash.html',
        };
    });

app.directive('assignmentList', function() {
        return {
            restrict: 'E',
            templateUrl: '/static/partials/admin/assignment.list.html',
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
            templateUrl: '/static/partials/dashboard/submission.list.html',
        };
    });

app.directive('courseModule', function() {
        return {
            restrict: 'E',
            templateUrl: '/static/partials/dashboard/course.module.html',
        };
    });

app.directive('courseList', function() {
        return {
            restrict: 'E',
            controller: "CourseListCtrl",
            templateUrl: '/static/partials/admin/course.list.html',
        };
    });


app.directive('sidebarModule', function() {
        return {
            restrict: 'E',
            templateUrl: '/static/partials/admin/sidebar.module.html',
        };
    });

app.directive('queueModule', function() {
        return {
            restrict: 'E',
            templateUrl: '/static/partials/admin/queue.module.html',
        };
    });

app.directive('queueList', function() {
        return {
            restrict: 'E',
            templateUrl: '/static/partials/queue/list.html',
        };
    });

app.directive('userqueueList', function() {
       return {
           restrict: 'E',
           templateUrl: '/static/partials/admin/userqueue.list.html',
       };
   });


app.directive('staffList', function() {
        return {
            restrict: 'E',
            controller: "StaffListCtrl",
            templateUrl: '/static/partials/admin/staff.list.html',
        };
    });


app.directive('studentList', function() {
            return {
                restrict: 'E',
                controller: "StudentListCtrl",
                templateUrl: '/static/partials/admin/students.list.html',
            };
        });



app.config(['$stateProvider', '$urlRouterProvider',
  function($stateProvider, $urlRouterProvider) {
    $urlRouterProvider.otherwise("/");

    var admin = {
      name: 'admin',
      url: '/',
      templateUrl: '/static/partials/admin/admin.html',
    }

    var dashboard = {
      name: 'dashboard',
      url: '/student',
      templateUrl: '/static/partials/dashboard/dashboard.html',
    }


    var submissions = {
      name: 'submission',
      abstract: true,
      url: '/submission',
      templateUrl: '/static/partials/common/submission.base.html',
    }

    var submissionFinal = {
      name: 'submission.final',
      url: '/final/:finalId',
      templateUrl: '/static/partials/admin/finalsubmission.html',
      controller: "FinalSubmissionCtrl"
    }

    var submissionDetail = {
      name: 'submission.detail',
      url: '/:submissionId',
      templateUrl: '/static/partials/common/submission.detail.html',
      controller: "SubmissionDetailCtrl"
    }

    var submissionDiff = {
      name: 'submission.diff',
      url: '/:submissionId/diff',
      templateUrl: '/static/partials/student/submission.diff.html',
      controller: "SubmissionDiffCtrl"
    }

    var assignments = {
      name: 'assignment',
      abstract: true,
      url: '/assignment',
      templateUrl: '/static/partials/common/assignment.base.html',
    }

    var assignmentDetail = {
      name: 'assignment.detail',
      url: '/detail/:assignmentId',
      templateUrl: '/static/partials/admin/assignment.detail.html',
      controller: "AssignmentDetailCtrl"
    }

    var courses = {
      name: 'course',
      abstract: true,
      url: '/course',
      templateUrl: '/static/partials/admin/course.base.html',
    }

    var courseList = {
      name: 'course.list',
      url: '/',
      templateUrl: '/static/partials/admin/course.list.html',
      controller: "CourseListCtrl"
    }

    var courseAssignmentBase = {
      name: 'course.assignment',
      abstract: true,
      url: '/:courseId/assignment',
      templateUrl: '/static/partials/admin/assignment.base.html',
    }

    var courseAssignmentList = {
      name: 'course.assignment.list',
      url: '/',
      templateUrl: '/static/partials/admin/course.assignment.list.html',
      controller: "CourseAssignmentListCtrl"
    }

    var courseAssignmentCreate = {
      name: 'course.assignment.create',
      url: '/create',
      templateUrl: '/static/partials/admin/assignment.create.html',
      controller: "AssignmentCreateCtrl"
    }

    var courseAssignmentEdit = {
      name: 'course.assignment.edit',
      url: '/edit/:assignmentId',
      templateUrl: '/static/partials/admin/assignment.edit.html',
      controller: "AssignmentEditCtrl"
    }

    var courseAssignmentQueueBase = {
        name: 'course.assignment.queue',
        abstract: true,
        url: '/queues/:assignmentId',
        templateUrl:'/static/partials/admin/queue.base.html'
    }

    var courseAssignmentQueueList = {
        name: 'course.assignment.queue.list',
        url: '/',
        templateUrl:'/static/partials/admin/queue.list.html',
        controller: "AssignmentQueueListCtrl"
    }

    var courseAssignmentQueueGenerate = {
        name: 'course.assignment.queue.generate',
        url: '/generate',
        templateUrl:'/static/partials/admin/queue.generate.html',
        controller: "AssignmentQueueGenerateCtrl"
    }

    var courseNew = {
      name: 'course.new',
      url: '/new',
      templateUrl: '/static/partials/admin/course.new.html',
      controller: "CourseNewCtrl"
    }

    var courseBase = {
      name: 'course.detail',
      url: '/:courseId',
      abstract: true,
      templateUrl: '/static/partials/admin/course.base.html',
    }

    var courseDetail = {
      name: 'course.detail.stats',
      url: '/',
      templateUrl: '/static/partials/admin/course.detail.html',
      controller: "CourseDetailCtrl"
    }

    var submissionList = {
          name: 'course.submissions',
          url: '/:courseId/submissions',
          templateUrl: '/static/partials/admin/submission.list.html'
    }
    var submissionListQuery = {
          name: 'course.submissions.query',
          url: '/:query',
          templateUrl: '/static/partials/admin/submission.list.html'
    }
    var staff = {
      name: 'staff',
      url: '/:courseId/staff',
      abstract: true,
      templateUrl: '/static/partials/admin/staff.base.html'
    }

    var staffList = {
      name: 'staff.list',
      url: '/',
      templateUrl: '/static/partials/admin/staff.list.html',
      controller: "StaffListCtrl"
    }

    var staffDetail = {
      name: 'staff.detail',
      url: '/:staffId',
      templateUrl: '/static/partials/admin/staff.detail.html',
      controller: "StaffDetailCtrl"
    }

    var staffAdd = {
        name: 'staff.add',
        url: '/add',
        templateUrl:'/static/partials/admin/staff.add.html',
        controller: 'StaffAddCtrl'
    }

    var students = {
          name: 'students',
          url: '/:courseId/students',
          abstract: true,
          templateUrl: '/static/partials/admin/students.base.html'
        }

    var studentsList = {
          name: 'students.list',
          url: '/',
          templateUrl: '/static/partials/admin/students.list.html',
          controller: "StudentsListCtrl"
        }

    var studentsAdd = {
        name: 'students.add',
        url: '/add',
        templateUrl: '/static/partials/admin/students.add.html',
        controller: 'StudentsAddCtrl'
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
      templateUrl: '/static/partials/queue/list.html'
    }

    var queueDetail = {
      name: 'queue.detail',
      url: '/:queueId',
      templateUrl: '/static/partials/queue/detail.html',
      controller: "QueueDetailCtrl"
    }

    var userQueueList = {
      name: 'userqueue',
      url: '/userqueue',
      templateUrl: '/static/partials/admin/userqueue.list.html',
    }

    var loginLanding = {
      name: 'loginLanding',
      url: '/loginLanding',
      templateUrl: '/static/partials/common/loginLanding.html'
    }

    $stateProvider.
      state(dashboard).
      state(admin).
      state(submissions).
      state(submissionFinal).
      state(submissionList).
      state(submissionListQuery).
      state(submissionDetail).
      state(submissionDiff).
      state(assignments).
      state(assignmentDetail).
      state(courses).
      state(courseBase).
      state(courseAssignmentBase).
      state(courseAssignmentList).
      state(courseAssignmentCreate).
      state(courseAssignmentEdit).
      state(courseAssignmentQueueBase).
      state(courseAssignmentQueueList).
      state(courseAssignmentQueueGenerate).
      state(courseList).
      state(courseDetail).
      state(courseNew).
      state(staff).
      state(staffAdd).
      state(staffList).
      state(staffDetail).
      state(students).
      state(studentsAdd).
      state(studentsList).
      state(versions).
      state(versionList).
      state(versionDetail).
      state(versionUpdate).
      state(versionNew).
      state(queues).
      state(queueList).
      state(queueDetail).
      state(userQueueList).
      state(loginLanding)
      ;
  }]);
