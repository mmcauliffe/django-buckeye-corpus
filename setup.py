from distutils.core import setup

setup(
    name='django-buckeye-corpus',
    version='0.1.0',
    author='Michael McAuliffe',
    author_email='michael.e.mcauliffe@gmail.com',
    packages=['buckeyebrowser'],
    url='http://pypi.python.org/pypi/django-buckeye-corpus/',
    license='LICENSE.txt',
    description='',
    long_description=open('README.md').read(),
    install_requires=['django',
					'django-celery',
					'python-praat-scripts'],
)
