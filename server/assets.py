from flask_assets import Bundle

# NOTE: try to avoid use minified libraries here. We'll get better stack traces
# when debugging, and we'll minify them in production anyway.

debug_js = Bundle(
    'https://unpkg.com/tota11y@0.1.5/build/tota11y.js',
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
    'https://unpkg.com/ionicons@4.2.4/dist/css/ionicons.css',
    'https://unpkg.com/sweetalert@1.1.3/dist/sweetalert.css',
    'css/helper.css',
    'css/swal-theme.css',
    'lib/datepicker/css/bootstrap-datetimepicker.css',
    'css/main.css',
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
    'https://unpkg.com/sweetalert@1.1.3/dist/sweetalert.min.js',
    'https://unpkg.com/markdown-it@8.0.1/dist/markdown-it.js',
    'https://cdn.rawgit.com/okpy/markdown-it-sanitizer/a328e3d/dist/markdown-it-sanitizer.js',
    'https://cdn.rawgit.com/okpy/markdown-it-anchor/722f7a89/dist/markdown-it-anchor.js',
    'https://cdn.ravenjs.com/2.1.0/raven.js',
    'lib/datepicker/js/moment.js',
    'lib/datepicker/js/collapse.js',
    'lib/datepicker/js/transition.js',
    'lib/datepicker/js/bootstrap-datetimepicker.min.js',
    'js/main.js',
    filters='jsmin',
    output='public/js/common.js'
)

dropzone_css = Bundle(
    'https://unpkg.com/dropzone@4.3.0/dist/dropzone.css',
    'css/dropzone.css',
    filters='cssmin',
    output='public/css/dropzone.css'
)
dropzone_js = Bundle(
    'https://unpkg.com/dropzone@4.3.0/dist/dropzone.js',
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
    'https://unpkg.com/instantclick@3.1.0/instantclick.js',
    'js/student.js',
    filters='jsmin',
    output='public/js/student.js'
)

staff_css = Bundle(
    'https://unpkg.com/admin-lte@2.3.6/dist/css/AdminLTE.css',
    'https://unpkg.com/admin-lte@2.3.6/dist/css/skins/skin-black-light.css',
    'https://unpkg.com/eonasdan-bootstrap-datetimepicker@4.17.47/build/css/bootstrap-datetimepicker.css',
    'css/staff.css',
    'css/jquery.steps.css',
    filters='cssmin',
    output='public/css/staff.css'
)

staff_js = Bundle(
    'https://unpkg.com/moment@2.14.1/moment.js',
    'https://unpkg.com/admin-lte@2.3.6/dist/js/app.js',
    'https://unpkg.com/list.js@1.2.0/dist/list.js',
    'https://unpkg.com/eonasdan-bootstrap-datetimepicker@4.17.47/src/js/bootstrap-datetimepicker.js',
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
    'https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.7.1/katex.min.js',
    'https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.7.1/contrib/auto-render.min.js',
    'https://cdn.rawgit.com/okpy/notebookjs/4bea3da/notebook.js',
    'https://cdn.rawgit.com/drudru/ansi_up/32a3c2de/ansi_up.js',
    filters='jsmin',
    output='public/js/code.js'
)
