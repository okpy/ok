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

instant_js = Bundle(
    'lib/instantclick/instantclick.min.js',
    output='public/js/instantclick.min.js'
)

staff_css = Bundle(
    'css/staff.css',
    filters='cssmin',
    output='public/css/staff.css'
)

staff_js = Bundle(
    'js/staff.js',
    'js/comments.js',
    filters='jsmin',
    output='public/js/staff.js'
)

list_js = Bundle(
    'lib/listjs/list.js',
    'lib/listjs/list.fuzzysearch.min.js',
    'lib/listjs/list.pagination.js',
    filters='jsmin',
    output='public/js/list.js'
)

adminlte_css = Bundle(
    'lib/admin/css/AdminLTE.min.css',
    'lib/admin/css/skins/skin-black-light.min.css',
    'lib/admin/plugins/pace/pace.min.css',
    filters='cssmin',
    output='public/css/adminlte.css'
)

adminlte_js = Bundle(
    'lib/admin/js/app.min.js',
    'lib/admin/plugins/pace/pace.min.js',
    'lib/admin/plugins/fastclick/fastclick.min.js',
    output='public/js/adminlte.js'
)

pygal_js = Bundle(
    'lib/pygal/pygal-tooltips.min.js',
    'lib/pygal/svg.jquery.js',
    output='public/js/pygal.js'
)

upload_css = Bundle(
    'lib/dropzone/dropzone.css',
    'css/upload.css',
    filters='cssmin',
    output='public/js/upload.css'
)

upload_js = Bundle(
    'lib/dropzone/dropzone.js',
    'js/upload.js',
    filters='jsmin',
    output='public/js/upload.js'
)
