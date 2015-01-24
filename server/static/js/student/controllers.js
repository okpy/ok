
app.controller("CourseSelectorController", ["$scope", "$window", "$state", '$stateParams', 'Course',
    function ($scope, $window, $state, $stateParams, Course) {
      Course.get(function(response) {
        $scope.courses = response.results
        // TODO : Remove
        console.log($scope.courses)
      });
      if ($window.user.indexOf("berkeley.edu") == -1) {
        $window.swal({
            title: "Is this the right login?",
            text: "Logging you in with your \"" + $window.user + "\" account...",
            type: "info",
            showCancelButton: true,
            confirmButtonColor: "#DD6B55",
            confirmButtonText: "Yes - that's correct!",
            cancelButtonText: "No - log me out",
            closeOnConfirm: true,
            closeOnCancel: true
        }, function(isConfirm) {
            if (isConfirm) {
              // Do nothing, because the user might want to select a course.
            } else {
                $window.location.href = $window.reloginLink;
            }
        });
      } else {
         $window.location.hash = "";
      }
    }
]);

// Assignment Controllers
app.controller("AssignmentOverviewController", ['$scope', 'Assignment', 'User', '$timeout',
  function($scope, Assignment, User, $timeout) {
    Assignment.query(function(response) {
      $scope.assignments = response.results;
    })}
]);

// Assignment Controllers
app.controller("GroupOverviewController", ['$scope', 'Assignment', 'User', '$timeout',
  function($scope, Assignment, User, $timeout) {
    Group.query(function(response) {
      $scope.assignments = response.results;
    })}
]);


// Eeek.
app.controller("AssignmentDashController", ['$scope', '$window',  '$stateParams', 'Assignment', 'User', 'Group', '$timeout',
  function($scope, $window,  $stateParams, Assignment, User, Group, $timeout) {

      $scope.toggleAssign = function (assign) {
        if ($scope.currAssign == assign) {
          $scope.currAssign = null
        } else {
          $scope.currAssign = assign;
        }
      }

      $scope.reloadAssignments = function () {
          User.get({
            course: $stateParams.courseId,
          }, function (response) {
            console.log(response.assignments)
            $scope.assignments = response.assignments
          })
      }

      $scope.reloadAssignGroup = function () {
          Assignment.group({
            id: $scope.currAssign.assignment.id,
          }, function (response) {
            $scope.currAssign.group = response.data;
            $scope.currGroup = $scope.currAssign.group;
          })
      }

      $scope.reloadAssignments()

      $scope.removeMember = function(currGroup, member) {
        console.log(member, currGroup.id)
            Group.removeMember({
              id: currGroup.id,
              member: member.email[0]
            }, function (err) {
              $scope.currGroup = null;
              $scope.hideGroup();
              $scope.currAssign.group = null
            });
      };

      $scope.getSubmissions = function (assignId) {
            User.getSubmissions({
              assignment: assignId
            }, function (response) {
              $scope.currAssign.submissions = response;
              $scope.showSubms();
            });
      }

      $scope.getBackups = function (assignId) {
            User.getBackups({
              assignment: assignId
            }, function (response) {
              $scope.currAssign.backups = response;
              $scope.showBackups();
            });
      }

      $scope.addMember = function(assign, member) {
        if (member && member != '') {
          assignId = assign.assignment.id
          Assignment.invite({
            id: assignId,
            email: member
          }, function (response) {
            // TODO  Check for error.
              $window.swal({
                  title: "Invitation Sent!",
                  text: "They will need to login to okpy.org and accept the invite.",
                  timer: 3500,
                  type: "success"
                });
              $scope.reloadAssignGroup()
          }, function (err, data) {
            $window.swal("Oops...", "That user/email isn't in this course.", "error");
            $scope.reloadAssignGroup()
         });
        }
      };

        $scope.showGroup = function showGroup(group) {
            $('.popups').addClass('active');
            $('.popup').removeClass('active');
            $('.popup.group').addClass('active').removeClass('hide');
            $scope.currGroup = group
        }

        $scope.hideGroup = function hideGroup() {
            $('.popups').removeClass('active');
            $('.popup').removeClass('active');
            $('.popup.group').addClass('active').addClass('hide');
        }

        $scope.showBackups = function showGroup(id) {
            $('.popups').addClass('active');
            $('.popup').removeClass('active');
            $('.popup.backups').addClass('active').removeClass('hide');
        }

        $scope.showSubms = function showGroup(id) {
            $('.popups').addClass('active');
            $('.popup').removeClass('active');
            $('.popup.submissions').addClass('active').removeClass('hide');
        }

        $scope.hidePopups =  function hidePopups() {
            $('.assign').removeClass('s');
            $('.popups').removeClass('active');
            $('.popup').removeClass('active');
            setTimeout(function() {
              $('.popup').addClass('hide');
            },400);
          }

        $scope.showLoader = function showLoader() {
          $('.loader').removeClass('hide');
        }

        $scope.hideLoader = function hideLoader() {
          $('.loader').addClass('done hide');
          setTimeout(function() {
            $('.loader').removeClass('done')
          },800)
        }

      }
]);

// Group Controllers
app.controller("GroupController", ["$scope", "$stateParams", "$window", "$timeout", "Group",
    function ($scope, $stateParams, $window, $timeout, Group) {
      $scope.loadGroup = function() {
        Group.query({
            assignment: $stateParams.assignmentId,
            members: $window.user
          }, function(groups) {
            if (groups.length == 1) {
              $scope.group = groups[0];
              $scope.inGroup = true;
            } else {
              $scope.group = undefined;
              $scope.inGroup = false;
            }
          }
        );
      }
      $scope.refreshGroup = function() {
          $timeout(function() {
            $scope.loadGroup();
          }, 300);
      }
      $scope.loadGroup();
      $scope.createGroup = function() {
        Group.save({
          assignment: $stateParams.assignmentId,
          members: $window.user
        }, $scope.refreshGroup);
      }
    }
  ]);

app.controller("MemberController", ["$scope", "$modal", "Group",
    function ($scope, $modal, Group) {
      $scope.remove = function() {
          Group.removeMember({
            member: $scope.member.email,
            id: $scope.group.id
          }, $scope.refreshGroup);
        }
    }
]);

app.controller("AddMemberController", ["$scope", "$stateParams", "$window", "$timeout", "Group",
    function ($scope, $stateParams, $window, $timeout, Group) {
      $scope.add = function() {
        if ($scope.newMember != "") {
          Group.addMember({
            member: $scope.newMember,
            id: $scope.group.id
          }, $scope.refreshGroup);
        }
      }
    }
  ]);

app.controller("InvitationsController", ["$scope", "$stateParams", "$window", "$timeout", "User", "Group",
    function ($scope, $stateParams, $window, $timeout, User, Group) {
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
        if ($scope.inGroup === false) {
          Group.acceptInvitation({
            id: invitation.id
          }, function() {
            $scope.refreshInvitations();
            $scope.refreshGroup();
          });
        } else {
        }
      }

      $scope.reject = function(invitation, $event) {
        $event.stopPropagation();
        Group.rejectInvitation({
          id: invitation.id
        }, $scope.refreshInvitations);
      }
    }
  ]);

