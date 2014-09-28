app.controller("AssignmentModuleController", ["$scope", "Assignment",
    function ($scope, Assignment) {
      Assignment.query(function(response) {
        $scope.assignments = response.data.results;
      });
    }
  ]);

app.controller("SubmissionModuleController", ["$scope", "Submission",
    function ($scope, Submission) {
      Submission.query(function(response) {
        $scope.Submissions = response.data.results;
      });
    }
  ]);

