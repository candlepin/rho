#!/usr/bin/python

import unittest

#from nose.plugins.attrib import attr

from rho import config
from rho import ssh_jobs

__test__ = False

hostname = "alikins.usersys.redhat.com"
bad_hostname = "thisshouldneverexist.usersys.redhat.com"
filtered_hostname = ""
user = ""

# haha, no password, only works current if ssh-agent is running, and
# hopefully, if you are me


auth_good =  ssh_jobs.SshAuth(name="adrian", username="adrian")
auth_no_user = ssh_jobs.SshAuth(name="badadrian", username="badadrian")
auth_bad_password = ssh_jobs.SshAuth(name="adrian", username="adrian", password="wrong")

# local_auth should redefine the above if need be
try:
    from local_auth import *
except ImportError:
    pass
# this api is going to change...
class _TestSshJobs(unittest.TestCase):
    auth = None
    ip = hostname
    def setUp(self):
        self.jobs = ssh_jobs.SshJobs()
        self.output = []
        self.retcode = []


    def _callback(self, resultlist=[]):
        for result in resultlist:
            print "%s:%s %s" % (result.ip, result.returncode, result.output)
            self.output.append((result.ip, result.returncode, result.output))

    def _run_cmds(self, cmds=None, number=1):
        if cmds:
            self.cmds = cmds
        self.ssh_cmds = [ssh_jobs.SshJob(ip=self.ip, cmds=cmds, auth=self.auth)] * number
        self.jobs.run_cmds(cmds=self.ssh_cmds, callback = self._callback)

    def test_echo_ip(self):
        self._run_cmds(["echo blippy %s" % self.ip])

    def test_ls_tmp(self):
        self._run_cmds(["ls -lart /tmp"])

    def test_ls_tmp_lots(self):
        self._run_cmds(["ls -lart /tmp"], 42)

    def test_sleep_short_single(self):
        self._run_cmds(["sleep 1"])

    def test_sleep_short_lots(self):
        self._run_cmds(["sleep 1"], 20)

    def test_sleep_long_single(self):
        self._run_cmds(["sleep 30"])
    test_sleep_long_single.slow = 1

    def test_sleep_long_lots(self):
        self._run_cmds(["sleep 30"], 37)
    test_sleep_long_lots.slow = 1

    def test_sleep_long_lots_of_threads(self):
        self.jobs.max_threads = 53
        self._run_cmds(["sleep 30"], 37)
    test_sleep_long_lots_of_threads.slow = 1

    def test_sleep_short_lots_of_threads(self):
        self.jobs.max_threads = 31
        self._run_cmds(["sleep 1"], 47)
    test_sleep_short_lots_of_threads.slow = 1


    def test_uname(self):
        self._run_cmds(["uname -a"])

    def test_rpm_release(self):
        self._run_cmds(["""rpm -q --queryformat "%{NAME}\n%{VERSION}\n%{RELEASE}\n" --whatprovides redhat-release"""])



class TestSshJobsWorks(_TestSshJobs):
    auth = auth_good

#class TestSshJobsNoUser(_TestSshJobs):
#    auth =  ssh_jobs.SshAuth(name="badadrian", username="badadrian")
    
class TestSshJobsNoHost(_TestSshJobs):
    auth = auth_good
    ip = bad_hostname

#class TestSshJobsF11(_TestSshJobs):
#    auth = auth_test
#    ip = "f11-virt-1.usersys.redhat.com"

