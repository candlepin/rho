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
"""
Rho Setup Script
"""

from setuptools import setup, find_packages
from setuptools import Command

import glob
import os
import subprocess


class BuildLangs(Command):

    description = "generate pot/po/mo translation files"
    user_options = [
        ("gen-messages", None, "generate message catalog from strings")]
    boolean_options = ["gen-messages"]

    def initialize_options(self):
        self.gen_messages = False

    def finalize_options(self):
        pass

    def run(self):
        self._gen_pot_file()

    def _gen_pot_file(self):
        py_dirs = ["src/rho/"]
        py_files = ['bin/rho']
        for py_dir in py_dirs:
            py_files = py_files + glob.glob("%s/*.py" % py_dir)
        print(py_files)
        args = ["xgettext", "-L", "python", "-o",
                "locale/rho.pot", "-d", "rho"] + py_files
        subprocess.Popen(args, stdout=subprocess.PIPE).communicate()
        # we develop in en_US, so make the default pot a en_Us

    def _gen_po_file(self):
        # generate the en_US.po file, this is for dist maintainers only
        args = ["msginit", "--no-translator", "-i",
                "locale/rho.pot", "-o", "locale/en_US.po"]
        subprocess.Popen(args, stdout=subprocess.PIPE).communicate()


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


def get_locale_paths():
    localepath = "share"
    mo_files = glob.glob("locale/*/LC_MESSAGES/*.mo")
    data_paths = []
    for mo_file in mo_files:
        data_dir = "%s/%s" % (localepath, os.path.split(mo_file)[0])
        data_paths.append((data_dir, [mo_file]))
    return data_paths


def get_data_files():
    gen_mo_files()
    return get_locale_paths()

setup(
    name="rho",
    version='0.0.21',
    description='Network scanner to identify operating systems and versions.',
    author='Red Hat',
    author_email='',
    url='',
    license='GPLv2',

    package_dir={
        'rho': 'src/rho',
    },
    packages=find_packages('src'),
    include_package_data=True,

    # non-python scripts go here
    scripts=[
        'bin/rho',
    ],

    data_files=get_data_files(),

    classifiers=[
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Information Technology',
        'Operating System :: POSIX',
        'Topic :: Utilities',
        'Programming Language :: Python'
    ],

    cmdclass={'build_langs': BuildLangs}
)
