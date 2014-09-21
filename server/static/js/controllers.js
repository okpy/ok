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

app.controller("SubmissionDetailCtrl", ['$scope', '$location', '$stateParams',  '$timeout', '$anchorScroll', 'Submission',
  function($scope, $location, $stateParams, $timeout, $anchorScroll, Submission) {
    $scope.submission = Submission.get({id: $stateParams.submissionId});
  }]);

app.controller("SubmissionDiffCtrl", ['$scope', '$stateParams',  'Submission', '$timeout',
  function($scope, $stateParams, Submission) {
    $scope.diff = Submission.diff({id: $stateParams.submissionId});
  }]);

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

app.controller("AssignmentListCtrl", ['$scope', 'Assignment',
  function($scope, Assignment) {
    $scope.assignments = Assignment.query();
  }]);

app.controller("AssignmentDetailCtrl", ["$scope", "$stateParams", "Assignment",
    function ($scope, $stateParams, Assignment) {
      $scope.assignment = Assignment.get({id: $stateParams.assignmentId});
    }
  ]);

app.controller("CodeLineController", ["$scope", "$timeout", "$location", "$anchorScroll",
    function ($scope, $timeout, $location, $anchorScroll) {
      $scope.lineNum = $scope.$index + 1;
      $scope.anchorId = $scope.file_name + "-L" + $scope.lineNum;
      $scope.scroll = function() {
        console.log("Scrolling to "+$scope.anchorId);
        $location.hash($scope.anchorId);
        $anchorScroll();
      }
      if ($scope.$last === true) {
        $timeout(function () {
          $(".diff-line-code").each(function(i, elem) {
            hljs.highlightBlock(elem);
          })
          $anchorScroll();
        });
      }
    }
  ]);

app.controller("DiffController", ["$scope", "$timeout", "$location", "$anchorScroll",
    function ($scope, $timeout, $location, $anchorScroll) {
      contents = [];
      var leftNum = 0, rightNum = 0;
      for (var i = 0; i < $scope.contents.length; i++) {
        codeline = {};
        codeline.start = $scope.contents[i][0];
        codeline.line = $scope.contents[i].slice(2);
        codeline.lineNum = i + 1;
        if (codeline.start == "+") {
          rightNum++;
          codeline.rightNum = rightNum;
          codeline.leftNum = "";
        } else if (codeline.start == "-") {
          leftNum++;
          codeline.leftNum = leftNum;;
          codeline.rightNum = "";
        } else if (codeline.start == "?") {
          // TODO: add in-line coloring
          continue;
        } else {
          leftNum++;
          rightNum++;
          codeline.leftNum = leftNum;;
          codeline.rightNum = rightNum;
        }
        contents.push(codeline);
      }
      $scope.contents = contents;
      $timeout(function() {
        $anchorScroll();
      });
    }
  ]);

app.controller("DiffLineController", ["$scope", "$timeout", "$location", "$anchorScroll",
    function ($scope, $timeout, $location, $anchorScroll) {
      var start = $scope.codeline.start;
      if (start == "+") {
        $scope.positive = true;
      } else if (start == "-") {
        $scope.negative = true;
      } else {
        $scope.neutral = true;
      }
      $scope.anchorId = $scope.file_name + "-L" + $scope.codeline.lineNum;
      $scope.scroll = function() {
        $location.hash($scope.anchorId);
        $anchorScroll();
      }
    }
  ]);

app.controller("GroupController", ["$scope", "$stateParams", "$window", "$timeout", "Group",
    function ($scope, $stateParams, $window, $timeout, Group) {
      $scope.group = Group.getFromAssignment({id: $stateParams.assignmentId});
      $scope.refreshGroup = function() {
          $timeout(function() {
            $scope.group = Group.getFromAssignment({id: $stateParams.assignmentId});
          }, 300);
      }
      $scope.createGroup = function() {
        Group.save({
          assignment: $stateParams.assignmentId,
          members: [$window.user]
        }, $scope.refreshGroup);
      }
    }
  ]);

app.controller("MemberController", ["$scope", "$modal", "Group",
    function ($scope, $modal, Group) {
      $scope.remove = function() {
        var modal = $modal.open({
          templateUrl: '/static/partials/removemember.modal.html',
          scope: $scope,
          size: 'sm',
          resolve: {
            modal: function () {
              return modal;
            }
          }
        });
        modal.result.then(function() {
          Group.removeMember({
            members: [$scope.member.email],
            id: $scope.group.id
          }, $scope.refreshGroup);
        });
      }
    }
  ]);

app.controller("AddMemberController", ["$scope", "$stateParams", "$window", "$timeout", "Group",
    function ($scope, $stateParams, $window, $timeout, Group) {
      $scope.add = function() {
        if ($scope.newMember != "") {
          Group.addMember({
            members: [$scope.newMember],
            id: $scope.group.id
          }, $scope.refreshGroup);
        }
      }
    }
  ]);

app.controller("InvitationsController", ["$scope", "$stateParams", "$window", "$timeout", "User",
    function ($scope, $stateParams, $window, $timeout, User) {
      $scope.invitations = User.invitations({
        assignment: $stateParams.assignmentId
      });
      $scope.refreshInvitations = function() {
          $timeout(function() {
            $scope.invitations = User.invitations({
              assignment: $stateParams.assignmentId
            });
          }, 300);
      }
      $scope.accept = function(invitation, $event) {
        $event.stopPropagation();
        if ($scope.group.in_group === false) {
          User.acceptInvitation({
            invitation: invitation.id
          }, function() {
            $scope.refreshInvitations();
            $scope.refreshGroup();
          });
        } else {
        }
      }

      $scope.reject = function(invitation, $event) {
        $event.stopPropagation();
        User.rejectInvitation({
          invitation: invitation.id
        }, $scope.refreshInvitations);
      }
    }
  ]);
