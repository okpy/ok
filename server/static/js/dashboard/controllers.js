app.controller("AssignmentModuleController", ["$scope", "Assignment",
    function ($scope, Assignment) {
      Assignment.query({
        active: true,
      }, function(response) {
        $scope.assignments = response.results;
      });
    }
  ]);

app.controller("SubmissionModuleController", ["$scope", "Submission",
    function ($scope, Submission) {
      Submission.query(function(response) {
        $scope.submissions = response.data.results;
      });
    }
  ]);

