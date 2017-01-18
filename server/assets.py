from flask_assets import Bundle

# NOTE: try to avoid use minified libraries here. We'll get better stack traces
# when debugging, and we'll minify them in production anyway.

landing_css = Bundle(
    'css/landing.css',
    filters='cssmin',
    output='public/css/landing.css'
)

common_css = Bundle(
    'https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.css',
    'https://fonts.googleapis.com/css?family=Quicksand:400,700,300|Lato:300,400,700',
    'https://code.ionicframework.com/ionicons/2.0.1/css/ionicons.css',
    'https://cdnjs.cloudflare.com/ajax/libs/sweetalert/1.1.3/sweetalert.css',
    'css/helper.css',
    'css/main.css',
    'css/highlight.css',
    'css/code.css',
    'css/swal-theme.css',
    'css/notebook.css',
    'lib/notebookjs/notebook.css',
    filters='cssmin',
    output='public/css/common.css'
)

oauth_css = Bundle(
    'css/oauth.css',
    'css/landing.css',
    filters='cssmin',
    output='public/css/oauth.css'
)

common_js = Bundle(
    'https://ajax.googleapis.com/ajax/libs/jquery/2.1.3/jquery.js',
    'https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.js',
    'https://cdnjs.cloudflare.com/ajax/libs/sweetalert/1.1.3/sweetalert.min.js',
    'https://cdnjs.cloudflare.com/ajax/libs/markdown-it/8.0.1/markdown-it.js',
    'https://cdn.rawgit.com/svbergerem/markdown-it-sanitizer/master/dist/markdown-it-sanitizer.js',
    'https://wzrd.in/standalone/markdown-it-anchor@latest',
    'js/main.js',
    'js/notebook.js',
    'lib/notebookjs/notebook.min.js',
    'lib/notebookjs/ansi_up.min.js',
    filters='jsmin',
    output='public/js/common.js'
)

student_css = Bundle(
    'css/student.css',
    filters='cssmin',
    output='public/css/student.css'
)

student_js = Bundle(
    'js/student.js',
    'js/comments.js',
    filters='jsmin',
    output='public/js/student.js'
)

staff_css = Bundle(
    'https://cdnjs.cloudflare.com/ajax/libs/admin-lte/2.3.6/css/AdminLTE.css',
    'https://cdnjs.cloudflare.com/ajax/libs/admin-lte/2.3.6/css/skins/skin-black-light.css',
    'https://cdnjs.cloudflare.com/ajax/libs/bootstrap-datetimepicker/4.17.37/css/bootstrap-datetimepicker.css',
    'css/staff.css',
    'css/jquery.steps.css',
    filters='cssmin',
    output='public/css/staff.css'
)

staff_js = Bundle(
    'https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.14.1/moment.js',
    'https://cdnjs.cloudflare.com/ajax/libs/admin-lte/2.3.6/js/app.js',
    'https://cdnjs.cloudflare.com/ajax/libs/list.js/1.2.0/list.js',
    'https://cdnjs.cloudflare.com/ajax/libs/bootstrap-datetimepicker/4.17.37/js/bootstrap-datetimepicker.min.js',
    'js/staff.js',
    'js/comments.js',
    'lib/listjs/list.pagination.js',
    'lib/pygal/pygal-tooltips.min.js',
    filters='jsmin',
    output='public/js/staff.js'
)
