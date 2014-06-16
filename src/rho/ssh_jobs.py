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

import gettext
t = gettext.translation('rho', 'locale', fallback=True)
_ = t.ugettext


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

# on python 2.4, the Queue class doesnt .join and .task_done,which we use and
# are nice. So we add them to Queue24 if we need to


class Queue24(Queue.Queue):

    def __init__(self, maxsize=0):
        # Notify all_tasks_done whenever the number of unfinished tasks
        # drops to zero; thread waiting to join() is notified to resume
        Queue.Queue.__init__(self, maxsize=maxsize)
        self.all_tasks_done = threading.Condition(self.mutex)
        self.unfinished_tasks = 0

    def task_done(self):
        """Indicate that a formerly enqueued task is complete.

        Used by Queue consumer threads.  For each get() used to fetch a task,
        a subsequent call to task_done() tells the queue that the processing
        on the task is complete.

        If a join() is currently blocking, it will resume when all items
        have been processed (meaning that a task_done() call was received
        for every item that had been put() into the queue).

        Raises a ValueError if called more times than there were items
        placed in the queue.
        """
        self.all_tasks_done.acquire()
        try:
            unfinished = self.unfinished_tasks - 1
            if unfinished <= 0:
                if unfinished < 0:
                    raise ValueError('task_done() called too many times')
                # notifyAll became notify_all in 2.6
                self.all_tasks_done.notifyAll()
            self.unfinished_tasks = unfinished
        finally:
            self.all_tasks_done.release()

    def join(self):
        """Blocks until all items in the Queue have been gotten and processed.

        The count of unfinished tasks goes up whenever an item is added to the
        queue. The count goes down whenever a consumer thread calls task_done()
        to indicate the item was retrieved and all work on it is complete.

        When the count of unfinished tasks drops to zero, join() unblocks.
        """
        self.all_tasks_done.acquire()
        try:
            while self.unfinished_tasks:
                self.all_tasks_done.wait()
        finally:
            self.all_tasks_done.release()

    # not exactly the way the 2.6+ Queue class does it, but it's
    # easier and a lot less code this way.
    def _put(self, item):
        self.queue.append(item)
        self.unfinished_tasks += 1


# if I were fancy, this might be a factory
# Check to see if our queue has "join", aka, if we
# are on python2.6 or newer
def OurQueue(*args, **kwargs):
    if getattr(Queue.Queue, 'join', None):
        return Queue.Queue(*args, **kwargs)
    return Queue24(*args, **kwargs)


class SshJob(object):

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
        self.out_queue = OurQueue()
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
            except Exception as e:
                log.error("Exception: %s" % e)
                log.error(traceback.print_tb(sys.exc_info()[2]))
                self.quit()

            self.out_queue.task_done()


# thread/queue for progress stuff so it stays synced and in order...
class ProgressThread(threading.Thread):

    def __init__(self):
        self.prog_queue = OurQueue()
        self.quitting = False
        threading.Thread.__init__(self, name="rho_output_thread")

    def quit(self):
        self.quitting = True

    def run(self):
        print _("Scanning...")
        while not self.quitting:
            prog_buf = self.prog_queue.get()
            print prog_buf

            self.prog_queue.task_done()


class SshThread(threading.Thread):

    def __init__(self, thread_id, ssh_queue, output_queue, prog_queue):
        self.ssh_queue = ssh_queue
        self.out_queue = output_queue
        self.prog_queue = prog_queue
        self.id = thread_id
        self.quitting = False
        threading.Thread.__init__(self, name="rho_ssh_thread-%s" % thread_id)
        self.ssh = None

    def quit(self):
        self.quitting = True

    def show_connect(self, ssh_job, port, auth):
        buf = _("%s:%s with auth %s") % (ssh_job.ip, port, auth.name)
        log.info(buf)
        self.prog_queue.put(buf)

    def connect(self, ssh_job):
        # do the actual paramiko ssh connection

        # Copy the list of ports, we'll modify it as we go:
        ports_to_try = list(ssh_job.ports)

        found_port = None  # we'll set this once we identify a port that works
        found_auth = False

        while True:
            if found_auth:
                break

            if found_port is not None:
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
                except paramiko.SSHException as e:
                    # paramiko throws an SSHException for pretty much everything... ;-<
                    log.error("ssh key error for %s: %s" % (debug_str, str(e)))
                    ssh_job.error = str(e)
                    continue

                self.ssh = paramiko.SSHClient()
                self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                try:
                    log.info("trying: %s" % debug_str)

                    self.show_connect(ssh_job, port, auth)
                    self.ssh.connect(ssh_job.ip, port=int(port),
                                     username=auth.username,
                                     password=auth.password,
                                     pkey=pkey,
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
                except paramiko.AuthenticationException as e:
                    # Because we stop checking ports once we find one where ssh
                    # is listening, we can report the error message here and it
                    # will end up in the final report correctly:
                    err = _("login failed")
                    log.error(err)
                    ssh_job.error = err
                    found_port = port
                    continue

                # No route to host:
                except socket.error as e:
                    log.warn("No route to host, skipping port: %s" % debug_str)
                    ssh_job.error = str(e)
                    break

                # TODO: Hitting a live port that isn't ssh will result in
                # paramiko.SSHException, do we need to handle this explicitly?

                # Something else happened:
                except Exception as detail:
                    log.warn("Connection error: %s - %s" % (debug_str,
                                                            str(detail)))
                    ssh_job.error = str(detail)
                    continue

    def run_cmds(self, ssh_job,):
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

        except Exception as e:
            log.error("Exception on %s: %s" % (ssh_job.ip, e))
            log.error(sys.exc_info())
            log.error(traceback.print_tb(sys.exc_info()[2]))
            ssh_job.connection_result = False
            ssh_job.command_output = e

    def run(self):
        while not self.quitting:
            try:
                # grab a "ssh_job" off the q
                ssh_job = self.ssh_queue.get()
                self.get_transport(ssh_job)
                self.out_queue.put(ssh_job)
                self.ssh_queue.task_done()
            except Exception as e:
                log.error("Exception: %s" % e)
                log.error(traceback.print_tb(sys.exc_info()[2]))
                self.ssh_queue.task_done()


class SshJobs(object):

    def __init__(self):
        # cmdSrc is some sort of list/iterator thing

        self.verbose = True
        self.max_threads = 10

        self.ssh_queue = OurQueue()
        self.ssh_jobs = []

    def queue_jobs(self, ssh_job):
        self.ssh_queue.put(ssh_job, block=True)

    def start_ssh_queue(self):
        for thread_num in range(self.max_threads):
            ssh_thread = SshThread(thread_num,
                                   self.ssh_queue,
                                   self.output_thread.out_queue,
                                   self.prog_thread.prog_queue)
            ssh_thread.setDaemon(True)
            ssh_thread.start()

    def start_output_queue(self):
        self.output_thread = OutputThread()
        self.output_thread.setDaemon(True)
        self.output_thread.start()

    def start_prog_queue(self):
        self.prog_thread = ProgressThread()
        self.prog_thread.setDaemon(True)
        self.prog_thread.start()

    def run_jobs(self, ssh_jobs=None, callback=None):
        if ssh_jobs:
            self.ssh_jobs = ssh_jobs

        # no point in spinning up 10 threads for one connection...
        if len(self.ssh_jobs) < self.max_threads:
            self.max_threads = len(self.ssh_jobs)

        self.start_prog_queue()
        self.start_output_queue()
        self.start_ssh_queue()

        while self.ssh_jobs:
            for ssh_job in self.ssh_jobs:
                # we don't set a cap on Queue size, should we?
                if not self.ssh_queue.full():
                    self.queue_jobs(ssh_job)
                    self.ssh_jobs.remove(ssh_job)

        self.ssh_queue.join()
        self.prog_thread.prog_queue.join()
        self.output_thread.out_queue.join()
