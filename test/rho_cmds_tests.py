#!/usr/bin/python

import subprocess
import unittest
# to check if root
import os

from rho import rho_cmds


# for unit testing, we just run these locally

class _TestRhoCmd(unittest.TestCase):

    def setUp(self):
        self.rho_cmd = self.cmd_class()
        self.out = self._run_cmds()

    def _run_cmds(self):
        output = []
        for cmd in self.rho_cmd.cmd_strings:
            p = subprocess.Popen((cmd), shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
            out, err = p.communicate()
            output.append((out, err))
        return output

#    def test_run(self):
#        print self.out

    def test_parse(self):
        self.rho_cmd.populate_data(self.out)

    def test_data(self):
        self.rho_cmd.populate_data(self.out)
        print self.rho_cmd.data


class TestUnameCmd(_TestRhoCmd):
    cmd_class = rho_cmds.UnameRhoCmd

    def test_data_display(self):
        self.rho_cmd.populate_data(self.out)
        print "uname: %(uname.os)s\n hostname:%(uname.hostname)s\n%(uname.processor)s\n" % self.rho_cmd.data


class TestRedhatReleaseRhoCmd(_TestRhoCmd):
    cmd_class = rho_cmds.RedhatReleaseRhoCmd

    def test_data_display(self):
        self.rho_cmd.populate_data(self.out)
        print "name: %(redhat-release.name)s\n version:%(redhat-release.version)s\n%(redhat-release.release)s\n" % self.rho_cmd.data


class TestScriptRhoCmd(_TestRhoCmd):
    cmd_class = rho_cmds.ScriptRhoCmd

    def setUp(self):
        self.rho_cmd = self.cmd_class(command="ls -rho /tmp")
        self.out = self._run_cmds()

class TestVirtWhatRhoCmd(_TestRhoCmd):
    cmd_class = rho_cmds.VirtWhatRhoCmd

    def test_virt_what_smoke(self):
        self.rho_cmd.populate_data(self.out)

class TestVirtRhoCmd(_TestRhoCmd):
    # this is all dependent on system level stuff, so hard to
    # test output, but this at least smoke tests it
    cmd_class = rho_cmds.VirtRhoCmd

    def test_virt_smoke(self):
        self.rho_cmd.populate_data(self.out)

# Only add this test if run as root
if os.geteuid() == 0:
    # smoke test Subman Facts using inherited test_data method
    class TestSubmanFactsRhoCmd(_TestRhoCmd):
        cmd_class = rho_cmds.SubmanFactsRhoCmd


class TestCpuCmd(_TestRhoCmd):
    cmd_class = rho_cmds.CpuRhoCmd

    def test_cpu_count(self):
        self.rho_cmd.populate_data(self.out)
        print "cpu.count: %(cpu.count)s" % self.rho_cmd.data

    def test_cpu_bogomips(self):
        self.rho_cmd.populate_data(self.out)
        print "cpu.bogomips: %(cpu.bogomips)s" % self.rho_cmd.data

    def test_cpu_vendor_id(self):
        self.rho_cmd.populate_data(self.out)
        print "cpu.vendor_id: %(cpu.vendor_id)s" % self.rho_cmd.data

    def test_cpu_socket_count(self):
        self.rho_cmd.populate_data(self.out)
        print "cpu.socket_count: %(cpu.socket_count)s" % self.rho_cmd.data

class TestDateRhoCmd(_TestRhoCmd):
    cmd_class = rho_cmds.DateRhoCmd

    def test_date(self):
        self.rho_cmd.populate_data(self.out)
        print "date.date: %(date.date)s" % self.rho_cmd.data

class TestDmiRhoCmd(_TestRhoCmd):
    cmd_class = rho_cmds.DmiRhoCmd

    def test_dmi_decode(self):
        self.rho_cmd.populate_data(self.out)
        print self.rho_cmd.data

class TestRedHatPackagesRhoCmd(_TestRhoCmd):
    cmd_class = rho_cmds.RedhatPackagesRhoCmd

    def test_is_red_hat(self):
        self.rho_cmd.populate_data(self.out)
        print "redhat-packages.is_redhat: %(redhat-packages.is_redhat)s" % self.rho_cmd.data

    def test_num_rh_packages(self):
        self.rho_cmd.populate_data(self.out)
        print "redhat-packages.num_rh_packages: %(redhat-packages.num_rh_packages)s" % self.rho_cmd.data

    def test_num_installed_packages(self):
        self.rho_cmd.populate_data(self.out)
        print "redhat-packages.num_installed_packages: %(redhat-packages.num_installed_packages)s" % self.rho_cmd.data

    def test_last_installed(self):
        self.rho_cmd.populate_data(self.out)
        print "redhat-packages.last_installed: %(redhat-packages.last_installed)s" % self.rho_cmd.data

    def test_last_built(self):
        self.rho_cmd.populate_data(self.out)
        print "redhat-packages.last_built: %(redhat-packages.last_built)s" % self.rho_cmd.data
