from setuptools import setup
import pyhostprep

from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()
with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='pyhostprep',
    version=pyhostprep.__version__,
    packages=['pyhostprep'],
    url='https://github.com/mminichino/host-prep-lib',
    license='Apache License 2.0',
    author='Michael Minichino',
    python_requires='>=3.8',
    entry_points={
        'console_scripts': ['bundlemgr = pyhostprep.bundlemgr:main']
    },
    package_data={'pyhostprep': ['data/config/*', 'data/playbooks/*']},
    install_requires=required,
    author_email='info@unix.us.com',
    description='Couchbase Host Automation Library',
    long_description=long_description,
    long_description_content_type='text/markdown',
    keywords=["couchbase", "devops", "automation"],
    classifiers=[
          "Development Status :: 4 - Beta",
          "License :: OSI Approved :: Apache Software License",
          "Intended Audience :: Developers",
          "Operating System :: OS Independent",
          "Programming Language :: Python",
          "Programming Language :: Python :: 3",
          "Topic :: Database",
          "Topic :: Software Development :: Libraries",
          "Topic :: Software Development :: Libraries :: Python Modules"],
)
