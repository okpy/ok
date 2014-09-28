app.factory('Assignment', ['$resource',
    function($resource) {
      return $resource('api/v1/assignment/:id', {format: "json"}, {
        query: {
          isArray: false
        },
        get: {
          isArray: false,
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
      });
    }
  ]);

app.factory('Submission', ['$resource',
    function($resource) {
      return $resource('api/v1/submission/:id', {
        format: "json",
        id: "@id",
      }, {
        query: {
        },
        get: {
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        diff: {
          url: 'api/v1/submission/:id/diff',
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        addComment: {
          method: "POST",
          url: 'api/v1/submission/:id/add_comment',
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        deleteComment: {
          method: "POST",
          url: 'api/v1/submission/:id/delete_comment',
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        }
      });
    }
  ]);

