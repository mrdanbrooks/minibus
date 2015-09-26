from setuptools import setup

with open("VERSION", "r") as f:
    version = f.readline().strip()

with open("README.md", "r") as f:
    long_description = f.read()

with open("requirements.txt", "rt") as f:
    requirements = f.read().splitlines()

setup(name='minibus',
      version=version,
      description="MiniBus IPC Library",
      long_description=long_description,
      url="https://github.com/mrdanbrooks/minibus",
      author="Dan Brooks",
      license="Apache v2.0",

      # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
          'Topic :: Software Development :: Libraries',
          'License :: OSI Approved :: Apache Software License',
          'Programming Language :: Python :: 2.7',
      ],
      keywords='minibus, publish/subscribe, ipc, development',

      py_modules=['minibus'],
      scripts=['mbtt'],

      install_requires=requirements, #['jsonschema','netifaces'],

      # These can be installed optionally using
      # $ pip install -e .[twisted,crypto]
      extras_require={
          'twisted': ['Twisted'],
          'crypto': ['gnupg'],
      }

      )



