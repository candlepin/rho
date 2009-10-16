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

""" Unit tests for CLI """

from rho.clicommands import *

import unittest
import os

class CliCommandsTests(unittest.TestCase):

    def setUp(self):
        if os.path.exists("test/rho.conf.test"):
            os.remove("test/rho.conf.test")

    def _run_test(self, cmd, args):
        os.environ[RHO_PASSPHRASE] = "blerg"
        self.conffile = "test/rho.conf.test"
        # tests aren't real bright, start with a fresh file
        if os.access(self.conffile, os.R_OK):
            os.remove(self.conffile)
        sys.argv = ["bin/rho" ]  + args + ["--config", self.conffile]
        cmd.main()

    def test_scan(self):
        try:
            self._run_test(ScanCommand(), ["scan"])
        except SystemExit:
            pass

    def test_profile_show(self):
        self._run_test(ProfileShowCommand(), ["profile", "show"])

    def test_profile_add(self):
        self._run_test(ProfileAddCommand(), ["profile", "add", "--name", "profilename"])

    def test_auth_show(self):
        self._run_test(AuthShowCommand(), ["auth", "show"])

    def test_auth_add(self):
        try:
            self._run_test(AuthAddCommand(), ["auth", "add"])
        except SystemExit:
            # we expect this to throw a optparse.parse.error
            pass

    def test_dumpconfig(self):
        try:
            self._run_test(DumpConfigCommand(), ['dumpconfig',
                                                 '--encrypted-file', 
                                                 'test/data/encrypted.data'])
        except SystemExit:
            pass
