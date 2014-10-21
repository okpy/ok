app.controller("SubmissionDashboardController", ["$scope", "$state", "Submission",
    function ($scope, $state, Submission) {
      $scope.itemsPerPage = 3;
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
            'file_contents': "presence"
          }
        },
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
    }
  ]);


