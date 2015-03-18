app.factory('User', ['$resource',
    function($resource) {
      return $resource('/api/v1/user/:id', {
        format: "json",
        id: window.user,
      }, {
        get: {
          transformResponse: function(data) {
            return JSON.parse(data).data;
          },
          cache: true
        },
        create: {
          method: "POST",
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        invitations: {
          url: '/api/v1/user/:id/invitations',
          isArray: true,
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        finalsub: {
          method: "GET",
          url: '/api/v1/user/:id/final_submission',
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        getBackups: {
          method: "GET",
          isArray: true,
          url: '/api/v1/user/:id/get_backups',
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        getSubmissions: {
          method: "GET",
          isArray: true,
          url: '/api/v1/user/:id/get_submissions',
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
      });
    }
  ]);

app.factory('Submission', ['$resource',
    function($resource) {
      return $resource('/api/v1/submission/:id', {
        format: "json",
        id: "@id",
      }, {
        query: {
        },
        get: {
          transformResponse: function(data) {
            return JSON.parse(data).data;
          },
          cache: true
        },
        diff: {
          url: '/api/v1/submission/:id/diff',
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        addScore: {
          method: "POST",
          url: '/api/v1/submission/:id/score',
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        addComment: {
          method: "POST",
          url: '/api/v1/submission/:id/add_comment',
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        deleteComment: {
          method: "POST",
          url: '/api/v1/submission/:id/delete_comment',
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        addTag: {
          method: "PUT",
          url: '/api/v1/submission/:id/add_tag',
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        removeTag: {
          method: "PUT",
          url: '/api/v1/submission/:id/remove_tag',
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        }
      });
    }
  ]);

app.factory('FinalSubmission', ['$resource',
    function($resource) {
      return $resource('/api/v1/final_submission/:id', {
        format: "json",
        id: "@id"
      }, {
        get: {
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        score: {
          method: "POST",
          url: '/api/v1/final_submission/:id/score',
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
      });
    }
  ]);


app.factory('Assignment', ['$resource',
    function($resource) {
      return $resource('/api/v1/assignment/:id', {
        format: "json",
        id: "@id"
      }, {
        query: {
          isArray: false,
          transformResponse: function(data) {
            return JSON.parse(data).data;
          },
          cache: true
        },
        get: {
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        create: {
          method: "POST",
          url: '/api/v1/assignment',
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        group: {
          url: '/api/v1/assignment/:id/group',
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        invite: {
          method: "POST",
          url: '/api/v1/assignment/:id/invite',
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
      });
    }
  ]);

app.factory('Group', ['$resource',
    function($resource) {
      return $resource('/api/v1/group/:id', {
        format: "json",
          id: "@id"
      }, {
        addMember: {
          url: '/api/v1/group/:id/add_member',
          method: 'PUT',
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        removeMember: {
          url: '/api/v1/group/:id/remove_member',
          method: 'PUT',
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        acceptInvitation: {
          url: '/api/v1/group/:id/accept',
          method: 'PUT',
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        rejectInvitation: {
          url: '/api/v1/group/:id/decline',
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
      return $resource('/api/v1/course/:id', {
        format: "json",
        id: "@id"
      }, {
        query: {
          isArray: true,
          transformResponse: function(data) {
            return JSON.parse(data).data.results;
          },
          cache: true
        },
        get: {
          transformResponse: function(data) {
            return JSON.parse(data).data;
          },
          cache: true
        },
        staff: {
          isArray: true,
          url: '/api/v1/course/:id/get_staff',
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        add_member: {
          method: "POST",
          url: '/api/v1/course/:id/add_staff',
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        remove_member: {
          method: "POST",
          url: '/api/v1/course/:id/remove_staff',
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
      });
    }
  ]);

app.factory('Version', ['$resource',
    function($resource) {
      return $resource('/api/v1/version/:id', {
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
          url: "/api/v1/version/:id/new",
          params: {}
        }
      });
    }
  ]);

app.factory('Queue', ['$resource',
    function($resource) {
      return $resource('/api/v1/queue/:id', {
        id: "@id",
      }, {
        get: {
          cache: true,
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        pull: {
          method: "GET",
          url: "/api/v1/queue/:id",
          cache: false,
          transformResponse: function(data) {
            return JSON.parse(data).data;
          }
        },
        query: {
          isArray: true,
          transformResponse: function(data) {
            return JSON.parse(data).data.results;
          }
        },
      });
    }
  ]);


