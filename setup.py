from setuptools import setup

setup(name='vm_automation',
      version='0.1.6',
      description='Virtual infrastructure automation simplified interaction library',
      url='http://github.com/rapid7/vm-automation',
      author='Metasploit Hackers',
      author_email='metasploit-hackers@lists.sourceforge.net',
      license=open("LICENSE").read(),
      packages=['vm_automation'],
      install_requires=[
          'pyVmomi',
      ],
      classifiers=[
            'Development Status :: 4 - Beta',
            'Intended Audience :: Information Technology',
            'Intended Audience :: System Administrators',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: BSD License',
            'Topic :: Software Development :: Libraries :: Python Modules',
            'Topic :: System :: Distributed Computing',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3.5',
      ],
      platforms=['Windows', 'Linux', 'Solaris', 'Mac OS-X', 'Unix'],
      keywords='vsphere vmware esx',
      zip_safe=True)
