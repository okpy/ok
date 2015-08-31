
app.controller("CourseModuleController", ["$scope",
    function ($scope) {
      $scope.course_name = "CS 61A";
      $scope.course_desc = "Structure and Interpretation of Computer Programs";
    }
  ]);


// Assignment Controllers
app.controller("AssignmentListCtrl", ['$scope', 'Assignment', 'User', '$timeout',
  function($scope, Assignment, User, $timeout) {
      Assignment.query(function(response) {
        $scope.assignments = response.results;
        var assign_ids = [];

        // hack to store the ids. There is a much better way to do this.
        for (var i = 0; i < response.results.length; i++) {
          assign_ids.push(response.results[i].id);
        }
        for (var i = 0; i < $scope.assignments.length; i++) {
              User.finalsub({
                assignment: $scope.assignments[i].id
              }, function (data) {
                  if (data.assignment){
                    var q = assign_ids.indexOf(data.assignment.id);

                    if (q != -1){
                      $scope.assignments[q].finalsub = data.id;
                    }
                  }
              });

        }
      });

  }]);

app.controller("AssignmentModuleController", ["$scope", "Assignment",
    function ($scope, Assignment) {
      Assignment.query({
        active: true,
      }, function(response) {
        $scope.assignments = response.results;
      });
    }
  ]);


app.controller("AssignmentDetailCtrl", ["$scope", "$stateParams", "Assignment",
    function ($scope, $stateParams, Assignment) {
      $scope.assignment = Assignment.get({id: $stateParams.assignmentId});
    }
  ]);

// Submission Controllers
app.controller("SubmissionListCtrl", ['$scope', "$state", 'Submission',
    function ($scope, $state, Submission) {
    $scope.itemsPerPage = 50;
    $scope.currentPage = 1;
    $scope.getPage = function(page) {
      Submission.query({
        fields: {
          'created': true,
          'db_created': true,
          'id': true,
          'submitter': {
            'id': true
          },
          'tags': true,
          'assignment': {
            'name': true,
            'display_name': true,
            'id': true,
            'active': true,
          },
          'messages': {
            'file_contents': true
          }
        },
        page: page,
        num_page: $scope.itemsPerPage,
        "messages.kind": "file_contents"
      }, function(response) {
        $scope.submissions = response.data.results;
        if (response.data.more) {
          $scope.totalItems = $scope.currentPage * $scope.itemsPerPage + 1;
        } else {
          $scope.totalItems = ($scope.currentPage - 1) * $scope.itemsPerPage + response.data.results.length;
        }
      });
    }
      $scope.clicked = false;

      $scope.submitVersion = function(subm) {
        $scope.clicked = true;
        Submission.addTag({
          id: subm,
          tag: "Submit"
        },$scope.refreshDash);
      }
      $scope.unSubmit = function(subm) {
        $scope.clicked = true;

        Submission.removeTag({
          id: subm,
          tag: "Submit"
        }, $scope.refreshDash);
      }

    $scope.refreshDash = function() {
        $state.go($state.current, {}, {reload: true});
      }



    $scope.pageChanged = function() {
      $scope.getPage($scope.currentPage);
    }
    $scope.getPage(1);
  }]);

app.controller("SubmissionDetailCtrl", ['$scope', '$location', '$stateParams',  '$timeout', '$anchorScroll', 'Submission',
  function($scope, $location, $stateParams, $timeout, $anchorScroll, Submission) {
    $scope.submission = Submission.get({id: $stateParams.submissionId});

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
    $scope.courses = Course.query();
  }]);

app.controller("CourseDetailCtrl", ["$scope", "$stateParams", "Course",
    function ($scope, $stateParams, Course) {
      $scope.course = Course.get({id: $stateParams.courseId});
    }
  ]);

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

// Diff Controllers
app.controller("SubmissionDiffCtrl", ['$scope', '$stateParams',  'Submission', '$timeout',
  function($scope, $stateParams, Submission, $timeout) {
    $scope.diff = Submission.diff({id: $stateParams.submissionId});

    Submission.get({
      id: $stateParams.submissionId
    }, function(response) {
      $scope.submission = response;
    }, function(error) {
      report_error($window, error);
    });

    $scope.hideEmpty = false;
    $scope.toggleBlank = function () {
      $scope.hideEmpty = !$scope.hideEmpty;
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
        if ($scope.diff.comments.hasOwnProperty($scope.file_name) && $scope.diff.comments[$scope.file_name].hasOwnProperty(i)) {
          codeline.comments = $scope.diff.comments[$scope.file_name][i]
        }
        codeline.lineNum = i + 1;
        if (codeline.start == "+") {
          rightNum++;
          codeline.rightNum = rightNum;
          codeline.leftNum = "+";
        } else if (codeline.start == "-") {
          leftNum++;
          codeline.leftNum = leftNum;;
          codeline.rightNum = "-";
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
          })
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
        $location.hash($scope.anchorId);
        $anchorScroll();
      }
      $scope.showComment = false;
      $scope.toggleComment = function(line) {
        $scope.showComment = !$scope.showComment;
      }
    }
  ]);

app.controller("CommentController", ["$scope", "$stateParams", "$timeout", "$modal", "Submission",
    function ($scope, $stateParams, $timeout, $modal, Submission) {
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
            id: $stateParams.submissionId,
            comment: $scope.comment.id
          }, $scope.refreshDiff);
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
      $scope.comment = function() {
        text = $scope.commentText.text;
        if (text !== undefined && text.trim() != "") {
          Submission.addComment({
            id: $stateParams.submissionId,
            file: $scope.file_name,
            index: $scope.codeline.index,
            message: text,
          }, $scope.refreshDiff);
        }
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
          delete version.current;
          version.current_version = version.version;
        }
        var oldVersion = $scope.versions && version.name in $scope.versions;

        if (oldVersion) {
          version.$update({"id": version.name});
        }
        else{
          version.$save();
        }
        $state.go('^.list');
      };
    }
  ]);

app.controller("LandingPageCtrl", ["$window", "$state",
    function ($window, $state) {
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
                $window.location.hash = "";
            } else {
                $window.location.href = $window.reloginLink;
            }
        });
      } else {
          $window.location.hash = "";
      }
    }
]);

app.controller("QueueListCtrl", ['$scope', 'Queue',
  function($scope, Queue) {
    $scope.queues = Queue.query({
        "fields": {
          "assignment": {
            "id": true,
            "display_name": true
          },
          "assigned_staff": {
            "id": true,
            "first_name": true,
            "last_name": true,
            "role": true
          },
          "submissions": true
        }
    });
  }]);
app.controller("QueueDetailCtrl", ["$scope", "Queue", "$stateParams",
    function ($scope, Queue, $stateParams) {
      $scope.queue = Queue.get({
        "fields": {
          "assignment": {
            "id": true,
            "display_name": true
          },
          "assigned_staff": {
            "id": true,
            "first_name": true,
            "last_name": true,
            "role": true
          },
          "submissions": {
            "id": true,
            "assignment": true,
            "compScore": true
          }
        },
        'id': $stateParams.queueId
    });
  }
  ]);
