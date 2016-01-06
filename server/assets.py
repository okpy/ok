from flask_assets import Bundle

common_css = Bundle(
    Bundle(
        'css/helper.css',
        'css/main.css',
        filters='cssmin',
    ),
    'lib/bootstrap/css/bootstrap.min.css',
    output='public/css/common.css'
)

common_js = Bundle(
    'lib/jquery/jquery.min.js',
    'lib/bootstrap/js/bootstrap.min.js',
    Bundle(
        'js/main.js',
        filters='jsmin'
    ),
    output='public/js/common.js'
)

adminlte_css = Bundle(
    'lib/admin/css/AdminLTE.min.css',
    'lib/admin/css/skins/skin-yellow.min.css',
    'lib/admin/plugins/pace/pace.min.css',
    output='public/css/adminlte.css'
)

adminlte_js = Bundle(
    'lib/admin/js/app.min.js',
    'lib/admin/plugins/pace/pace.min.js',
    'lib/admin/plugins/chartjs/Chart.min.js',
    'lib/admin/plugins/fastclick/fastclick.min.js',
    'lib/admin/plugins/datatables/jquery.dataTables.min.js',
    'lib/admin/plugins/datatables/dataTables.bootstrap.min.js',
    output='public/js/adminlte.js'
)

student_css = Bundle(
    'css/student.css',
    filters='cssmin',
    output='public/css/student.css'
)

student_js = Bundle(
    'js/student.js',
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
    filters='jsmin',
    output='public/js/staff.js'
)
