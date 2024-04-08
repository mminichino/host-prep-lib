from setuptools import setup, find_packages
import pyhostprep

from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name='pyhostprep',
    version=pyhostprep.__version__,
    packages=find_packages(exclude=['tests']),
    url='https://github.com/mminichino/host-prep-lib',
    license='Apache License 2.0',
    author='Michael Minichino',
    python_requires='>=3.8',
    entry_points={
        'console_scripts': [
            'bundlemgr = pyhostprep.bundlemgr:main',
            'swmgr = pyhostprep.swmgr:main',
            'storagemgr = pyhostprep.storagemgr:main',
        ]
    },
    package_data={'pyhostprep': ['data/config/*', 'data/playbooks/*']},
    install_requires=[
        'attrs>=22.2.0',
        'pytest>=7.0.1',
        'pytest-asyncio>=0.16.0',
        'pytest-rerunfailures>=10.3',
        'pytest-mock>=3.6.1',
        'docker>=5.0.3',
        'ansible>=6.7.0',
        'ansible-runner>=2.3.3',
        'requests>=2.31.0',
        'urllib3>=1.26.18; "amzn2" not in platform_release',
        'urllib3==1.26.18; "amzn2" in platform_release',
        'overrides>=7.4.0',
        'bumpversion>=0.6.0',
        'psutil>=5.9.5',
        'Jinja2>=3.0.0'
    ],
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
