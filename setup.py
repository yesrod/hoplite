from setuptools import setup, find_packages

setup(
    name='hoplite',
    version='1.0.6',
    description='HOPLITE: A system for monitoring kegerator levels and temperatures',
    #    py_modules=['Hoplite', 'hoplite-web'],
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=[
        'Rpi.GPIO', 'numpy', 'luma.lcd', 'hx711', 'posix_ipc', 'remi'],
    package_dir={'hoplite': 'hoplite/'},
    package_data={  # Optional
        'hoplite': ['static/example-config.json', 'static/settings_16.png'],
    },
)
