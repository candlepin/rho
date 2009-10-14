#!/usr/bin/python

import unittest


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

    def test_echo_ip(self):
        ssh_cmds = [ssh_jobs.SshJob(ip=self.ip, cmds=["echo  vvv %s" % self.ip], auth=self.auth)]
        self.jobs.cmds_to_run = ssh_cmds
        self.jobs.run_cmds(callback = self._callback)

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

