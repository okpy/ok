function defaultTransformer(data) {
  json = JSON.parse(data);
  if (json.status == '200') {
    return json.data;
  } else {
    if (json.status == '500') {
      if (json.message == 'internal server error :(') {
        json.message = 'An uncaught error or exception has been thrown. If this is urgent, please contact your instructors.'
      }
      return json;
    }
    return json;
  }
}

app.factory('User', ['$resource',
    function($resource) {
      return $resource('/api/v1/user/:id', {
        format: "json",
        id: window.user,
      }, {
        get: {
          transformResponse: defaultTransformer,
          cache: true
        },
        force_get: {
          method: "GET",
          transformResponse: defaultTransformer,
          cache: false
        },
        create: {
          method: "POST",
          transformResponse: defaultTransformer
        },
        invitations: {
          url: '/api/v1/user/:id/invitations',
          isArray: true,
          transformResponse: defaultTransformer
        },
        finalsub: {
          method: "GET",
          url: '/api/v1/user/:id/final_submission',
          transformResponse: defaultTransformer
        },
        getBackups: {
          method: "GET",
          isArray: true,
          url: '/api/v1/user/:id/get_backups',
          transformResponse: defaultTransformer
        },
        getSubmissions: {
          method: "GET",
          isArray: true,
          url: '/api/v1/user/:id/get_submissions',
          transformResponse: defaultTransformer
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
          transformResponse: defaultTransformer,
          cache: true
        },
        diff: {
          url: '/api/v1/submission/:id/diff',
          transformResponse: defaultTransformer
        },
        addScore: {
          method: "POST",
          url: '/api/v1/submission/:id/score',
          transformResponse: defaultTransformer
        },
        addComment: {
          method: "POST",
          url: '/api/v1/submission/:id/add_comment',
          transformResponse: defaultTransformer
        },
        deleteComment: {
          method: "POST",
          url: '/api/v1/submission/:id/delete_comment',
          transformResponse: defaultTransformer
        },
        addTag: {
          method: "PUT",
          url: '/api/v1/submission/:id/add_tag',
          transformResponse: defaultTransformer
        },
        removeTag: {
          method: "PUT",
          url: '/api/v1/submission/:id/remove_tag',
          transformResponse: defaultTransformer
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
          transformResponse: defaultTransformer
        },
        post: {
          method: 'POST',
          transformResponse: defaultTransformer
        }
      })
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
          transformResponse: defaultTransformer,
          cache: true
        },
        get: {
          transformResponse: defaultTransformer
        },
        create: {
          method: "POST",
          url: '/api/v1/assignment',
          transformResponse: defaultTransformer
        },
        edit: {
          method: "POST",
          url: '/api/v1/assignment/:id/edit',
          transformResponse: defaultTransformer
        },
        group: {
          url: '/api/v1/assignment/:id/group',
          transformResponse: defaultTransformer
        },
        autograde: {
          method: "POST",
          url: '/api/v1/assignment/:id/autograde',
          transformResponse: defaultTransformer
        },
        invite: {
          method: "POST",
          url: '/api/v1/assignment/:id/invite',
          transformResponse: defaultTransformer
        },
        queues: {
          isArray:true,
          url: '/api/v1/assignment/:id/queues',
          transformResponse: defaultTransformer
        }
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
          transformResponse: defaultTransformer
        },
        removeMember: {
          url: '/api/v1/group/:id/remove_member',
          method: 'PUT',
          transformResponse: defaultTransformer
        },
        acceptInvitation: {
          url: '/api/v1/group/:id/accept',
          method: 'PUT',
          transformResponse: defaultTransformer
        },
        rejectInvitation: {
          url: '/api/v1/group/:id/decline',
          method: 'PUT',
          transformResponse: defaultTransformer
        },
        reorder: {
          url: '/api/v1/group/:id/reorder',
          method: 'PUT',
          transformResponse: defaultTransformer
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
        create: {
          method: "POST",
          url: '/api/v1/course',
          transformResponse: defaultTransformer
        },
        get: {
          transformResponse: defaultTransformer,
          cache: true
        },
        assignments: {
           isArray: true,
           url:'/api/v1/course/:id/assignments',
           transformResponse: defaultTransformer
        },
        staff: {
          isArray: true,
          url: '/api/v1/course/:id/get_staff',
          transformResponse: defaultTransformer
        },
        students: {
          isArray: true,
          url: '/api/v1/course/:id/get_students',
         transformResponse: defaultTransformer
        },
        add_member: {
          method: "POST",
          url: '/api/v1/course/:id/add_staff',
          transformResponse: defaultTransformer
        },
        remove_member: {
          method: "POST",
          url: '/api/v1/course/:id/remove_staff',
          transformResponse: defaultTransformer
        },
        add_student: {
          method: "POST",
          url: '/api/v1/course/:id/add_student',
          transformResponse: defaultTransformer
        },
        add_students: {
          method: "POST",
          url: '/api/v1/course/:id/add_students',
          transformResponse: defaultTransformer
        },
        remove_student: {
          method: "POST",
          url: '/api/v1/course/:id/remove_student',
          transformResponse: defaultTransformer
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
          transformResponse: defaultTransformer
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
          transformResponse: defaultTransformer
        },
        pull: {
          method: "GET",
          url: "/api/v1/queue/:id",
          cache: false,
          transformResponse: defaultTransformer
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


app.factory('Search', ['$resource',
    function($resource) {
      return $resource('/api/v1/search', {
        }, {
          query: {
            url: '/api/v1/search',
            transformResponse: defaultTransformer
          }
        }
      )
    }
  ]);

app.factory('Queues', ['$resource',
    function($resource) {
      return $resource('/api/v1/queues', {
        }, {
          generate: {
            isArray:true,
            method: 'POST',
            url: '/api/v1/queues/generate',
            transformResponse: function(data) {
              return JSON.parse(data).data;
            }
          }
        }
      )
    }
  ]);
