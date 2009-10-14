#!/usr/bin/python

import subprocess
import select

import os
import posix
import string
import sys
import time
import StringIO

class Auth():
    def __init__(self, name=None, type=None, username=None, password=None):
        self.name = name
        self.type = type
        self.username = username
        self.password = None

class SshAuth(Auth):
    def __init__(self, name=None, type=None, username=None, password=None):
        self.name = name
        self.type = "ssh"
        self.username = username
        self.password = None



class SshJob():
    def __init__(self, ip=None, cmd=None, auth=None):
        self.ip = ip
        self.cmd = cmd
        self.auth = auth
        self.ssh_cmd = ["ssh", "%s@%s" % (self.auth.username, self.ip), "%s" % (self.cmd)]
        self.output = None
        self.returncode = None

        #self.config = config.Config()['config']
        #self.auth = self.config.credentials['bobslogin']
        # what is auth? undetermined yet
#        self.auth = self.config['

    def run(self):
#        print self.ssh_cmd
        p = subprocess.Popen(self.ssh_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        (stdout, stderr) = p.communicate()
        retcode = p.returncode
#        print stdout, stderr, retcode
        self.output = stdout
        self.returncode = retcode

class SshJobs():
    def __init__(self, cmdSrc=None):
        self.read_set = []
        self.write_set = []
        self.jobs = []
        self.jobs_read = []
        self.jobs_write = []
        # cmdSrc is some sort of list/iterator thing
        self.cmds_to_run = cmdSrc

        self.verbose = True
        self.outfile = None
        self.max_threads = 10  

    def run_cmds(self, callback=None):
        self.output_queue = my_sshpt.startOutputThread(self.verbose, self.outfile)
        self.ssh_connect_queue = my_sshpt.startSSHQueue(self.output_queue, self.max_threads)

        while self.cmds_to_run:
            for cmd in self.cmds_to_run:
                if self.ssh_connect_queue.qsize()  self.max_threads:
                    my_sshpt.queueSSHConnection(self.ssh_connect_queue, cmd)
                    self.cmds_to_run.remove(cmd)
            time.sleep(1)
        self.ssh_connect_queue.join()
        return self.output_queue

    # this is a lame one at a time, single threaded, blocking, sync approah
    # will replce with something better 
    def run_cmds_old(self, callback=None):
        while self.cmds_to_run:
            job = self.cmds_to_run.pop()
            job.run()
            if callback:
                callback([job])
#            print job.output
            self.jobs.append(job)

    def add_cmd_to_run(self, job):
        pass

    def get_job(self):
        pass


def example_callback(resultlist=[]):
    for result in resultlist:
        print "%s: %s" % (result.ip, result.output)

if __name__ == "__main__":  
    ssh_cmds = []

    auth = SshAuth(name="adrian", username="adrian")

    ip_range = ["alikins.usersys.redhat.com", "badhost.example.com"]
    for ip in ip_range:
        ssh_cmds.append(SshJob(ip=ip, cmd="echo foo bar %s" % ip, auth=auth ))
        
    jobs = SshJobs()
    jobs.cmds_to_run = ssh_cmds
    jobs.run_cmds(callback=callback)

#jobs.read_jobs()
