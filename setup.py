from setuptools import setup, find_packages
import sys

if not sys.version_info[0] == 3:
    sys.exit("ERROR: HOPLITE requires Python 3.5 or higher")
else:
    if sys.version_info[1] < 5:
        sys.exit("ERROR: HOPLITE requires Python 3.5 or higher")
    if sys.version_info[1] == 5:
        print("WARNING: Python 3.5 is end of life and will not be supported in the future.")
        print("Please upgrade your Python version to 3.6 or higher,") 
        print("either by upgrading your OS or installing Python manually.") 

setup(
    name='hoplite',
    version='1.2.0',
    description='HOPLITE: A system for monitoring kegerator levels and temperatures',
    #    py_modules=['Hoplite', 'hoplite-web'],
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    python_requires=">=3.5",
    install_requires=[
        'Rpi.GPIO', 'numpy', 'luma.lcd>=2.0.0', 'hx711', 'posix_ipc', 'remi', 'flask'],
    package_dir={'hoplite': 'hoplite/'},
    package_data={  # Optional
        'hoplite': ['static/example-config.json', 'static/settings_16.png'],
    },
)
