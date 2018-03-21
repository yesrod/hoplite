from setuptools import setup

setup(
    name='hoplite',
    version='0.1',
    description='HOPLITE: A system for monitoring kegerator levels and temperatures',
    py_modules=['hoplite'],
    install_requires=['Rpi.GPIO', 'numpy', 'luma.lcd', 'hx711'],
)

