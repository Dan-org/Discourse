"""
Django Discourse setup.
"""

from setuptools import setup, find_packages

setup( name='django-discourse',
       version='0.1',
       description='Django app for various communication and content site needs.',
       author='Brantley Harris',
       author_email='brantley.harris@gmail.com',
       packages = find_packages(),
       include_package_data = True,
       zip_safe = False,
       install_requires = ['django-yamlfield', 'bleach']
      )
