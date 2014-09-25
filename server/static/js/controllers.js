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

app.controller("CourseNewCtrl", ["$scope", "Course", "$state", 
    function ($scope, Course, $state) {
      $scope.courses = Course.query();
      $scope.course = {};

      $scope.save = function() {
        var course = new Course($scope.course);
        var oldCourse = $scope.courses && course.name in $scope.courses;

        if (oldCourse) {
          course.$update({"id": course.name});
        }
        else{
          course.$save();
        }
        $state.go('^.list');
      };
    }
  ]);

app.controller("AssignmentListCtrl", ['$scope', 'Assignment',
  function($scope, Assignment) {
    $scope.assignments = Assignment.query();
  }]);

app.controller("AssignmentDetailCtrl", ["$scope", "$stateParams", "Assignment", "$state", 
    function ($scope, $stateParams, Assignment, $state) { 
      if ($stateParams.assignmentId == "new") {
        $state.go("^.new");
        return;
      }

      $scope.assignment = Assignment.get({id: $stateParams.assignmentId});
    }
  ]);

app.controller("AssignmentNewCtrl", ['$scope', 'Assignment', 'Course', '$state', 
  function($scope, Assignment, Course, $state) {
    $scope.assignments = Assignment.query();
    $scope.courses = Course.query();

    $scope.save = function() {
      var assignment = new Assignment($scope.assignment);

      var oldAssignment = $scope.assignments && assignment.name in $scope.assignment;

      if (oldAssignment) {
        assignment.$update({"id": assignment.id});
      }
      else{
        assignment.$save();
      }
      $state.go('^.list');
    };
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

function DropdownCtrl($scope) {
  $scope.status = {
    isopen: false
  };
}
