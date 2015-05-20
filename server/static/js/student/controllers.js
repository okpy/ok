app.controller("HeaderController", ["$scope", "$window", "$state", "$stateParams",
    function ($scope, $window, $state, $stateParams) {
        $scope.openMenu = function(menu) {
            $(menu).addClass('active')
            $('.container-fluid').addClass('active').addClass('pushed')
        }
        $scope.closeMenu = function() {
            $('.menu').removeClass('active')
            $('.container-fluid').removeClass('active').removeClass('pushed')
        }
    }
])

app.controller("CourseSelectorController", ["$scope", "$window", "$state", '$stateParams', 'Course',
    function ($scope, $window, $state, $stateParams, Course) {
      Course.get(function(response) {
        $scope.courses = response.results
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
    Assignment.query({
      fields: {
        id: true,
        display_name: true,
        id: true,
        due_date: true,
        points: true,
        created: true,
      }}, function(response) {
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



app.controller("SubmissionDetailCtrl", ['$scope', '$window', '$location', '$stateParams', '$sce', '$timeout', '$anchorScroll', 'Submission',
  function($scope, $window, $location, $stateParams, $sce, $timeout, $anchorScroll, Submission) {
      var converter = new Showdown.converter();
      $scope.convertMarkdown = function(text) {
        if (text == "" || text === undefined) {
          return $sce.trustAsHtml("")
        }
        return $sce.trustAsHtml(converter.makeHtml(text));
      }

     Submission.get({
      id: $stateParams.submissionId
     }, function (response) {
        $scope.submission = response;
        $scope.courseId = $stateParams.courseId;
        if (response.messages && response.messages.file_contents && response.messages.file_contents['submit']) {
          delete $scope.submission.messages.file_contents['submit'];
          $scope.isSubmit = true;
        }
      });
  }]);


// Main dashboard controller. Should be modularized later.
app.controller("AssignmentDashController", ['$scope', '$window', '$state',  '$stateParams', 'Assignment', 'User', 'Group', 'Submission', 'FinalSubmission', '$timeout',
  function($scope, $window, $state,  $stateParams, Assignment, User, Group, Submission, FinalSubmission, $timeout) {
      $scope.courseId = $stateParams.courseId

      $scope.reloadAssignments = function () {
          User.get({
            course: $stateParams.courseId,
          }, function (response) {
            $scope.closeDetails();
            $scope.assignments = response.assignments;
            for (i = 0;i<response.assignments.length;i++) {
                $scope.assignInit(response.assignments[i]);
            }
          }, function (error) {
            $window.swal('Unknown Course', 'Whoops. There was an error', 'error');
            $state.transitionTo('courseLanding', null, { reload: true, inherit: true, notify: true })
          })
      }
      $scope.assignInit = function(assign) {
        if (assign.backups) {
            $scope.getBackups(assign, false);
        }
        if (assign.submissions) {
            $scope.getSubmissions(assign, false);
        }
      }
      $scope.showComposition = function(score, backupId) {
        if (score) {
          $window.swal({title: 'Score: '+score.score+'/2',
              text: 'Message: ' + score.message,
              showCancelButton: false,
              icon: false,
              allowEscapeKey: true,
              allowOutsideClick: true,
              confirmButtonText: "View Comments",
              closeOnConfirm: true},
              function(isConfirm){
                if (isConfirm) {
                  $window.location.replace('#/'+$scope.courseId+'/submission/'+backupId.toString()+'/diff')
                } else {

                } });
        }
      }
      $scope.reloadView = function () {
        // oldToggle = $scope.currAssign.id
          $scope.currAssign = null;

          User.force_get({
            course: $stateParams.courseId,
          }, function (response) {
            $scope.assignments = response.assignments;
            $scope.hideLoader()
          }, function (error) {
            $scope.hideLoader()
            $window.swal('Unknown Course', 'Whoops. There was an error', 'error');
            $state.transitionTo('courseLanding', null, { reload: true, inherit: true, notify: true })
          });
        $scope.hidePopups();

        // $state.transitionTo($state.current, angular.copy($stateParams), { reload: true, inherit: true, notify: true });
      };

      $scope.reloadAssignments()

      $scope.removeMember = function(currGroup, member) {
            Group.removeMember({
              id: currGroup.id,
              email: member.email[0]
            }, function (err) {
                $scope.reloadView()
                $scope.currGroup = null;
                $scope.currAssign.group = null
            });
      };

      $scope.winRate = function (assign, backupId) {
        assign.winrate = {'progress': 1, 'message': "Loading"}
        Submission.winRate({
          id: backupId
        }, function (response){
          if (response.error.type) {
            assign.winrate = {'progress': 0, 'error': true, 'message': response.error.type+" Error"}
            $window.swal(response.error.type + " Error",'There was a ' + response.error.type + ' error in your code.','error')
          } else {
            $scope.winrate = response
            assign.winrate = {
              'progress': (response.winrate / .56) * 100,
              'percent': response.winrate * 100,
              'message': response.message
            }
          }
          // $window.swal(response.winrate*100 +"%",'Final Win Rate','info')
        }, function (err) {
          assign.winrate = {
            'message': response.message,
            'error': true
          }

          $window.swal("Uhoh",'There was an error','error')
        });
      }

      $scope.rejectInvite = function(currGroup) {
          Group.rejectInvitation({
            id: currGroup.id,
          }, function (err) {
            currGroup = null
            $scope.currAssign.group = null
          });
      };

      $scope.acceptInvite = function(currGroup) {
          Group.acceptInvitation({
              id: currGroup.id,
          }, function (err) {
            $scope.reloadView()
          });
      };

      $scope.subm_quantity = 10;
      $scope.backup_quantity = 10;


      $scope.getSubmissions = function (assign,toIncrease) {
            if (toIncrease) {
              $scope.subm_quantity += 50;
            }
            User.getSubmissions({
              assignment: assign.assignment.id,
              quantity: $scope.subm_quantity
            }, function (response) {
              assign.submissions = response;
            });
      }

      $scope.getBackups = function (assign, toIncrease) {
            if (toIncrease) {
              $scope.backup_quantity += 50;
            }
            User.getBackups({
              assignment: assign.assignment.id,
              quantity: $scope.backup_quantity
            }, function (response) {
                assign.backups = response;
            });
      }

      $scope.changeSubmission = function (submId) {
        FinalSubmission.change({
          submission: submId
        }, function (response) {
          $scope.reloadView()
          $window.swal({
              title: "Changed Submission",
              text: "We'll grade the submission you marked.",
              timer: 3500,
              type: "success"
            });
        }, function (error) {
            $window.swal("Oops...", "Couldn't change your submission (the deadline to do so may have passed).", "error");
        })
      }


      $scope.addMember = function(assign, member) {
        if (member && member != '') {
          assignId = assign.assignment.id
          Assignment.invite({
            id: assignId,
            email: member
          }, function (response) {
              $scope.reloadView()
              $window.swal({
                  title: "Invitation Sent!",
                  text: "They will need to login to okpy.org and accept the invite.",
                  timer: 3500,
                  type: "success"
                });

          }, function (err) {
            $window.swal("Oops...", "Can't add that user to your group.    Is that the right email? They might already be in a group or may not be in the course.", "error");
         });
        }
      };
      
      $scope.randomColor = function randomColor(assignment) {
        themes = ['blue','gold','green']
        if (!assignment.color) {
            assignment.color = themes[Math.ceil(Math.random()*themes.length)-1]
        }
        return assignment
      }

        $scope.openDetails = function openDetails(assign) {
            $scope.currGroup = assign.group
            $scope.currAssign = assign
            $('.container-fluid').addClass('active');
            $('.sidebar[id="'+assign.assignment.id+'"]').addClass('active');
        }
        
        $scope.closeDetails = function closeDetails() {
            $('.sidebar').removeClass('active');
            $('.container-fluid').removeClass('active');
        }
        $scope.flagSubmission = function(submId) {
            $window.swal({
                title: 'Oops. Well, this is embarrassing.',
                text: 'Flagging isn\'t ready yet. Resubmit an old copy, for now, or contact your GSI.',
                showCancelButton: false,
                icon: false,
                allowEscapeKey: true,
                allowOutsideClick: true,
                confirmButtonText: "Ok",
                closeOnConfirm: true});
          }
      }
]);