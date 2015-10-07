// Error Handling
function report_error($window, err) {
    console.log(err);
    $window.swal('Error', err.data.message, 'error');
}

// Admin Sidebar
app.controller("SidebarCntrl", ['$scope', '$window', 'Assignment',
  function($scope, $window, Assignment) {
    Assignment.query(function(response) {
      $scope.assignments = response.results;
    }, function(err) {
        report_error($window, err);
    });
    $scope.course_name = "Ok Admin"
  }]);

// Submission Controllers
app.controller("SubmissionModuleController", ["$scope", "$window", "Submission",
  function ($scope, $window, Submission) {
    Submission.query(function(response) {
      $scope.num_submissions = response.results.length;
    }, function(err) {
         report_error($window, err);
     });
  }
  ]);


// Assignment Controllers
app.controller("AssignmentModuleController", ["$scope", "$window", "Assignment",
  function ($scope, $window, Assignment) {
    Assignment.query(function(response) {
      $scope.assignments = response.results;
    }, function(err) {
         report_error($window, err);
     });
  }
  ]);

app.controller("AssignmentDetailCtrl", ["$scope", "$window", "$stateParams", "Assignment",
  function ($scope, $window, $stateParams, Assignment) {
    $scope.assignment = Assignment.get({
        id: $stateParams.assignmentId
    }, function (response) {
    }, function(err) {
        report_error($window, err);
    });

    $scope.statistics = Assignment.statistics({
      id: $stateParams.assignmentId
    }, function (response) {
    }, function (err) {
      report_error($window, err);
    })
  }
  ]);


app.controller("AssignmentCreateCtrl", ["$scope", "$window", "$state", "$stateParams", "Assignment", "Course",
  function ($scope, $window, $state, $stateParams, Assignment, Course) {
    $scope.existingAssign = Assignment.get({
        id: $stateParams.assignmentId
    }, function (response) {
    }, function (err) {
        report_error($window, err);
    });
    var future = new Date();
    future.setDate(future.getDate() + 31);
    due_date = lock_date = future.getFullYear() + '-' + future.getMonth() + '-' + future.getDate()



    $scope.newAssign = {
      'due_date': due_date,
      'lock_date': lock_date,
      'due_time': '23:59:59.0000',
      'lock_time': '23:59:59.0000',
      'max_group_size': 2,
      'revisions': false,
      'points': 4,
      'autograding_enabled': false,
      'autograding_key': "",
    };
    Course.get({
      id: $stateParams.courseId
    }, function(response) {
      $scope.course = response;
    }, function(err) {
         report_error($window, err);
     });
    // TODO: only allow user to create assignment for specified course - no more dropdown!
    Course.get({}, function(resp) {
        $scope.courses = resp.results;
        $scope.newAssign.course = $scope.courses[0];
    }, function(err) {
         report_error($window, err);
     });

    $scope.createAssign = function () {
        var due_date_time = $scope.newAssign.due_date + ' ' + $scope.newAssign.due_time
        var lock_date_time = $scope.newAssign.lock_date + ' ' + $scope.newAssign.lock_time
        Assignment.create({
          'display_name': $scope.newAssign.display_name,
          'name': $scope.newAssign.endpoint,
          'points': $scope.newAssign.points,
          'max_group_size': $scope.newAssign.max_group_size,
          'templates': {},
          'due_date': due_date_time,
          'course': $scope.newAssign.course.id,
          'revision': $scope.newAssign.revisions,
          'lock_date': lock_date_time,
          'autograding_enabled': $scope.newAssign.autograding_enabled,
          'autograding_key': $scope.newAssign.autograding_key,
          'url': $scope.newAssign.url
        },
          function (response) {
            $scope.courses = Course.query({},
              function (response) {
                $window.swal("Assignment Created!",'','success');
               $state.transitionTo('course.assignment.list' , {courseId: $scope.course.id} , { reload: true, inherit: true, notify: true });
             });
          }, function (error) {
            report_error($window, error);
          }
        )

    }
  }
  ]);

app.controller("AssignmentEditCtrl", ["$scope", "$window", "$state", "$stateParams", "Assignment", "Course",
  function ($scope, $window, $state, $stateParams, Assignment, Course) {

    Course.get({
      id: $stateParams.courseId
    }, function(response) {
      $scope.course = response;
    }, function(err) {
         report_error($window, err);
     });

    $scope.reloadAssignment = function() {
      Assignment.get({
        id: $stateParams.assignmentId
      }, function (response) {
        $scope.initAssignment(response);
      }, function(err) {
           report_error($window, err);
       });
    }

    $scope.initAssignment = function(assign) {
      $scope.assign = assign;
      $scope.assign.endpoint = assign.name;
      parts = assign.due_date.split(' ');
      assign.due_date = parts[0];
      assign.due_time = parts[1];
      if (assign.lock_date != null) {
        parts = assign.lock_date.split(' ');
        assign.lock_date = parts[0];
        assign.lock_time = parts[1];
      }
      if (assign.revisions == null) {
        assign.revisions = false;
      }
      if (assign.autograding_enabled == null) {
        assign.autograding_enabled = false;
      }
      $scope.initCourses(assign);
    }

    $scope.initCourses = function(assign) {
      Course.get({}, function(resp) {
          $scope.courses = resp.results;
          for (var i=0;i<resp.results.length;i++) {
            course = resp.results[i];
            if (course.id == assign.course.id) {
              assign.course = course;
              break;
            }
          }
      }, function(err) {
           report_error($window, err);
       });
    }

    $scope.reloadAssignment();

    $scope.editAssign = function () {
        var due_date_time = $scope.assign.due_date + ' ' + $scope.assign.due_time
        var lock_date_time = $scope.assign.lock_date + ' ' + $scope.assign.lock_time
        var updatedAssign = {}
        if (!$scope.assign.autograding_enabled) {
          updatedAssign = {
            'id': $scope.assign.id,
            'display_name': $scope.assign.display_name,
            'name': $scope.assign.endpoint,
            'points': $scope.assign.points,
            'max_group_size': $scope.assign.max_group_size,
            'due_date': due_date_time,
            'course': $scope.assign.course.id,
            'revision': $scope.assign.revisions,
            'lock_date': lock_date_time,
            'url': $scope.assign.url
          }
        } else {
          if (!$scope.assign.autograding_key) {
            $window.swal("No Autograding Key!", 'Please enter the autograder key or disable autograding', 'error');
            return;
          }
          updatedAssign = {
            'id': $scope.assign.id,
            'display_name': $scope.assign.display_name,
            'name': $scope.assign.endpoint,
            'points': $scope.assign.points,
            'max_group_size': $scope.assign.max_group_size,
            'due_date': due_date_time,
            'course': $scope.assign.course.id,
            'revision': $scope.assign.revisions,
            'lock_date': lock_date_time,
            'autograding_enabled': $scope.assign.autograding_enabled,
            'autograding_key': $scope.assign.autograding_key,
            'url': $scope.assign.url
          }
        }
        Assignment.edit(updatedAssign,
          function (response) {
            $scope.assignments = Assignment.query({},
              function (response) {
              $window.swal("Assignment Updated!",'','success');
              $state.transitionTo('course.assignment.list', {courseId: $scope.course.id}, {'reload': true})
            });
          }, function(err) {
               report_error($window, err);
           }
        )

    }
  }
  ]);

app.controller("AssignmentQueueListCtrl", ["$scope", "$window", "$state", "$stateParams", "Assignment", "Course", "Queues",
  function ($scope, $window, $state, $stateParams, Assignment, Course, Queues) {
    Course.get({
      id: $stateParams.courseId
    }, function(response) {
      $scope.course = response;
    });

    // combine into one call?
    $scope.reloadAssignment = function() {
      Assignment.get({
        id: $stateParams.assignmentId
      }, function (response) {
        $scope.assignment = response;
      }, function (err) {
        $window.swal('Error', 'Could not load assignment. Wrong page?', 'error')
       });
    }
    $scope.reloadQueues = function() {
        Assignment.queues({
            id: $stateParams.assignmentId
        },function (response) {
            $scope.queues = response;
        }, function (err) {
            $window.swal('Error', 'Could not load queues. Maybe none exist?', 'error')
        });
    }

    $scope.generateQueues = function() {
        Queues.generate({
            course: $scope.course.id,
            assignment: $scope.assignment.id
        }, function (response) {
            $window.swal('Success', 'Queues generated', 'success');
            $scope.queues = response;
        }, function (err) {
            $window.swal('Error', 'Queues could not be generated.', 'error');
        });
    }

    $scope.reloadAssignment();
    $scope.reloadQueues();
}])

app.controller("AssignmentQueueGenerateCtrl", ["$scope", "$window", "$state", "$stateParams", "Assignment", "Course", "Queues",
  function ($scope, $window, $state, $stateParams, Assignment, Course, Queues) {
    $scope.newQs = {
        'students': '*',
        'staff': '*'
    }

    Course.get({
      id: $stateParams.courseId
    }, function(response) {
      $scope.course = response;
      $scope.hideStaffList();
    });

    $scope.hideStaffList = function hideStaffList() {
        $scope.stafflist = $scope.selection = [];
    }

    $scope.showStaffList = function showStaffList() {
        Course.staff({
            id: $stateParams.courseId
        },function (response) {
            $scope.stafflist = [];
            for (var i = 0;i<response.length;i++) {
                var instructor = response[i];
                var email = instructor.user.email[0];
                if ($scope.stafflist.indexOf(email) == -1) {
                    $scope.stafflist.push(email);
                }
            }
            $scope.selection = $scope.stafflist.slice();
        });
    }

    // http://stackoverflow.com/a/14520103/4855984
    $scope.toggleSelection = function toggleSelection(staffEmail) {
        var idx = $scope.selection.indexOf(staffEmail);

        // is currently selected
        if (idx > -1) {
          $scope.selection.splice(idx, 1);
        }

        // is newly selected
        else {
          $scope.selection.push(staffEmail);
        }
      };

    $scope.reloadAssignment = function() {
      Assignment.get({
        id: $stateParams.assignmentId
      }, function (response) {
        $scope.assignment = response;
      }, function (err) {
        $window.swal('Error', 'Could not load assignment. Wrong page?', 'error')
       });
    }

    $scope.generateQs = function() {
        var staff = $scope.selection.length > 0 ? $scope.selection : $scope.newQs.staff.split(',');
        console.log(staff);
        Queues.generate({
            course: $scope.course.id,
            assignment: $scope.assignment.id,
//            students: [$scope.newQs.students],
            staff: staff
        }, function (response) {
            $window.swal('Success', 'Queues generated', 'success');
            $state.transitionTo("course.assignment.queue.list", {'courseId': $scope.course.id, 'assignmentId': $scope.assignment.id}, {'reload': true});
        }, function (err) {
            $window.swal('Error', 'Queues could not be generated.', 'error');
        });
    }

    $scope.reloadAssignment();
}]);

app.controller("SubmissionDashboardController", ["$scope", "$window", "$state", "Submission",
  function ($scope, $window, $state, Submission) {
    $scope.itemsPerPage = 3;
    $scope.currentPage = 1;
    $scope.getPage = function(page) {
      Submission.query({
        user: '',
        page: page,
        num_page: $scope.itemsPerPage,
        "messages.kind": "file_contents"
      }, function(response) {
        $scope.submissions = response.data.results;
        $scope.clicked = false;
        if (response.data.more) {
          $scope.totalItems = $scope.currentPage * $scope.itemsPerPage + 1;
        } else {
          $scope.totalItems = ($scope.currentPage - 1) * $scope.itemsPerPage + response.data.results.length;
        }
      }, function(err) {
           report_error($window, err);
       });
    }

    $scope.pageChanged = function() {
      $scope.getPage($scope.currentPage);
    }
    $scope.getPage(1);
  }
  ]);

app.controller("FinalSubmissionCtrl", ['$scope', '$location', '$stateParams', '$sessionStorage', '$window', '$state', '$anchorScroll','FinalSubmission', 'Submission',
  function($scope, $location, $stateParams, $sessionStorage, $window, $state, $anchorScroll, FinalSubmission,Submission) {
    FinalSubmission.get({
      id: $stateParams.finalId
    }, function (response){
      $scope.finalSubmission = response;
      $scope.submission = response.submission;
      $scope.backupId = response.submission.backup.id;
      $scope.diff = Submission.diff({id: $scope.backupId});

      if (response.submission.score.length > 0) {
        $scope.compScore = response.submission.score[0].score
        $scope.compMessage = response.submission.score[0].message
      } else {
        $scope.compScore = null;
        $scope.compMessage = null;
      }
    }, function(err) {
         report_error($window, err);
     });
    $scope.storage = $sessionStorage
    $scope.hideEmpty = false;
    $scope.toggleBlank = function () {
      $scope.hideEmpty = !$scope.hideEmpty;
    }

    if ($scope.storage.currentQueue) {
      var queue = JSON.parse($scope.storage.currentQueue);
      submissions = [];
      $scope.queueId = queue['id'];
      var submDict = queue['submissions']
      for (var key in submDict) {
       submissions.push(submDict[key]['id']);
     }
     var currSubm = submissions.indexOf(parseInt($stateParams.finalId));

     $scope.allSubmissions = submissions;
     $scope.currentPage = currSubm;
     $scope.totalItems = submissions.length;
     if (currSubm > 0) {
      $scope.prevId = submissions[currSubm-1];
    }
    if (currSubm > -1 && currSubm < submissions.length - 1) {
      $scope.nextId = submissions[currSubm+1];
    }

  }

  $scope.submitGrade = function() {
    Submission.addScore({
      id: $scope.backupId,
      submission: $scope.submission.id,
      score: $scope.compScore,
      message: $scope.compMessage,
      key: "composition"
    }, function (resp) {
      $scope.goTo($scope.nextId)
    }, function(err) {
         report_error($window, err);
     });
  }

    // Goes to the next submission
    $scope.goTo = function (finalSubm) {
      if (finalSubm != undefined) {
        $state.transitionTo("submission.final", { finalId: finalSubm});
     } else if ($scope.queueId != undefined) {
        // No more items. Show a success message.
        $window.swal({ title: "Nice work!", type: 'success',  text: "Great progress so far!",   timer: 2500 });
        // $location.path('/queue/'+$scope.queueId)
        $state.transitionTo("queue.detail", { queueId: $scope.queueId});
      } else {
        $state.transitionTo("queue.list")
      }
    }


  }]);


app.controller("SubmissionListCtrl", ['$scope', '$stateParams', '$window', 'Search', 'Course',
  function($scope, $stateParams, $window, Search, Course) {
    $scope.itemsPerPage = 20;
    $scope.currentPage = 1;
    $scope.query = {
      'string': ''
    }

    $scope.getPage = function(page) {
      Search.query({
        query: $scope.query.string || '',
        page: page,
        num_per_page: $scope.itemsPerPage,
        courseId: $scope.course.id
      }, function(response) {
        $scope.submissions = response.data.results;
        $scope.more = response.data.more;
        if (response.data.more) {
          $scope.totalItems = $scope.currentPage * $scope.itemsPerPage + 1;
        } else {
          $scope.totalItems = ($scope.currentPage - 1) * $scope.itemsPerPage + response.data.results.length;
        }
      }, function(err) {
           report_error($window, err);
       });
    }

    $scope.course = Course.get({
      id: $stateParams.courseId
    }, function(response) {
      if ($stateParams.query) {
        $scope.query.string = $stateParams.query;
        //$scope.getPage(1);
      }
    }, function(err) {
         report_error($window, err);
     });

    $scope.isSubmit = function (submission)  {
      if ('backup' in submission && 'messages' in submission.backup) {
        return 'submit' in submission.backup.messages.file_contents;
      } else {
        if ('messages' in submission){
          return 'submit' in submission.messages.file_contents;
        }
      }
      return false;
    }
    $scope.mergeFS = function (submissions) {
      // Make a FS behave more like a Submission.
      for (var subNum in submissions) {
        var submission = submissions[subNum];
        if (submission.submission) {
          submission['fsid'] = submission['id'];
          for (var attr in submission.submission) {
            submission[attr] = submission['submission'][attr];
          }
        }
      }
      return submissions;
    }
    $scope.pageChanged = function() {
      $scope.getPage($scope.currentPage);
    }

    $scope.search = function() {
      $scope.getPage($scope.currentPage)
    }

    $scope.autogradeSubm = function (subm) {
      var assing = subm.assignment;
      $window.swal({title: "Enter your access token below",
       text: "You can access it by running the following command in an ok folder \n"+
         'python3 -c "import pickle; print(pickle.load(open(\'.ok_refresh\', \'rb\'))[\'access_token\'])"',
       type: "input",
       showCancelButton: true,
       closeOnConfirm: true,
       animation: "slide-from-top",
       inputPlaceholder: "Paste your access token here. format: ya29.longcode"},
       function(inputValue) {
         if (inputValue === false) return false;
         if (inputValue === "") {
           swal.showInputError("You need to write something!");
           return false
         }
         Assignment.autograde({
           id: assign.id,
           grade_final: false,
           subm: subm.id,
           token: inputValue,
         }, function(response) {
            $window.swal('Success', 'Queued for autograding.', 'success');
          }, function(err) {
              report_error($window, err);
          });
        });
      }

    $scope.download_zip = function(query, all, courseId) {
      filename = 'query_(your email)_(current time).zip'
      Search.download_zip({
        query: query,
        all: all,
        courseId: courseId
      }, function(response) {
        $window.swal({
          title: 'Success',
          text:'Saving submissions to ' + response[0] +
          '\n Zip of submissions will be ready in Google Cloud Storage ok_grades_bucket in a few minutes',
          type: 'success',
          confirmButtonText: 'View zip',
          cancelButtonText: 'Not now',
          showCancelButton: true},
          function() {
            $window.location = 'https://console.developers.google.com/storage/browser'+response[0];
          });
      }, function(err) {
        report_error($window, err);
      });
    }
  }]);


app.controller("SubmissionDetailCtrl", ['$scope', '$window', '$location', '$stateParams',  '$timeout', '$anchorScroll', 'Submission',
  function($scope, $window, $location, $stateParams, $timeout, $anchorScroll, Submission) {
    $scope.tagToAdd = "";
    $scope.submission = Submission.get({id: $stateParams.submissionId});
    $scope.validTags = [
    { text: 'Submit' },
    { text: 'Bugs' },
    { text: 'Comments' }
    ];;

    $scope.showInput = false;

    $scope.toggle = function() {
      $scope.showInput = !$scope.showInput;
    };

    $scope.add = function() {
      Submission.addTag({
        id: $stateParams.submissionId,
        tag: $scope.tagToAdd
      }, function() {
        $scope.submission.tags.push($scope.tagToAdd);
      }, function(err) {
           report_error($window, err);
       });
      $scope.toggle();
    }
  }]);

app.controller("TagCtrl", ['$scope', '$window', 'Submission', '$stateParams',
  function($scope, $window, Submission, $stateParams) {
    var submission = $scope.$parent.$parent.$parent.submission;
    $scope.remove = function() {
      Submission.removeTag({
        id: $stateParams.submissionId,
        tag: $scope.tag
      }, function(response) {
      }, function(err) {
           report_error($window, err);
       });
      var index = submission.tags.indexOf($scope.tag);
      submission.tags.splice(index, 1);
    }
  }]);

// Course Controllers
app.controller("CourseListCtrl", ['$scope', 'Course',
  function($scope, Course) {
    $scope.courses = Course.query({});
  }]);

  app.controller("CourseAssignmentListCtrl", ['$scope', '$window', '$http', 'Assignment', 'Course', '$stateParams', '$window',
    function($scope, $window, $http, Assignment, Course, $stateParams, $window) {
    $scope.course = Course.get({id: $stateParams.courseId});
    $scope.reloadView = function() {
       Course.assignments({
        id: $stateParams.courseId
       },function(response) {
         $scope.assignments = response
       }, function(err) {
           report_error($window, err);
       });
     }

     $scope.autograde = function (assign) {
       $window.swal({title: "Enter your access token below",
        text: "You can access it by running the following command in an ok folder \n"+
          'python3 -c "import pickle; print(pickle.load(open(\'.ok_refresh\', \'rb\'))[\'access_token\'])"',
        type: "input",
        showCancelButton: true,
        closeOnConfirm: true,
        animation: "slide-from-top",
        inputPlaceholder: "Paste your access token here. format: ya29.longcode"},
        function(inputValue) {
          if (inputValue === false) return false;
          if (inputValue === "") {
            swal.showInputError("You need to write something!");
            return false
          }
          Assignment.autograde({
            id: assign.id,
            grade_final: true,
            token: inputValue,
          }, function(response) {
             $window.swal('Success', 'Queued for autograding.', 'success');
           }, function(err) {
               report_error($window, err);
           });
         });
       }

      $scope.downloadScores = function(assign) {
        var tmp_name = 'scores_' + assign.course.offering + '_' + assign.display_name + '.csv'
        var filename = tmp_name.replace(/\//g, '_').replace(/ /g, '_')
        Assignment.download_scores({
          id: assign.id
        }, function() {
          $window.swal({
            title: 'Success',
            text:'Writing scores to ' + filename +
            '\n Scores will be ready in Google Cloud Storage ok_grades_bucket in a few minutes',
            type: 'success',
            confirmButtonText: 'View scores',
            cancelButtonText: 'Not now',
            showCancelButton: true},
            function() {
              $window.location = 'https://console.developers.google.com/storage/browser/ok_grades_bucket/';
            });
        }, function(err) {
          report_error($window, err);
        });
      }

     $scope.delete = function(assign) {
      $window.swal({
          title: "Are you sure?",
          text: "You will not be able to recover this assignment!",
          type: "warning",
          showCancelButton: true,
          confirmButtonColor: "#DD6B55",
          confirmButtonText: "Yes, delete it!",
          closeOnConfirm: false,
          html: false
        }, function(){
          $scope.deleteAssignment(assign);
        });
      }

      $scope.deleteAssignment = function(assign) {
        Assignment.delete({
           id: assign.id
         }, function(response) {
           $window.swal('Success', 'Assignment deleted.', 'success');
           $scope.reloadView();
         }, function(err) {
             report_error($window, err);
         });
      }
     $scope.reloadView();
   }]);

app.controller("CourseDetailCtrl", ["$scope", "$window", "$stateParams", "Course",
  function ($scope, $window, $stateParams, Course) {
    $scope.course = Course.get({id: $stateParams.courseId
    }, function(response) {
    }, function(err) {
        report_error($window, err);
    });
  }
  ]);

app.controller("CourseNewCtrl", ["$scope", "$window", "$state", "$window", "Course",
  function ($scope, $window, $state, $window, Course) {
    $scope.course = {};

    $scope.createCourse = function() {
      Course.create({
        'display_name': $scope.course.name,
        'institution': $scope.course.institution,
        'offering': $scope.course.offering,
        'active': true
      },
       function (response) {
         $scope.courses = Course.query({},
          function (response) {
            $window.swal("Course Created!",'','success');
           $state.transitionTo('course.list' , {} , { reload: true, inherit: true, notify: true });
         });
       }, function(err) {
           report_error($window, err);
       })
    };
  }
  ]);



// Staff Controllers
app.controller("StaffListCtrl", ["$scope","$window", "$stateParams", "Course", "User",
  function($scope, $window, $stateParams, Course, User) {
  $scope.course = Course.get({id: $stateParams.courseId});
  $scope.members = Course.staff({id: $stateParams.courseId});
    $scope.remove = function (userEmail) {
      Course.remove_member({
        id: $stateParams.courseId,
        email: userEmail
      }, function() {
        $window.swal("Removed!", "Removed " + userEmail + " from the course staff", "success");
      }, function(err) {
          report_error($window, err);
      });
    };

    }]);

app.controller("StaffDetailCtrl", ["$scope", "$stateParams", "Course", "User",
  function ($scope, $stateParams, Course, User) {
    $scope.course = Course.get({id: $stateParams.courseId});
    $scope.staff = User.get({id: $stateParams.staffId});
    $scope.roles = ['staff', 'admin', 'user'];
    $scope.save = function () {


    };

  }]);

app.controller("StaffAddCtrl", ["$scope", "$state", "$stateParams", "$window", "Course",
  function ($scope, $state, $stateParams, $window, Course) {
    $scope.course = Course.get({id: $stateParams.courseId});
    $scope.roles = ['staff', 'admin', 'user'];
    $scope.newMember = {
      role: 'staff'
    }
    $scope.save = function () {
      Course.add_member({
        id: $stateParams.courseId,
        email: $scope.newMember.email
      }, function() {
        Course.staff({
          id: $scope.course.id
        }, function () {
          $window.swal("Added!", "Added "+$scope.newMember.email+" to the course staff", "success");
          $state.transitionTo('staff.list', {courseId: $scope.course.id}, {'reload': true})
          $scope.newMember.email = "";
        }, function(err) {
            report_error($window, err);
        })
      }, function(err) {
          report_error($window, err);
      });
    };
  }
  ]);


// Student Enrollment Controllers
app.controller("StudentsAddCtrl", ["$scope", "$state", "$stateParams", "$window", "Course",  "User",
function($scope, $state, $stateParams, $window, Course, User) {
  $scope.course = Course.get({id: $stateParams.courseId});
  $scope.newMember = {
    role: 'user'
  }
       $scope.save = function () {
        Course.add_student({
          id: $stateParams.courseId,
          email: $scope.newMember.email
        }, function() {
          Course.students({
            id: $scope.course.id
          }, function () {
            $window.swal("Added!", "Enrolled "+$scope.newMember.email+" in the course.", "success");
            $state.transitionTo('students.list', {courseId: $scope.course.id}, {'reload': true})
            $scope.newMember.email = "";
          })
        }, function(err) {
            report_error($window, err);
        });
      };

      $scope.saves = function () {
        arr = $scope.newMember.emails.split(',');
        $scope.newMember.emails = new Array()
        for (var i=0;i<arr.length;i++) {
          $scope.newMember.emails.push(arr[i].trim());
        }
        Course.add_students({
          id: $stateParams.courseId,
          emails: $scope.newMember.emails
        }, function() {
          Course.students({
            id: $scope.course.id
          }, function () {
            $window.swal("Added!", "Enrolled "+$scope.newMember.emails.toString().substr(1,-1)+" in the course.", "success");
            $state.transitionTo('students.list', {courseId: $scope.course.id}, {'reload': true})
            $scope.newMember.email = "";
          }, function(err) {
              report_error($window, err);
          })
        }, function(err) {
            report_error($window, err);
        });
      };
}]);

app.controller("StudentsListCtrl", ["$scope", "$stateParams", "$window", "Course",
  function($scope, $stateParams, $window, Course) {
    $scope.course = Course.get({id: $stateParams.courseId});
    $scope.members = Course.students({id: $stateParams.courseId});

    $scope.remove = function (userEmail) {
      Course.remove_student({
        id: $stateParams.courseId,
        email: userEmail
      }, function() {
        $window.swal("Removed!", "Removed " + userEmail + " from the course", "success");
        $scope.members = Course.students({id: $stateParams.courseId});
      }, function(err) {
          report_error($window, err);
      });
    };
  }]);

// Diff Controllers
app.controller("SubmissionDiffCtrl", ['$scope', '$location', '$window', '$stateParams',  'Submission',  "$sessionStorage", '$timeout',
  function($scope, $location, $window, $stateParams, Submission, $sessionStorage, $timeout) {
    $scope.diff = Submission.diff({id: $stateParams.submissionId});
    $scope.storage = $sessionStorage;

    Submission.get({
      id: $stateParams.submissionId
    }, function(response) {
      $scope.submission = response;
      if ($scope.submission.compScore == null) {
          $scope.compScore = null;
          $scope.compMessage = null;
        } else {
          $scope.compScore = $scope.submission.compScore.score;
          $scope.compMessage = $scope.submission.compScore.message;
        }
    }, function(error) {
      report_error($window, error);
    });


    if ($scope.storage.currentQueue) {
      var queue = JSON.parse($scope.storage.currentQueue);
      submissions = [];
      $scope.queueId = queue['id'];
      var submDict = queue['submissions']
      for (var key in submDict) {
       submissions.push(submDict[key]['id']);
     }
     var currSubm = submissions.indexOf(parseInt($stateParams.submissionId));

     $scope.allSubmissions = submissions;
     $scope.currentPage = currSubm;
     $scope.totalItems = submissions.length;
     $scope.prevId = submissions[currSubm-1];
     $scope.nextId = submissions[currSubm+1];

   } else {
    $scope.prevId = undefined;
    $scope.nextId = undefined;
  }

  $scope.submitGrade = function() {
    Submission.addScore({
      id: $stateParams.submissionId,
      score: $scope.compScore,
      message: $scope.compMessage
    }, $scope.nextSubm
    , function(err) {
       report_error($window, err);
   });
  }

    // Goes to the next submission
    $scope.nextSubm = function () {
      if ($scope.nextId != undefined) {
       $location.path('/submission/'+$scope.nextId+'/diff');
     } else if ($scope.queueId != undefined) {
        // No more items. Show a success message.
        $window.swal({ title: "Nice work!", type: 'success',  text: "Great progress so far!",   timer: 2500 });
        $location.path('/queue/'+$scope.queueId)
      } else {
        $location.path('/queue/');
      }
    }

    $scope.hideEmpty = false;
    $scope.toggleBlank = function () {
      $scope.hideEmpty = !$scope.hideEmpty;
    }

    // Goes back a page.
    $scope.backPage = function () {
      $timeout(function() {
       $window.history.back();;
     }, 300);
    }
    $scope.refreshDiff = function() {
      $timeout(function() {
        $scope.diff = Submission.diff({id: $stateParams.submissionId});
      }, 300);
    }
  }]);

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

app.controller("DiffController", ["$scope", "$timeout", "$location", "$anchorScroll", "$sce",
  function ($scope, $timeout, $location, $anchorScroll, $sce) {
    contents = [];
    var leftNum = 0, rightNum = 0;
    for (var i = 0; i < $scope.contents.length; i++) {
      codeline = {"type": "line"};
      codeline.start = $scope.contents[i][0];
      codeline.line = $scope.contents[i].slice(2);
      codeline.index = i;
      // Only care about right-num (which is the new-file)
      if ($scope.diff.comments.hasOwnProperty($scope.file_name) && $scope.diff.comments[$scope.file_name].hasOwnProperty(rightNum)) {
        codeline.comments = $scope.diff.comments[$scope.file_name][rightNum]
      }
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
        $(".diff-line-code").each(function(i, elem) {
          hljs.highlightBlock(elem);
        });
        $anchorScroll();
      });
    }
    ]);

app.controller("DiffLineController", ["$scope", "$timeout", "$location", "$anchorScroll", "$sce", "$modal",
  function ($scope, $timeout, $location, $anchorScroll, $sce, $modal) {
    var converter = new Showdown.converter();
    $scope.convertMarkdown = function(text) {
      if (text == "" || text === undefined) {
        return $sce.trustAsHtml("")
      }
      return $sce.trustAsHtml(converter.makeHtml(text));
    }
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
      //$location.hash($scope.anchorId);
      // $anchorScroll();
    }

    $scope.showComment = false;
    $scope.hideBox = false;
    $scope.showWriter = true;
    $scope.toggleComment = function() {
      $scope.showComment = !$scope.showComment;
      $scope.hideBox = !$scope.showComment;
    }
    $scope.toggleBox = function() {
      $scope.hideBox = !$scope.hideBox;
    }
    $scope.toggleWriter = function() {
      $scope.showWriter = !$scope.showWriter;
    }
  }
  ]);

app.controller("CommentController", ["$scope", "$window", "$stateParams", "$timeout", "$modal", "Submission",
  function ($scope, $window, $stateParams, $timeout, $modal, Submission) {
    $scope.remove = function() {
      var modal = $modal.open({
        templateUrl: '/static/partials/common/removecomment.modal.html',
        scope: $scope,
        size: 'sm',
        resolve: {
          modal: function () {
            return modal;
          }
        }
      });
      modal.result.then(function() {
        Submission.deleteComment({
          id: $scope.backupId,
          comment: $scope.comment.id
        }, function (result){
          $scope.toggleBox();
          $scope.toggleComment();
          $scope.toggleWriter();
          document.querySelector('#comment-'+$scope.comment.id).remove();
        }, function(err) {
            report_error($window, err);
        });
      });
    }
  }
  ]);

app.controller("WriteCommentController", ["$scope", "$window", "$sce", "$stateParams", "Submission",
  function ($scope, $window, $sce, $stateParams, Submission) {
    var converter = new Showdown.converter();
    $scope.convertMarkdown = function(text) {
      if (text == "" || text === undefined) {
        return $sce.trustAsHtml("No comment yet...")
      }
      return $sce.trustAsHtml(converter.makeHtml(text));
    }
    $scope.commentText = {text:""}
    $scope.makeComment = function() {
      text = $scope.commentText.text;
      if (text !== undefined && text.trim() != "") {
        Submission.addComment({
          id: $scope.backupId,
          file: $scope.file_name,
          index: $scope.codeline.rightNum - 1,
          message: text,
        }, function (resp) {
          resp.self = true
          if ($scope.codeline.comments) {
            $scope.codeline.comments.push(resp)
          } else {
            $scope.codeline.comments = [resp]
          }
          $scope.toggleWriter()
        }, function(err) {
            report_error($window, err);
        });
      }
    }
  }
  ]);

// Group Controllers
app.controller("GroupController", ["$scope", "$window", "$stateParams", "$window", "$timeout", "Group",
  function ($scope, $window, $stateParams, $window, $timeout, Group) {
    $scope.loadGroup = function() {
      Group.query({assignment: $stateParams.assignmentId}, function(groups) {
        if (groups.length == 1) {
          $scope.group = groups[0];
          $scope.inGroup = true;
        } else {
          $scope.group = undefined;
          $scope.inGroup = false;
        }
      });
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
      }, $scope.refreshGroup
      , function(err) {
        report_error($window, err);
    });
    }
  }
  ]);

app.controller("MemberController", ["$scope", "$window", "$modal", "Group",
  function ($scope, $window, $modal, Group) {
    $scope.remove = function() {
      var modal = $modal.open({
        templateUrl: '/static/partials/common/removemember.modal.html',
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
          member: $scope.member.email,
          id: $scope.group.id
        }, $scope.refreshGroup
        , function(err) {
             report_error($window, err);
         });
      });
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
        }, $scope.refreshGroup
        , function(err) {
           report_error($window, err);
       });
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
        }, function(err) {
            report_error($window, err);
        });
      } else {
      }
    }

    $scope.reject = function(invitation, $event) {
      $event.stopPropagation();
      Group.rejectInvitation({
        id: invitation.id
      }, $scope.refreshInvitations
      , function(err) {
         report_error($window, err);
     });
    }
  }
  ]);


// Version Controllers
app.controller("VersionListCtrl", ['$scope', 'Version',
  function($scope, Version) {
    $scope.versions = Version.query();
  }]);

app.controller("VersionDetailCtrl", ["$scope", "$stateParams", "Version", "$state",
  function ($scope, $stateParams, Version, $state) {
    if ($stateParams.versionId == "new") {
      $state.go("^.new");
      return;
    }

    $scope.version = Version.get({id: $stateParams.versionId});
    $scope.download_link = function(version) {
      return [$scope.version.base_url, version, $scope.version.name].join('/');
    }
  }
  ]);

app.controller("VersionNewCtrl", ["$scope", "$window", "Version", "$state", "$stateParams",
  function ($scope, $window, Version, $state, $stateParams) {
    $scope.versions = {};
    Version.query(function (versions) {
      angular.forEach(versions, function (version) {
        $scope.versions[version.name] = version;
      });
      if ($stateParams.versionId) {
        $scope.version = $scope.versions[$stateParams.versionId] || {};
      }
    });
    delete $scope.versionNames;
    $scope.version = {};
    $scope.version.current = true;

    $scope.$watch('version.name', function (newValue, oldValue) {
      if (newValue in $scope.versions) {
        var existingVersion = $scope.versions[newValue];
        $scope.version.base_url = existingVersion.base_url;
        if (existingVersion.current_version) {
          $scope.version.version = existingVersion.current_version;
          $scope.version.current = true;
        }
      }
      else {
        $scope.version = {name: newValue};
      }
    });

    $scope.save = function() {
      var version = new Version($scope.version);
      if (version.current) {
        version.current_version = version.version;
      }
      var oldVersion = $scope.versions && version.name in $scope.versions;

      if (oldVersion) {
        version.$update({"id": version.name},
          function (resp) {
            $state.go('^.list');
          }, function(err) {
              report_error($window, err);
          }
        );
      }
      else{
        version.$save(function(resp) {
          $state.go('^.list');
        }, function(err) {
             report_error($window, err);
         });
      }
    };
  }
  ]);

app.controller("QueueModuleController", ["$scope", "$window", "Queue",
  function ($scope, $window, Queue) {
    $scope.queues = Queue.get(function (response) {
      $scope.num_submissions = 0;
      res = response['results']
      if (res.length > 0) {
        for (var i = 0; i < res.length; i++) {
          $scope.num_submissions += res[i].submissions.length;
        }
      } else {
        $scope.num_submissions = 0;
      }
    }, function(err) {
        report_error($window, err);
    });
  }]);

app.controller("QueueListCtrl", ['$scope', '$window', 'Queue',
  function($scope, $window, Queue) {
    /* TODO: Fields to this query */
     Queue.get(function (response) {
        $scope.queues = response['results']
      });
     $scope.refresh = function () {
      Queue.pull(function (response) {
          $scope.queues = response['results']
       }, function(err) {
           report_error($window, err);
       });
     }
  }]);

app.controller("UserQueueListCtrl", ["$scope", "Queue", "$window", "$state",
  function($scope, Queue, $window, $state) {

    $scope.queues = Queue.query({
      "owner": $window.keyId
    }, function(response) {
    }, function(err) {
        report_error($window, err);
    });

  }]);

app.controller("QueueDetailCtrl", ["$scope", "Queue", "$window", "Submission", "$stateParams", "$sessionStorage",
  function ($scope, Queue, $window, Submission, $stateParams, $sessionStorage) {
    $scope.$storage = $sessionStorage;
    Queue.pull({
      id: $stateParams.queueId
    }, function (result) {
      $scope.queue = result;
      $scope.assignment = $scope.queue.assignment.id;
      $scope.course = $scope.assignment.course;
      result['submissions'].sort(function(a, b) {
        return a.id - b.id;
      });
      $scope.$storage.currentQueue = JSON.stringify(result);
      $scope.submList = result['submissions'];
    }, function(err) {
        report_error($window, err);
    });


  }]);
