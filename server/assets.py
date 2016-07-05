from flask_assets import Bundle

common_css = Bundle(
    Bundle(
        'css/helper.css',
        'css/main.css',
        'css/highlight.css',
        'css/code.css',
        filters='cssmin',
    ),
    'lib/bootstrap/css/bootstrap.min.css',
    'lib/swal/sweetalert.min.css',
    'css/swal-theme.css',
    output='public/css/common.css'
)

common_js = Bundle(
    'lib/jquery/jquery.min.js',
    'lib/bootstrap/js/bootstrap.min.js',
    'lib/swal/sweetalert.min.js',
    'lib/markdown/markdown.js',
    Bundle(
        'js/main.js',
        filters='jsmin'
    ),
    output='public/js/common.js'
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

landing_css = Bundle(
    'css/landing.css',
    filters='cssmin',
    output='public/css/landing.css'
)

instant_js = Bundle(
    'lib/instantclick/instantclick.min.js',
    output='public/js/instantclick.min.js'
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
    filters='jsmin',
    output='public/js/staff.js'
)
