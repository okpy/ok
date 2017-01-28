from flask_assets import Bundle

# NOTE: try to avoid use minified libraries here. We'll get better stack traces
# when debugging, and we'll minify them in production anyway.

debug_js = Bundle(
    'https://cdnjs.cloudflare.com/ajax/libs/tota11y/0.1.5/tota11y.js',
    output='public/js/debug.js'
)

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
    'css/swal-theme.css',
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
    'https://cdn.rawgit.com/svbergerem/markdown-it-sanitizer/6efc1722/dist/markdown-it-sanitizer.js',
    'https://wzrd.in/standalone/markdown-it-anchor@2.6.0',
    'https://cdn.ravenjs.com/2.1.0/raven.js',
    'js/main.js',
    filters='jsmin',
    output='public/js/common.js'
)

dropzone_css = Bundle(
    'https://cdnjs.cloudflare.com/ajax/libs/dropzone/4.3.0/dropzone.css',
    'https://cdnjs.cloudflare.com/ajax/libs/pace/1.0.2/themes/blue/pace-theme-loading-bar.css',
    'css/dropzone.css',
    filters='cssmin',
    output='public/css/dropzone.css'
)
dropzone_js = Bundle(
    'https://cdnjs.cloudflare.com/ajax/libs/dropzone/4.3.0/dropzone.js',
    'https://cdnjs.cloudflare.com/ajax/libs/pace/1.0.2/pace.js',
    'js/dropzone.js',
    filters='jsmin',
    output='public/js/dropzone.js'
)

student_css = Bundle(
    'css/student.css',
    filters='cssmin',
    output='public/css/student.css'
)

student_js = Bundle(
    'https://cdnjs.cloudflare.com/ajax/libs/instantclick/3.0.1/instantclick.js',
    'js/student.js',
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
    'https://cdnjs.cloudflare.com/ajax/libs/jquery-steps/1.1.0/jquery.steps.js',
    'https://cdnjs.cloudflare.com/ajax/libs/jquery-validate/1.15.1/jquery.validate.js',
    'js/staff.js',
    'lib/listjs/list.pagination.js',
    'lib/pygal/pygal-tooltips.min.js',
    filters='jsmin',
    output='public/js/staff.js'
)

code_css = Bundle(
    'https://cdn.rawgit.com/jsvine/nbpreview/9da3f2da/css/vendor/notebook.css',
    'css/code.css',
    'css/highlight.css',
    'css/notebook.css',
    filters='cssmin',
    output='public/css/code.css'
)

code_js = Bundle(
    'js/comments.js',
    'js/notebook.js',
    'https://cdn.rawgit.com/okpy/notebookjs/6821d77a/notebook.js',
    'https://cdn.rawgit.com/drudru/ansi_up/32a3c2de/ansi_up.js',
    filters='jsmin',
    output='public/js/code.js'
)
