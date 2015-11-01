// Error Handling
function report_error($window, err) {
    console.log(err);
    $window.swal('Error', err.data.message, 'error');
}

app.controller("HeaderController", ["$scope", "$window", "$state", "$stateParams",
    function ($scope, $window, $state, $stateParams) {
        $scope.openMenu = function(menu) {
            document.querySelector('.menu').classList.add('active');
            container = document.querySelector('.container-fluid').classList;
            container.add('active');
            container.add('pushed');
        }
        $window.closeMenu = $scope.closeMenu = function() {
            document.querySelector('.menu').classList.remove('active');
            container = document.querySelector('.container-fluid').classList;
            container.remove('active');
            container.remove('pushed');
        }
    }
])

function filter_rows(items) {
    rows = [];
    row = [];
    for (var i=0;i<items.length;i++) {
        item = items[i];
        if (i%3 == 0 && i != 0) {
            rows.push(row);
            row = [];
        }
        row.push(item);
    }
    if (row.length > 0) {
        rows.push(row);
    }
    return rows;
}

app.controller("CourseSelectorController", ["$scope", "$window", "$state", '$stateParams', 'Course',
    function ($scope, $window, $state, $stateParams, Course) {
      Course.get({
        'onlyenrolled': true
      },function(response) {
        if (response.results) {
            $scope.courses = response.results;
            $scope.rows = filter_rows(response.results);
        } else {
            $scope.courses = $scope.rows = []
        }
      }, function(err) {
           report_error($window, err);
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

      $scope.loadAll = function() {
        Course.get(function(response) {
            if (response.results) {
                $scope.rows = filter_rows(response.results);
            } else {
                $scope.courses = $scope.rows = undefined;
            }
          }, function(err) {
            report_error($window, err);
        });
      }
    }
]);

// Assignment Controllers
app.controller("AssignmentOverviewController", ['$scope', "$window",'Assignment', 'User', '$timeout',
  function($scope, $window, Assignment, User, $timeout) {
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
    }, function(err) {
         report_error($window, err);
     })}
]);

// Assignment Controllers
app.controller("GroupOverviewController", ['$scope', "$window",'Assignment', 'User', '$timeout',
  function($scope, $window, Assignment, User, $timeout) {
    Group.query(function(response) {
      $scope.assignments = response.results;
    }, function(err) {
         report_error($window, err);
     })}
]);



app.controller("SubmissionDetailCtrl", ['$scope', '$window', '$location', '$stateParams', '$sce', '$timeout', '$anchorScroll', 'Submission',
  function($scope, $window, $location, $stateParams, $sce, $timeout, $anchorScroll, Submission) {
      var converter = new Showdown.converter();

      $window.closeMenu();

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
      }, function(err) {
           report_error($window, err);
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
            $scope.initAssignments(response.assignments);
          }, function (error) {
            report_error($window, error);
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

        $scope.labelPartners(assign);
      }
      $scope.initAssignments = function(assignments) {
        $scope.assignments = assignments;
         $scope.rows = filter_rows(assignments);
          for (i = 0;i<assignments.length;i++) {
              $scope.assignInit(assignments[i]);
          }
      }

      $scope.labelPartners = function(assign) {
        info = assign.group.group_info;
        if (info !== null) {
            arr = info.member;
            for (var i = 0; i < arr.length; i++) {
                member = arr[i];
                member.i = i;
                member.letter = String.fromCharCode(65 + i);
            }
        }
      }

      $scope.initSortable = function(assign) {
        $('.sortable').disableSelection();
        $('.sortable').sortable({
            update: function(event, ui) {
                $scope.updatePartners(assign.group);
            }
        });
      }

        $scope.updatePartners = function(group) {
          info = group.group_info;
          if (info !== null && info !== undefined) {
              arr = info.member;
              order = {}
              i = 0;
              $('.sidebar.active .sortable li').each(function() {
                  order[$(this).data('i')] = i
                  i += 1;
              });
              for (var i = 0; i< arr.length; i++) {
                member = arr[i];
                member.i = j = order[i];
                member.letter = letter = String.fromCharCode(65 + order[i]);
                $('.sortable li[data-i="'+i+'"]').find('.member-letter').html(letter);
              }
              return arr
          }
        }

      $scope.reorder = function(group) {
        arr = $scope.updatePartners(group);
        order = arr.concat()
        for (var i=0;i<arr.length;i++) {
            member = arr[i];
            order.splice(member.i, 1, member.email[0]);
        }

        Group.reorder({
            id: group.group_info.id,
            order: order
        },
        function (response) {
            $scope.closeDetails();
            $scope.reloadView();
            $window.swal({
                title: "Order saved",
                text: "The order you specified has been saved.",
                timer: 3500,
                type: "success"
            });
        }, function(err) {
            report_error($window, err);
        })
      }

      $scope.reloadAssignments();

      $scope.showComposition = function(score, backupId) {
        if (score) {
          if (score.message.length > 200) {
            var gradeResults = open('','_blank','height=600,width=500');
            gradeResults.document.write('<pre>' + score.message + '</pre>');
            score.message = " (In pop-up window)";
          }
          $window.swal({title: 'Score: '+score.score,
              text: 'Message: ' + score.message,
              showCancelButton: true,
              icon: false,
              allowEscapeKey: true,
              allowOutsideClick: true,
              confirmButtonText: "View Code",
              closeOnConfirm: true},
              function(isConfirm){
                if (isConfirm) {
                  $window.location.replace('#/'+$scope.courseId+'/submission/'+backupId.toString()+'/diff')
                } else {
                  if (gradeResults) {
                    gradeResults.close();
                  }
                } });
        }
      }
      $scope.reloadView = function () {
        // oldToggle = $scope.currAssign.id
//          $scope.currAssign = null;

          User.force_get({
            course: $stateParams.courseId,
          }, function (response) {
            $scope.initAssignments(response.assignments);
            $scope.initSortable();
          }, function (error) {
            report_error($window, error);
            $state.transitionTo('courseLanding', null, { reload: true, inherit: true, notify: true })
          });

        // $state.transitionTo($state.current, angular.copy($stateParams), { reload: true, inherit: true, notify: true });
      };

      $scope.removeMember = function(currGroup, member) {
            Group.removeMember({
              id: currGroup.id,
              email: member.email[0]
            }, function (response) {
                $window.swal('Removed!', 'You may now invite additional members to your group.', 'success');
                $scope.closeDetails();
                $scope.reloadView();
            }, function(err) {
                  report_error($window, err);
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

          report_error($window, err);
        });
      }

      $scope.rejectInvite = function(currGroup) {
          Group.rejectInvitation({
            id: currGroup.id,
          }, function (response) {
            $scope.closeDetails();
            $window.swal({
              title: "Invitation rejected.",
              text: "You can now invite other members and/or be invited.",
              timer: 3500,
              type: "success"
            });
            $scope.reloadView();
          }, function (err) {
            report_error($window, err);
          });
      };

      $scope.acceptInvite = function(currGroup) {
          Group.acceptInvitation({
              id: currGroup.id,
          }, function (response) {
            $scope.closeDetails();
            $window.swal({
              title: "Group joined!",
              text: "You can now view submissions credited to this group.",
              timer: 3500,
              type: "success"
            });
            $scope.reloadView();
          }, function (err) {
            report_error($window, err);
          });
      };

      $scope.subm_quantity = 5;
      $scope.backup_quantity = 5;


      $scope.getSubmissions = function (assign,toIncrease) {
            if (toIncrease) {
              $scope.subm_quantity += 10;
            }
            User.getSubmissions({
              assignment: assign.assignment.id,
              quantity: $scope.subm_quantity
            }, function (response) {
              assign.submissions = response;
            }, function(err) {
                 report_error($window, err);
             });
      }

      $scope.getBackups = function (assign, toIncrease) {
            if (toIncrease) {
              $scope.backup_quantity += 10;
            }
            User.getBackups({
              assignment: assign.assignment.id,
              quantity: $scope.backup_quantity
            }, function (response) {
                assign.backups = response;
            }, function(err) {
                 report_error($window, err);
             });
      }

      $scope.changeSubmission = function (backup) {
        FinalSubmission.post({
          submission: backup.id
        }, function (response) {
            $scope.closeDetails();
          $scope.reloadView();
          $window.swal({
              title: "Changed Submission",
              text: "We'll grade the submission you marked.",
              timer: 3500,
              type: "success"
            });
        }, function (error) {
            report_error($window, error);
        })
      }


      $scope.addMember = function(assign, member) {
        if (member && member != '') {
          assignId = assign.assignment.id
          Assignment.invite({
            id: assignId,
            email: member
          }, function (response) {
                $scope.closeDetails();
                $window.swal({
                  title: "Invitation Sent!",
                  text: "Your partner will need to login to okpy.org and accept the invite.",
                  timer: 3500,
                  type: "success"
                });
                $scope.reloadView();
          }, function(err) {
               report_error($window, err);
           });
        }
      };

      $scope.canReorder = function(assign) {
        if (!assign.assignment.active) {
            $window.swal('Error', 'Cannot reorder group members after the assignment lock date.', 'error');
        }
      }

      $scope.randomColor = function randomColor(assignment) {
        // themes = ['blue','gold','purple']
        themes = ['gold']  // fluctuating (randomly-chosen) colors confuse people
        if (!assignment.color) {
            var blob = document.querySelectorAll('.blob[id="'+assignment.id+'"]');
            assignment.color = blob.length > 0 ? blob[0].getAttribute('color') : themes[Math.ceil(Math.random()*themes.length)-1]
        }
        return assignment
      }

      $scope.makeAbsoluteURL = function makeAbsoluteURL(url) {
        if (url.indexOf("http") == 0) {
          return url
        } else {
          return "http://" + url
        }
      }

        $scope.openDetails = function openDetails(assign) {
            $scope.currGroup = assign.group
            $scope.currAssign = assign
            document.querySelector('.container-fluid').classList.add('active');
            document.querySelector('.sidebar[id="'+assign.assignment.id+'"]').classList.add('active');
            $scope.initSortable(assign);
        }

        $window.closeDetails = $scope.closeDetails = function closeDetails() {
            document.querySelector('.menu').classList.remove('active');
            document.querySelector('.container-fluid').classList.remove('active');
            sidebars = document.querySelectorAll('.sidebar');
            for (var i=0;i<sidebars.length;i++) {
                sidebar = sidebars[i];
                sidebar.classList.remove('active');
            }
        }
    }
]);
