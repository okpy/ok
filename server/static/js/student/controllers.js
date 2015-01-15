
app.controller("CourseModuleController", ["$scope",
    function ($scope) {
      $scope.course_name = "CS 61A";
      $scope.course_desc = "Structure and Interpretation of Computer Programs";
    }
  ]);


// Assignment Controllers
app.controller("AssignmentOverviewController", ['$scope', 'Assignment', 'User', '$timeout',
  function($scope, Assignment, User, $timeout) {
      alert("FOOO!!!!!");
      Assignment.query(function(response) {
        $scope.assignments = response.results;
      })}
]);
