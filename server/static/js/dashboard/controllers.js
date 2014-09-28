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

app.controller("AssignmentListCtrl", ['$scope', 'Assignment',
  function($scope, Assignment) {
      Assignment.query(function(response) {
        $scope.assignments = response.data.results;
      });
  }]);

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

