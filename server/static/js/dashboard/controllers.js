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
      Submission.query({
        fields: {
          'created': true,
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
        page: 1,
        num_page: 2,
      }, function(response) {
        $scope.submissions = response.data.results;
      });
    }
  ]);

app.controller("SubmissionModuleController", ["$scope", "Submission",
    function ($scope, Submission) {
      Submission.query({
        fields: false,
      }, function(response) {
        $scope.submissions = response.data.results;
      });
    }
  ]);

