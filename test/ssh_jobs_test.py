#!/usr/bin/python

import unittest

#from nose.plugins.attrib import attr

from rho import config
from rho import ssh_jobs
from rho import rho_cmds

__test__ = False

# this api is going to change...


class TestSshJobs(unittest.TestCase):

    ips = []

    def setUp(self):
        self.jobs = ssh_jobs.SshJobs()
        self.output = []
        self.retcode = []

        self.sleep30 = rho_cmds.ScriptRhoCmd("sleep 30")
        self.sleep1 = rho_cmds.ScriptRhoCmd("sleep 1")
        self.uname = rho_cmds.UnameRhoCmd()
        self.rh_release = rho_cmds.RedhatReleaseRhoCmd()

    def _callback(self, resultlist=[]):
        pass
        for result in resultlist:
            print
            print "%s:%s %s" % (result.ip, result.returncode, result.output)
            print
            self.output.append((result.ip, result.returncode, result.output))

    def _run_jobs(self, jobs=None, number=1):
        if jobs:
            self.ssh_jobs = jobs
        self.ssh_jobs = []
        for ip, auth in self.ips:
            self.ssh_jobs = self.ssh_jobs + [ssh_jobs.SshJob(ip=ip, rho_cmds=jobs, auths=auth)] * number
#        print self.ssh_jobs
        self.jobs.run_jobs(ssh_jobs=self.ssh_jobs, callback=self._callback)

    def test_echo_blippy(self):
        self._run_jobs([rho_cmds.ScriptRhoCmd("echo blippy")])

    def test_ls_tmp(self):
        self._run_jobs([rho_cmds.ScriptRhoCmd("ls -lart /tmp")])

    def test_ls_tmp_lots(self):
        self._run_jobs([rho_cmds.ScriptRhoCmd("ls -lart /tmp")], 42)

    def test_sleep_short_single(self):
        self._run_jobs([self.sleep1])

    def test_sleep_short_lots(self):
        self._run_jobs([self.sleep1], 20)

    def test_sleep_long_single(self):
        self._run_jobs([self.sleep30])
    test_sleep_long_single.slow = 1

    def test_sleep_long_lots(self):
        self._run_jobs([self.sleep30], 37)
    test_sleep_long_lots.slow = 1

    # note, by default sshd only will allow 10 clients to backlog in
    # the auth step, so this can make ssh start refusing new connections
    # and new ssh attempts to issue the very descriptive and helpfule error
    # "Error reading SSH protocol banner". You can either pause a little before
    # each connection attempt to let sshd sort itself out, increase "MaxStartups" in
    # /etc/ssh/sshd_config, or just don't use as many threads
    def test_sleep_long_lots_of_threads(self):
        self.jobs.max_threads = 53
        self._run_jobs([self.sleep30], 37)
    test_sleep_long_lots_of_threads.slow = 1

    def test_sleep_short_lots_of_threads(self):
        self.jobs.max_threads = 31
        self._run_jobs([self.sleep1], 47)
    test_sleep_short_lots_of_threads.slow = 1

    def test_multiple_commands(self):
        self._run_jobs([self.uname, self.rh_release, rho_cmds.ScriptRhoCmd("/sbin/ifconfig")])
#        self._run_cmds(["uname -a", "rpm -q redhat-relase", "hostname", "ls /tmp", "/sbin/ifconfig"])

    def test_uname(self):
        self._run_jobs([self.uname])

    def test_rpm_release(self):
        self._run_jobs([self.rh_release])

    def test_rho_cmd_no_list(self):
        try:
            self._run_jobs(self.uname)
        except AttributeError:
            pass

# ok, for joe schmo, none of these will work. They kind of expect machines
# to exist, that you can ssh to, and have auth on. Obviously, I do not
# know what those are. But these should be examples. I'm not sure of
# a better way to test this.

# class TestSshJobsWorks(_TestSshJobs):
#    ips = [(hostname, auth_good)]

# class TestSshJobsNoUser(_TestSshJobs):
#    auth =  ssh_jobs.SshAuth(name="badadrian", username="badadrian")


# class TestSshJobsNoHost(_TestSshJobs):
#    auth = auth_good
#    ip = bad_hostname


# class TestSshJobsF11(_TestSshJobs):
#    ips = [("f11-virt-1.usersys.redhat.com", auth_test)]

# class TestSshJobsAll(_TestSshJobs):
#    ips = [("f11-virt-1.usersys.redhat.com", auth_test),
#           ("f11-virt-2.usersys.redhat.com", auth_test),
#           ("f11-virt-1.usersys.redhat.com", auth_bad_password),
#            (hostname, auth_good)]
