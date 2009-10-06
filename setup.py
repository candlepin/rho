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

    classifiers = [
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Programming Language :: Python'
    ],
#    test_suite = 'nose.collector',
)


# XXX: this will also print on non-install targets
print("rho target is complete")
