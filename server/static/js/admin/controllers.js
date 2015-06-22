// Admin Sidebar
app.controller("SidebarCntrl", ['$scope', 'Assignment',
  function($scope, Assignment) {
    Assignment.query(function(response) {
      $scope.assignments = response.results;
    });
    $scope.course_name = "Ok Admin"
  }]);

// Submission Controllers
app.controller("SubmissionModuleController", ["$scope", "Submission",
  function ($scope, Submission) {
    Submission.query(function(response) {
      $scope.num_submissions = response.results.length;
    });
  }
  ]);


// Assignment Controllers
app.controller("AssignmentModuleController", ["$scope", "Assignment",
  function ($scope, Assignment) {
    Assignment.query(function(response) {
      $scope.assignments = response.results;
    });
  }
  ]);

app.controller("AssignmentDetailCtrl", ["$scope", "$stateParams", "Assignment",
  function ($scope, $stateParams, Assignment) {
    $scope.assignment = Assignment.get({id: $stateParams.assignmentId});
  }
  ]);

app.controller("AssignmentCreateCtrl", ["$scope", "$window", "$state", "$stateParams", "Assignment", "Course",
  function ($scope, $window, $state, $stateParams, Assignment, Course) {
    $scope.existingAssign = Assignment.get({id: $stateParams.assignmentId});
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
      'autograding_enabled': true
    };
    Course.get({
      id: $stateParams.courseId
    }, function(response) {
      $scope.course = response;
    });
    // TODO: only allow user to create assignment for specified course - no more dropdown!
    Course.get({}, function(resp) {
        $scope.courses = resp.results;
        $scope.newAssign.course = $scope.courses[0];
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
          'grading_script_file': $scope.newAssign.grading_script_file,
          'zip_file_url': $scope.newAssign.zip_file_url,
          'access_token': $scope.newAssign.access_token
        },
          function (response) {
            $scope.courses = Course.query({},
              function (response) {
                $window.swal("Assignment Created!",'','success');
               $state.transitionTo('course.assignment.list' , {courseId: $scope.course.id} , { reload: true, inherit: true, notify: true });
             });
          }, function (error) {
            console.log('error')
            $window.swal("Could not create assignment",'There was an error','error');

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
    });

    $scope.reloadAssignment = function() {
      Assignment.get({
        id: $stateParams.assignmentId
      }, function (response) {
        $scope.initAssignment(response);
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
      });
    }

    $scope.reloadAssignment();

    $scope.editAssign = function () {
        var due_date_time = $scope.assign.due_date + ' ' + $scope.assign.due_time
        var lock_date_time = $scope.assign.lock_date + ' ' + $scope.assign.lock_time
        Assignment.edit({
          'id': $scope.assign.id,
          'display_name': $scope.assign.display_name,
          'name': $scope.assign.endpoint,
          'points': $scope.assign.points,
          'max_group_size': $scope.assign.max_group_size,
          'templates': {},
          'due_date': due_date_time,
          'course': $scope.assign.course.id,
          'revision': $scope.assign.revisions,
          'lock_date': lock_date_time,
          'autograding_enabled': $scope.assign.autograding_enabled,
          'grading_script_file': $scope.assign.grading_script_file,
          'zip_file_url': $scope.assign.zip_file_url,
          'access_token': $scope.assign.access_token
        },
          function (response) {
            $scope.assignments = Assignment.query({},
              function (response) {
              $window.swal("Assignment Updated!",'','success');
              $state.transitionTo('course.assignment.list', {courseId: $scope.course.id}, {'reload': true})
            });
          }, function (error) {
            console.log('error')
            $window.swal("Could not update assignment",'There was an error','error');

          }
        )

    }
  }
  ]);

app.controller("SubmissionDashboardController", ["$scope", "$state", "Submission",
  function ($scope, $state, Submission) {
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
    FinalSubmission.score({
      id: $stateParams.finalId,
      score: $scope.compScore,
      message: $scope.compMessage,
      source: "composition"
    }, $scope.goTo($scope.nextId));
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
        $scope.search_query = encodeURIComponent(response.data.query);
        if (response.data.more) {
          $scope.totalItems = $scope.currentPage * $scope.itemsPerPage + 1;
        } else {
          $scope.totalItems = ($scope.currentPage - 1) * $scope.itemsPerPage + response.data.results.length;
        }
      }, function(err) {
        $window.swal('Uh oh', 'We couldn\'t complete the search. Remember that your query must have valid flags.', 'error');
      });
    }

    $scope.course = Course.get({id: $stateParams.courseId});

    $scope.pageChanged = function() {
      $scope.getPage($scope.currentPage);
    }

    $scope.search = function() {
      $scope.getPage($scope.currentPage)
    }
  }]);


app.controller("SubmissionDetailCtrl", ['$scope', '$location', '$stateParams',  '$timeout', '$anchorScroll', 'Submission',
  function($scope, $location, $stateParams, $timeout, $anchorScroll, Submission) {
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
      });
      $scope.toggle();
    }
  }]);

app.controller("TagCtrl", ['$scope', 'Submission', '$stateParams',
  function($scope, Submission, $stateParams) {
    var submission = $scope.$parent.$parent.$parent.submission;
    $scope.remove = function() {
      Submission.removeTag({
        id: $stateParams.submissionId,
        tag: $scope.tag
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

  app.controller("CourseAssignmentListCtrl", ['$scope', '$http', 'Assignment', 'Course', '$stateParams', '$window',
    function($scope, $http, Assignment, Course, $stateParams, $window) {
    $scope.course = Course.get({id: $stateParams.courseId});
    $scope.reloadView = function() {
       Course.assignments({
        id: $stateParams.courseId
       },function(response) {
         $scope.assignments = response
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
         }, function(error) {
          $window.swal('Error', 'Could not delete assignment.', 'error')
         });
      }
      
     $scope.reloadView();
   }]);

app.controller("CourseDetailCtrl", ["$scope", "$stateParams", "Course",
  function ($scope, $stateParams, Course) {
    $scope.course = Course.get({id: $stateParams.courseId});
  }
  ]);

app.controller("CourseNewCtrl", ["$scope", "$state", "$window", "Course",
  function ($scope, $state, $window, Course) {
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
       }, function (error) {
         $window.swal("Could not create course",'There was an error','error');

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
        })
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
        }, function() {
          $window.swal("Oops", "Could not enroll student", 'error')
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
          })
        }, function() {
          $window.swal("Oops", "Could not enroll student", 'error')
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
      });
    };
  }]);

// Diff Controllers
app.controller("SubmissionDiffCtrl", ['$scope', '$location', '$window', '$stateParams',  'Submission',  "$sessionStorage", '$timeout',
  function($scope, $location, $window, $stateParams, Submission, $sessionStorage, $timeout) {
    $scope.diff = Submission.diff({id: $stateParams.submissionId});
    $scope.storage = $sessionStorage;

    $scope.submission = Submission.get({
      fields: {
        created: true,
        compScore: true,
        tags: true,
        message: true
      }
    }, {
      id: $stateParams.submissionId
    }, function () {
      if ($scope.submission.compScore == null) {
        $scope.compScore = null;
        $scope.compMessage = null;
      } else {
        $scope.compScore = $scope.submission.compScore.score;
        $scope.compMessage = $scope.submission.compScore.message;
      }
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
     console.log(currSubm)
     console.log(submissions)

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
    }, $scope.nextSubm);
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
          $scope.toggleBox()
          $scope.comment = false;
        });
      });
    }
  }
  ]);

app.controller("WriteCommentController", ["$scope", "$sce", "$stateParams", "Submission",
  function ($scope, $sce, $stateParams, Submission) {
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
        });
      }
    }
  }
  ]);

// Group Controllers
app.controller("GroupController", ["$scope", "$stateParams", "$window", "$timeout", "Group",
  function ($scope, $stateParams, $window, $timeout, Group) {
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
      }, $scope.refreshGroup);
    }
  }
  ]);

app.controller("MemberController", ["$scope", "$modal", "Group",
  function ($scope, $modal, Group) {
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

app.controller("VersionNewCtrl", ["$scope", "Version", "$state", "$stateParams",
  function ($scope, Version, $state, $stateParams) {
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
          }, function (err) {
            alert(err);
          }
        );
      }
      else{
        version.$save(function(resp) {
          $state.go('^.list');
        });
      }
    };
  }
  ]);

app.controller("QueueModuleController", ["$scope", "Queue",
  function ($scope, Queue) {
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
    });
  }]);

app.controller("QueueListCtrl", ['$scope', 'Queue',
  function($scope, Queue) {
    /* TODO: Fields to this query */
     Queue.get(function (response) {
        $scope.queues = response['results']
      });
     $scope.refresh = function () {
      Queue.pull(function (response) {
          $scope.queues = response['results']
       });
     }
  }]);

app.controller("UserQueueListCtrl", ["$scope", "Queue", "$window", "$state",
  function($scope, Queue, $window, $state) {

    $scope.queues = Queue.query({
      "owner": $window.keyId
    });

  }]);

app.controller("QueueDetailCtrl", ["$scope", "Queue", "Submission", "$stateParams", "$sessionStorage",
  function ($scope, Queue, Submission, $stateParams, $sessionStorage) {
    $scope.$storage = $sessionStorage;
    Queue.pull({
      id: $stateParams.queueId
    }, function (result) {
      $scope.queue = result;
      result['submissions'].sort(function(a, b) {
        return a.id - b.id;
      });
      $scope.$storage.currentQueue = JSON.stringify(result);
      $scope.submList = result['submissions'];
    });


  }]);
