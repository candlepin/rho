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

import paramiko

from rho import config
from rho.log import log
from rho import scan_report

import Queue
import socket
import StringIO
import sys
import threading
import traceback


# probably should be in a different module, but nothing else
# to go with it
def get_pkey(auth):
    if auth.type != config.SSH_KEY_TYPE:
        return None

    fo = StringIO.StringIO(auth.key)
    # this is lame, but there doesn't appear to be any API to just
    # DWIM with the the key_data, I have to figure out if its RSA or DSA/DSS myself
    if fo.readline().find("-----BEGIN DSA PRIVATE KEY-----") > -1:
        fo.seek(0)
        pkey = paramiko.DSSKey.from_private_key(fo, password=auth.password)
        return pkey
    fo.seek(0)
    if fo.readline().find("-----BEGIN RSA PRIVATE KEY-----") > -1:
        fo.seek(0)
        pkey = paramiko.RSAKey.from_private_key(fo, password=auth.password)
        return pkey

    print _("The private key file for %s is not a recognized ssh key type" % auth.name)
    return None

class SshJob():
    def __init__(self, ip=None, ports=[22], rho_cmds=None, auths=None,
            timeout=30, cache={}, allow_agent=False):
        # rho_cmds really needs to be list like, easy mistake to make...
        assert getattr(rho_cmds, "__iter__")

        self.ip = ip
        # list of ports to try
        self.ports = ports
        # the port that actually worked
        self.port = None

        # rho commands is RhoCmdList, aka, a list of RhoCmds (duh)
        self.rho_cmds = rho_cmds

        # list of auths to try
        self.auths = auths
        
        # the auth we actually used
        self.auth = None

        # do we try to use an ssh-agent for this connection?
        self.allow_agent = allow_agent

        # do we try to let paramiko search for ssh keys for
        # this connection?
        self.look_for_keys = False

        self.timeout = timeout
        self.command_output = None
        self.connection_result = True
        self.returncode = None
        self.auth_used = None
        self.error = None

    def output_callback(self):
        pass

class OutputThread(threading.Thread):
    def __init__(self, report=None):
        self.out_queue = Queue.Queue()
        self.report = scan_report.ScanReport()
        self.quitting = False
        threading.Thread.__init__(self, name="rho_output_thread")
       
    def quit(self):
        self.quitting = True

    def run(self):
        while not self.quitting:
            ssh_job = self.out_queue.get()
            if ssh_job == "quit":
                self.quit()

            try:
                self.report.add(ssh_job)
            except Exception, e:
                log.error("Exception: %s" % e)
                log.error(traceback.print_tb(sys.exc_info()[2]))
                self.quit()

            self.out_queue.task_done()


class SshThread(threading.Thread):
    def __init__(self, thread_id, ssh_queue, output_queue):
        self.ssh_queue = ssh_queue
        self.out_queue = output_queue
        self.id = thread_id
        self.quitting = False
        threading.Thread.__init__(self, name="rho_ssh_thread-%s" % thread_id)
        self.ssh = None

    def quit(self):
        self.quitting = True

    def connect(self, ssh_job):
        # do the actual paramiko ssh connection
           # Copy the list of ports, we'll modify it as we go:
        ports_to_try = list(ssh_job.ports)

        found_port = None # we'll set this once we identify a port that works
        found_auth = False

        while True:
            if found_auth:
                break

            if found_port != None:
                log.warn("Found ssh on %s:%s, but no auths worked." %
                        (ssh_job.ip, found_port))
                break

            if len(ports_to_try) == 0:
                log.debug("Could not find/connect to ssh on: %s" % ssh_job.ip)
                err = _("unable to connect")
                ssh_job.error = err
                break

            port = ports_to_try.pop(0)

            for auth in ssh_job.auths:
                ssh_job.error = None

                debug_str = "%s:%s/%s" % (ssh_job.ip, port, auth.name)
                # this checks the case of a passphrase we can't decrypt
                try:
                    pkey = get_pkey(auth)
                except paramiko.SSHException, e:
                    # paramiko throws an SSHException for pretty much everything... ;-<
                    log.error("ssh key error for %s: %s" % (debug_str, str(e)))
                    ssh_job.error = str(e)
                    continue

                self.ssh = paramiko.SSHClient()
                self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                try:
                    log.info("trying: %s" % debug_str)

                    self.ssh.connect(ssh_job.ip, port=int(port), 
                                     username=auth.username,
                                     password=auth.password,
                                     pkey=pkey,
                                     # FIXME: 
                                     # we should probably set this somewhere
                                     allow_agent=ssh_job.allow_agent,
                                     look_for_keys=ssh_job.look_for_keys,
                                     timeout=ssh_job.timeout)
                    ssh_job.port = port
                    ssh_job.auth = auth
                    found_port = port
                    found_auth = True
                    log.info("success: %s" % debug_str)
                    break

                # Implies we've found an SSH server listening:
                except paramiko.AuthenticationException, e:
                    # Because we stop checking ports once we find one where ssh
                    # is listening, we can report the error message here and it
                    # will end up in the final report correctly:
                    err = _("login failed")
                    log.error(err)
                    ssh_job.error = err
                    found_port = port
                    continue

                # No route to host:
                except socket.error, e:
                    log.warn("No route to host, skipping port: %s" % debug_str)
                    ssh_job.error = str(e)
                    break

                # TODO: Hitting a live port that isn't ssh will result in
                # paramiko.SSHException, do we need to handle this explicitly?

                # Something else happened:
                except Exception, detail:
                    log.warn("Connection error: %s - %s" % (debug_str,
                        str(detail)))
                    ssh_job.error = str(detail)
                    continue



    def run_cmds(self, ssh_job, callback=None):
        for rho_cmd in ssh_job.rho_cmds:
            output = []
            for cmd_string in rho_cmd.cmd_strings:
                stdin, stdout, stderr = self.ssh.exec_command(cmd_string)
                output.append((stdout.read(), stderr.read()))
            rho_cmd.populate_data(output)

    def get_transport(self, ssh_job):
        if ssh_job.ip is "":
            return None

        try:
            self.connect(ssh_job)
            if not self.ssh:
                return

            # there was a connection/auth failure
            if ssh_job.error:
                return
            self.run_cmds(ssh_job)
            self.ssh.close()


        except Exception, e:
            log.error("Exception on %s: %s" % (ssh_job.ip, e))
 #           log.error(sys.exc_type())
            log.error(sys.exc_info())
            log.error(traceback.print_tb(sys.exc_info()[2]))
            ssh_job.connection_result = False
            ssh_job.command_output = e


    def run(self):
        try:
            # grab a "ssh_job" off the q
            ssh_job = self.ssh_queue.get()
            self.get_transport(ssh_job)
            
            self.out_queue.put(ssh_job)
            self.ssh_queue.task_done()

        except Exception, e:
            log.error("Exception: %s" % e)
#            log.error(sys.exc_type())
            log.error(traceback.print_tb(sys.exc_info()[2]))
            
            
        
class SshJobs():
    def __init__(self):
        # cmdSrc is some sort of list/iterator thing

        self.verbose = True
        self.max_threads = 10  

        self.ssh_queue = Queue.Queue()
        self.ssh_jobs = []

    def queue_jobs(self, ssh_job):
        self.ssh_queue.put(ssh_job, block=True)

    def start_ssh_queue(self):
        for thread_num in range(self.max_threads):
            ssh_thread = SshThread(thread_num, 
                                   self.ssh_queue,
                                   self.output_thread.out_queue)
            ssh_thread.setDaemon(True)
            ssh_thread.start()
        

    def start_output_queue(self):
        self.output_thread = OutputThread()
        self.output_thread.setDaemon(True)
        self.output_thread.start()
        

    def run_jobs(self, ssh_jobs=None, callback=None):
        if ssh_jobs:
            self.ssh_jobs = ssh_jobs

        # no point in spinning up 10 threads for one connection...
        if len(self.ssh_jobs) < self.max_threads:
            self.max_threads = len(self.ssh_jobs)
        
        self.start_output_queue()
        self.start_ssh_queue()

        while self.ssh_jobs:
            for ssh_job in self.ssh_jobs:
                # we don't set a cap on Queue size, should we? 
                if not self.ssh_queue.full():
                    self.queue_jobs(ssh_job)
                    self.ssh_jobs.remove(ssh_job)
        self.ssh_queue.join()
        self.output_thread.out_queue.join()


