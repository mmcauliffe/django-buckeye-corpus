from distutils.core import setup

packages=['buckeyebrowser']
template_patterns = [
    'templates/*.html',
    'templates/*/*.html',
    'templates/*/*/*.html',
    ]

setup(
    name='django-buckeye-corpus',
    version='0.3.54',
    author='Michael McAuliffe',
    author_email='michael.e.mcauliffe@gmail.com',
    url='http://pypi.python.org/pypi/django-buckeye-corpus/',
    license='LICENSE.txt',
    description='',
    long_description=open('README.md').read(),
    install_requires=['Django',
                    'django-celery',
                    'python-praat-scripts',
                    'pillow',
                    'linguistic-helper-functions',
                    'django-picklefield'],
    packages=packages,
    package_data=dict( (package_name, template_patterns)
                   for package_name in packages )
)
