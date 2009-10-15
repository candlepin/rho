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

import my_sshpt

import os
import posix
import string
import subprocess
import sys
import time

class Auth():
    def __init__(self, name=None, type=None, username=None, password=None):
        self.name = name
        self.type = type
        self.username = username
        self.password = password

class SshAuth(Auth):
    def __init__(self, name=None, type=None, username=None, password=None):
        self.name = name
        self.type = "ssh"
        self.username = username
        self.password = password


#FIXME: SshJob needs to have a RhoJobsList, where each RhoJob item actually has
# a list of cli commands to run
class SshJob():
    def __init__(self, ip=None, port=22, rho_cmds=None, auth=None, timeout=30):
        self.ip = ip
        self.port = port

        # rho commands is RhoCmdList, aka, a list of RhoCmds (duh)
        self.rho_cmds = rho_cmds
        
        self.auth = auth
        self.timeout = timeout
        self.command_output = None
        self.connection_result = True
        self.returncode = None
        self.auth_used = None
        assert getattr(rho_cmds, "__iter__")

    def output_callback(self):
        print "ip: %s\ncommand_output: %s\nconnection_result: %s" % (self.ip, self.command_output, self.connection_result)
        
        #self.config = config.Config()['config']
        #self.auth = self.config.credentials['bobslogin']
        # what is auth? undetermined yet
#        self.auth = self.config['


class SshJobs():
    def __init__(self, ssh_job_src=None):
        # cmdSrc is some sort of list/iterator thing
        self.ssh_jobs = ssh_job_src

        self.verbose = True
        self.outfile = None
        self.max_threads = 10  

    def run_jobs(self, ssh_jobs=None, callback=None):
        if ssh_jobs:
            self.ssh_jobs = ssh_jobs
        
        self.output_queue = my_sshpt.startOutputThread(self.verbose, self.outfile)
        self.ssh_connect_queue = my_sshpt.startSSHQueue(self.output_queue, self.max_threads)

        while self.ssh_jobs:
            for ssh_job in self.ssh_jobs:
                
                if self.ssh_connect_queue.qsize()  <= self.max_threads:
                    my_sshpt.queueSSHConnection(self.ssh_connect_queue, ssh_job)
                    self.ssh_jobs.remove(ssh_job)
#            time.sleep(1)
        self.ssh_connect_queue.join()
        return self.output_queue


def example_callback():
    for result in resultlist:
        print "%s: %s" % (result.ip, result.output)

if __name__ == "__main__":  
    ssh_jobs = []

    auth = SshAuth(name="adrian", username="adrian")

    ip_range = ["alikins.usersys.redhat.com", "badhost.example.com"]
    for ip in ip_range:
        ssh_jobs.append(SshJob(ip=ip, rho_cmds=[rho_cmds.UnameRhoCmd()], auth=auth ))
        
    jobs = SshJobs()
#    jobs.cmds_to_run = ssh_cmds
    jobs.run_cmds(ssh_jobs = ssh_jobs, callback=callback)

#jobs.read_jobs()
