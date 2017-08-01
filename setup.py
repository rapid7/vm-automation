from setuptools import setup

setup(name='vm_automation',
      version='0.1',
      description='Virtual infrastructure automation simplified interaction library',
      url='http://github.com/rapid7/vm-automation',
      author='Metasploit Hackers',
      author_email='metasploit-hackers@lists.sourceforge.net',
      license='BSD-3-Clause',
      packages=['vm_automation'],
      install_requires=[
          'pyVim',
          'pyVmomi',
      ],
      zip_safe=False)

