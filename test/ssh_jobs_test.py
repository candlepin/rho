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

    ips = [] 
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
        self.ssh_cmds = []
        for ip, auth in self.ips:
            self.ssh_cmds = self.ssh_cmds + [ssh_jobs.SshJob(ip=ip, cmds=cmds, auth=auth)] * number
        print self.ssh_cmds
        self.jobs.run_cmds(cmds=self.ssh_cmds, callback = self._callback)

    def test_echo_blippy(self):
        self._run_cmds(["echo blippy"])

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

    # note, by default sshd only will allow 10 clients to backlog in
    # the auth step, so this can make ssh start refusing new connections
    # and new ssh attempts to issue the very descriptive and helpfule error
    # "Error reading SSH protocol banner". You can either pause a little before
    # each connection attempt to let sshd sort itself out, increase "MaxStartups" in
    # /etc/ssh/sshd_config, or just don't use as many threads
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


# ok, for joe schmo, none of these will work. They kind of expect machines
# to exist, that you can ssh to, and have auth on. Obviously, I do not
# know what those are. But these should be examples. I'm not sure of
# a better way to test this.

#class TestSshJobsWorks(_TestSshJobs):
#    ips = [(hostname, auth_good)]

#class TestSshJobsNoUser(_TestSshJobs):
#    auth =  ssh_jobs.SshAuth(name="badadrian", username="badadrian")
    




#class TestSshJobsNoHost(_TestSshJobs):
#    auth = auth_good
#    ip = bad_hostname



#class TestSshJobsF11(_TestSshJobs):
#    ips = [("f11-virt-1.usersys.redhat.com", auth_test)]

#class TestSshJobsAll(_TestSshJobs):
#    ips = [("f11-virt-1.usersys.redhat.com", auth_test),
#           ("f11-virt-2.usersys.redhat.com", auth_test),
#           ("f11-virt-1.usersys.redhat.com", auth_bad_password),
#            (hostname, auth_good)]



