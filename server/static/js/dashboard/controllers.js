app.controller("AssignmentModuleController", ["$scope", "Assignment",
    function ($scope, Assignment) {
      Assignment.query({
        active: true,
      }, function(response) {
        $scope.assignments = response.results;
      });
    }
  ]);

app.controller("SubmissionDashboardController", ["$scope", "Submission",
    function ($scope, Submission) {
      $scope.itemsPerPage = 2;
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
            'assignment': {
              'name': true,
              'display_name': true,
              'id': true,
            },
          },
          page: page,
          num_page: $scope.itemsPerPage,
        }, function(response) {
          $scope.submissions = response.data.results;
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

app.controller("SubmissionModuleController", ["$scope", "Submission",
    function ($scope, Submission) {
      Submission.query({
        fields: false,
        num_page: 1,
        page: 1,
        stats: true
      }, function(response) {
        $scope.num_submissions = response.data.statistics.total;
      });
    }
  ]);

app.controller("CourseModuleController", ["$scope",
    function ($scope) {
      $scope.course_name = "CS 61A";
      $scope.course_desc = "Structure and Interpretation of Computer Programs";
    }
  ]);

