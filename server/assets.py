from flask_assets import Bundle

common_css = Bundle(
    'css/helper.css',
    'css/main.css',
    'vendor/bootstrap/dist/css/bootstrap.min.css',
    filters='cssmin',
    output='public/css/common.css'
)

common_js = Bundle(
    'vendor/jquery/dist/jquery.min.js',
    'vendor/bootstrap/dist/js/bootstrap.min.js',
    Bundle(
        'js/main.js',
        filters='jsmin'
    ),
    output='public/js/common.js'
)
