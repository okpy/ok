app.factory('User', ['$resource',
    function($resource) {
      return $resource('api/v1/user/:id', {
        format: "json",
        id: window.user,
      }, {
        get: {
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        invitations: {
          url: 'api/v1/user/:id/invitations',
          isArray: true,
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

app.factory('Assignment', ['$resource',
    function($resource) {
      return $resource('api/v1/assignment/:id', {format: "json"}, {
        query: {
          isArray: false,
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        get: {
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
      });
    }
  ]);

app.factory('Group', ['$resource',
    function($resource) {
      return $resource('api/v1/group/:id', {
        format: "json",
        id: "@id",
      }, {
        query: {
          isArray: true,
          transformResponse: function(response) {
            response = JSON.parse(response);
            if (response.status != 200) {
              return []
            }
            data = response.data
            return data.results;
          }
        },
        get: {
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        addMember: {
          url: 'api/v1/group/:id/add_member',
          method: 'PUT',
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        removeMember: {
          url: 'api/v1/group/:id/remove_member',
          method: 'PUT',
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        acceptInvitation: {
          url: 'api/v1/group/:id/accept_invitation',
          method: 'PUT',
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        rejectInvitation: {
          url: 'api/v1/group/:id/reject_invitation',
          method: 'PUT',
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        }
      });
    }
  ]);

app.factory('Course', ['$resource',
    function($resource) {
      return $resource('api/v1/course/:id', {
        format: "json",
      }, {
        query: {
          isArray: true,
          transformResponse: function(data) {
            return JSON.parse(data).data.results;
          }
        },
        get: {
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
      });
    }
  ]);

app.factory('Version', ['$resource',
    function($resource) {
      return $resource('api/v1/version/:id', {
        format: "json",
      }, {
        query: {
          isArray: true,
          transformResponse: function(data) {
            return JSON.parse(data).data.results;
          }
        },
        get: {
          isArray: false,
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        update: {
          method: "PUT",
          url: "api/v1/version/:id/new",
          params: {}
        }
      });
    }
  ]);

app.factory('Queue', ['$resource',
    function($resource) {
      return $resource('api/v1/queue/:id', {
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
      });
    }
  ]);


