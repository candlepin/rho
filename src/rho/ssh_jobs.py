#!/usr/bin/python

import subprocess
import select

import os
import posix
import string
import sys
import time
import StringIO


class SshJob():
    def __init__(self, ip=None, cmd=None, auth=None):
        self.ip = ip
        self.cmd = cmd
        self.output = None
        # what is auth? undetermined yet
        self.auth = None

    def run(self):
        (stdout, stderr) = subprocess.Popen(self.cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE).communicate()
        self.output = stdout

class SshJobs():
    def __init__(self, cmdSrc=None):
        self.read_set = []
        self.write_set = []
        self.jobs = []
        self.jobs_read = []
        self.jobs_write = []
        # cmdSrc is some sort of list/iterator thing
        self.cmds_to_run = cmdSrc

    # this is a lame one at a time, single threaded, blocking, sync approah
    # will replce with something better 
    def run_cmds(self, callback=None):
        while self.cmds_to_run:
            job = self.cmds_to_run.pop()
            job.run()
            if callback:
                callback([job])
            print job.output
            self.jobs.append(job)

    def add_cmd_to_run(self, job):
        pass

    def get_job(self):
        pass


if __name__ == "__main__":  
    ssh_cmds = []
    for i in range(1,5):
        ip = "192.168.1.%s" % i
        ssh_cmds.append(SshJob(ip=ip, cmd=["ssh", "adrian@alikins.usersys.redhat.com", "echo", ip]))
        
    jobs = SshJobs()
    jobs.cmds_to_run = ssh_cmds
    jobs.run_cmds()

#jobs.read_jobs()
