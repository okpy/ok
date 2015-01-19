
app.controller("CourseModuleController", ["$scope",
    function ($scope) {
      $scope.course_name = "CS 61A";
      $scope.course_desc = "Structure and Interpretation of Computer Programs";
    }
  ]);

// Assignment Controllers
app.controller("AssignmentOverviewController", ['$scope', 'Assignment', 'User', '$timeout',
  function($scope, Assignment, User, $timeout) {
      Assignment.query(function(response) {
        $scope.assignments = response.results;
      })}
]);

// Eeek.
app.controller("AssignmentDashController", ['$scope', 'Assignment', 'User', '$timeout',
  function($scope, Assignment, User, $timeout) {
      Assignment.query(function(response) {
        $scope.assignments = response.results;
        for (var i = 0; i < response.results.length; i++) {
          $scope.assignments[i].group = ['Alvin', 'Angie']
          $scope.assignments[i].latestSubm = {'id': 4855443348258816 , 'time': '2016-01-14 18:54:49.591784'}
        }

        $scope.showGroup = function showGroup(id) {
            $('.popups').addClass('active');
            $('.popup').removeClass('active');
            $('.popup.group').addClass('active').removeClass('hide');
            $( ".sortable" ).sortable();
        }

        $scope.showBackups = function showGroup(id) {
            $('.popups').addClass('active');
            $('.popup').removeClass('active');
            $('.popup.backups').addClass('active').removeClass('hide');
        }

        $scope.showSubms = function showGroup(id) {
            $('.popups').addClass('active');
            $('.popup').removeClass('active');
            $('.popup.submissions').addClass('active').removeClass('hide');
        }

        $scope.hidePopups =  function hidePopups() {
            $('.assign').removeClass('s');
            $('.popups').removeClass('active');
            $('.popup').removeClass('active');
            setTimeout(function() {
              $('.popup').addClass('hide');
            },400);
          }

        $scope.showLoader = function showLoader() {
          $('.loader').removeClass('hide');
        }

        $scope.hideLoader = function hideLoader() {
          $('.loader').addClass('done hide');
          setTimeout(function() {
            $('.loader').removeClass('done')
          },800)
        }

      })


    }


]);
