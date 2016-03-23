from setuptools import setup
from pip.req import parse_requirements
import io
import os

__version__ = '0.1.5'
__author__ = 'Cedric Zhuang'


def here(filename=None):
    ret = os.path.abspath(os.path.dirname(__file__))
    if filename is not None:
        ret = os.path.join(ret, filename)
    return ret


def read(*filenames, **kwargs):
    encoding = kwargs.get('encoding', 'utf-8')
    sep = kwargs.get('sep', '\n\n')
    buf = []
    for filename in filenames:
        with io.open(here(filename), encoding=encoding) as f:
            buf.append(f.read())
    return sep.join(buf)


requirements = parse_requirements('requirements.txt', session=False)
test_requirements = parse_requirements('test-requirements.txt', session=False)


def get_long_description():
    filename = 'README.md'
    try:
        import pypandoc
        ret = pypandoc.convert(filename, 'rst')
    except ImportError:
        ret = read(filename)
    return ret


setup(
    name="retryz",
    version=__version__,
    author="Cedric Zhuang",
    author_email="jealous@163.com",
    description="Retry decorator with a bunch of configuration parameters.",
    license="Apache Software License",
    keywords="retry decorator",
    url="http://github.com/jealous/retryz",
    packages=['retryz'],
    platforms=['any'],
    long_description=get_long_description(),
    classifiers=[
        "Programming Language :: Python",
        "Natural Language :: English",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: Apache Software License",
    ],
    install_requires=[str(ir.req) for ir in requirements],
    tests_require=[str(ir.req) for ir in test_requirements],
)
