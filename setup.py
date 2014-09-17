from setuptools import setup, find_packages

setup(
    name='ok',
    version='1.0.6',
    description=('ok.py supports programming projects by running tests, '
                'tracking progress, and assisting in debugging.'),
    # long_description=long_description,
    url='https://github.com/Cal-CS-61A-Staff/ok',
    author='John Denero, Soumya Basu, Stephen Martinis, Sharad Vikram, Albert Wu',
    # author_email='',
    license='Apache License, Version 2.0',
    keywords=['education', 'autograding'],
    packages=find_packages('client',
                           exclude=['*.tests', '*.tests.*',
                                    '*demo_assignments*']),
    package_dir={'': 'client'},
    # install_requires=[],
    entry_points={
        'console_scripts': [
            'ok=client.__main__:main',
            # 'ok-publish=client.publish:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
)

