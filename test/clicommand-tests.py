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
from mock import Mock
import unittest
import sys


class HushUpStderr(object):

    def write(self, s):
        pass


class CliCommandsTests(unittest.TestCase):

    def setUp(self):
        # Temporarily disable stderr for these tests, CLI errors clutter up
        # nosetests command.
        self.orig_stderr = sys.stderr
        sys.stderr = HushUpStderr()

    def tearDown(self):
        # Restore stderr
        sys.stderr = self.orig_stderr

    def _run_test(self, cmd, args):
        sys.argv = ["bin/rho"] + args
        cmd.main()

    def test_scan_facts_default(self):
        try:
            self._run_test(ScanCommand(), ["scan", "--profile", "profilename",
                                           "--reset", "--reportfile",
                                           "data/test_report.csv", "--facts",
                                           "default", "ansible_forks",
                                           "100"])
        except SystemExit:
            pass

    def test_scan_facts_file(self):
        try:
            self._run_test(ScanCommand(), ["scan", "--profile", "profilename",
                                           "--reset", "--reportfile",
                                           "data/test_report.csv", "--facts",
                                           "data/facts_test", "ansible_forks",
                                           "100"])
        except SystemExit:
            pass

    def test_scan_facts_list(self):
        try:
            self._run_test(ScanCommand(), ["scan", "--profile", "profilename",
                                           "--reset", "--reportfile",
                                           "data/test_report.csv", "--facts",
                                           "Username_uname.all",
                                           "RedhatRelease_redhat-release.release",
                                           "--ansible_forks",
                                           "100"])
        except SystemExit:
            pass

    def test_profile_list(self):
        self._run_test(ProfileListCommand(), ["profile", "list"])

    def test_profile_add_hosts_list(self):
        try:
            self._run_test(ProfileAddCommand(), ["profile", "add", "--name",
                                                 "profilename", "hosts",
                                                 "1.2.3.4", "1.2.3.[4:100]",
                                                 "--auths", "auth_1", "auth2"])
        except SystemExit:
            pass

    def test_profile_add_hosts_file(self):
        try:
            self._run_test(ProfileAddCommand(), ["profile", "add", "--name",
                                                 "profilename", "hosts",
                                                 "data/hosts_test","--auths",
                                                 "auth_1", "auth2"])
        except SystemExit:
            pass

    def test_auth_list(self):
        self._run_test(AuthListCommand(), ["auth", "list"])

    def test_auth_add(self):
        getpass = Mock()
        getpass.return_value = "pass"
        try:
            self._run_test(AuthAddCommand(), ["auth", "add", "--name", "test",
                                              "--username", "test_user", "--password",
                                              "--sshkeyfile", "somefile"])
        except SystemExit:
            pass

    def test_profile_add_nonexistent_auth(self):
        self.assertRaises(SystemExit, self._run_test, ProfileAddCommand(),
                          ["profile", "add", "--name", "profile", "hosts",
                           "1.2.3.4", "--auth", "doesnotexist"])

    def test_bad_range_options(self):
        # Should fail scanning range without a username:
        self.assertRaises(SystemExit, self._run_test, ProfileAddCommand(),
                          ["profile", "add", "--name",
                           "profilename", "hosts",
                           "a:d:b:s", "--auths",
                           "auth_1", "auth2"])

