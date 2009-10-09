#!/usr/bin/env python
#
# Copyright (c) 2009 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

"""
Rho Setup Script
"""

from setuptools import setup, find_packages
from setuptools import Command
#from distutils import install_data

import glob
import os
import shutil
import string
import subprocess
#class InstallData(install_data):
	
class BuildLangs(Command):
    description = "generate pot/po/mo translation files"
    user_options = [("gen-messages", None, "generate message catalog from strings")]
    boolean_options = ["gen-messages"]
    
    def initialize_options(self):
        self.gen_messages = False
	    
    def finalize_options(self):
        pass

    def run(self):
        self._gen_pot_file()

    def _gen_pot_file(self):
        pyfiles = glob.glob("src/rho/*.py")
	args = ["xgettext", "-o", "locale/rho.pot", "-d", "rho"] + pyfiles
	subprocess.Popen(args, stdout=subprocess.PIPE).communicate()
	# we develop in en_US, so make the default pot a en_Us
	shutil.copyfile("locale/rho.pot", "locale/en_US.po")


# should probably use intltool instead, but we dont have any translations
# yet so doesnt really matter


def gen_mo_files():
	po_files = glob.glob("locale/*.po")
	mo_files = []
	for po_file in po_files:
		locale = po_file[:-3]
		mo_file_dir = "%s/LC_MESSAGES/" % locale
		try:
			os.makedirs(mo_file_dir)
		except OSError:
			pass
		mo_file = "%s/rho.mo" % mo_file_dir
		subprocess.Popen(["msgfmt", "-o", mo_file, po_file])
		mo_files.append(mo_file)
	return mo_files


localepath = "share/"

setup(
    name="rho",
    version='0.1',
    description='Network scanner to identify operating systems and versions.',
    author='Red Hat',
    author_email='',
    url='',
    license='GPLv2',

    package_dir={
        'rho': 'src/rho',
    },
    packages = find_packages('src'),
    include_package_data = True,

    # non-python scripts go here
    scripts = [
        'bin/rho',
    ],

    data_files = [(localepath, gen_mo_files())],  

    classifiers = [
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Programming Language :: Python'
    ],

    cmdclass = { 'build_langs': BuildLangs }
#    test_suite = 'nose.collector',
)


# XXX: this will also print on non-install targets
print("rho target is complete")
