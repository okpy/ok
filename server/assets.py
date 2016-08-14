from flask_assets import Bundle

landing_css = Bundle(
    'css/landing.css',
    filters='cssmin',
    output='public/css/landing.css'
)

common_css = Bundle(
    'css/helper.css',
    'css/main.css',
    'css/highlight.css',
    'css/code.css',
    'css/swal-theme.css',
    filters='cssmin',
    output='public/css/common.css'
)

common_js = Bundle(
    'js/main.js',
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
    'css/staff.css',
    filters='cssmin',
    output='public/css/staff.css'
)

staff_js = Bundle(
    'js/staff.js',
    'js/comments.js',
    'lib/listjs/list.fuzzysearch.min.js',
    'lib/pygal/pygal-tooltips.min.js',
    filters='jsmin',
    output='public/js/staff.js'
)
