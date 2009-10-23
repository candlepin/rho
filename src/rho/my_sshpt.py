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

import gettext
t = gettext.translation('rho', 'locale', fallback=True)
_ = t.ugettext

import getpass, threading, Queue, sys, os, re, datetime

from rho.log import log 
from optparse import OptionParser
from time import sleep
import traceback
import StringIO

import paramiko

import config


class GenericThread(threading.Thread):
    """A baseline thread that includes the functions we want for all our threads so we don't have to duplicate code."""
    def quit(self):
        self.quitting = True

class OutputThread(GenericThread):
    """This thread is here to prevent SSHThreads from simultaneously writing to the same file and mucking it all up.  Essentially, it allows sshpt to write results to an outfile as they come in instead of all at once when the program is finished.  This also prevents a 'kill -9' from destroying report resuls and also lets you do a 'tail -f <outfile>' to watch results in real-time.
    
        output_queue: Queue.Queue(): The queue to use for incoming messages.
        verbose - Boolean: Whether or not we should output to stdout.
    """
    def __init__(self, output_queue, verbose=True, report=None):
        """Name ourselves and assign the variables we were instanciated with."""
        threading.Thread.__init__(self, name="OutputThread")
        self.output_queue = output_queue
        self.verbose = verbose
        self.quitting = False
        self.report = report

    
    def quit(self):
        self.quitting = True

    def write(self, queueObj):
        print queueObj.ip
        for rho_cmd in queueObj.rho_cmds:
            print rho_cmd.name, rho_cmd.data

    def run(self):
        while not self.quitting:
            queueObj = self.output_queue.get()
            if queueObj == "quit":
                self.quit()

            try:
                self.report.add(queueObj)
            except Exception, detail:
                log.error("Exception: %s" % detail)
                log.error(sys.exc_type())
                log.error(traceback.print_tb(sys.exc_info()[2]))
#                self.output_queue.task_done()
                self.quit()
#            self.write(queueObj)
            # somewhere in here, we return the data to...?
            self.output_queue.task_done()

class SSHThread(GenericThread):
    """Connects to a host and optionally runs commands or copies a file over SFTP.
    Must be instanciated with:
      id                    A thread ID
      ssh_connect_queue     Queue.Queue() for receiving orders
      output_queue          Queue.Queue() to output results

    Here's the list of variables that are added to the output queue before it is put():
        queueObj['host']
        queueObj['username']
        queueObj['password']
        queueObj['commands'] - List: Commands that were executed
        queueObj['connection_result'] - String: 'SUCCESS'/'FAILED'
        queueObj['command_output'] - String: Textual output of commands after execution
    """
    def __init__ (self, id, ssh_connect_queue, output_queue):
        threading.Thread.__init__(self, name="SSHThread-%d" % (id,))
        self.ssh_connect_queue = ssh_connect_queue
        self.output_queue = output_queue
        self.id = id
        self.quitting = False

    def quit(self):
        self.quitting = True

    def run (self):
        try:
            while not self.quitting:
                queueObj = self.ssh_connect_queue.get()
                if queueObj == 'quit':
                    self.quit()
                    
#                success, command_output = attemptConnection(host, username, password, timeout, commands)
                attemptConnection(queueObj)

                #hmm, this is weird...
                if queueObj.connection_result:
                    queueObj.connection_result = "SUCCESS"
                else:
                    queueObj.connection_result = "FAILED"

                self.output_queue.put(queueObj)
                self.ssh_connect_queue.task_done()
                # just for progress, etc...
                if queueObj.output_callback:
                    queueObj.output_callback()
        except Exception, detail:
            log.error("Exception: %s" % detail)
            log.error(sys.exc_type())
            log.error(traceback.print_tb(sys.exc_info()[2]))
#            self.output_queue.task_done()
#            self.ssh_connect_queue.task_done()
            self.quit()

def startOutputThread(verbose, report):
    """Starts up the OutputThread (which is used by SSHThreads to print/write out results)."""
    output_queue = Queue.Queue()
    output_thread = OutputThread(output_queue, verbose,report)
    output_thread.setDaemon(True)
    output_thread.start()
    return output_queue

def stopOutputThread():
    """Shuts down the OutputThread"""
    for t in threading.enumerate():
        if t.getName().startswith('OutputThread'):
            t.quit()
    return True

def startSSHQueue(output_queue, max_threads):
    """Setup concurrent threads for testing SSH connectivity.  Must be passed a Queue (output_queue) for writing results."""
    ssh_connect_queue = Queue.Queue()
    for thread_num in range(max_threads):
        ssh_thread = SSHThread(thread_num, ssh_connect_queue, output_queue)
        ssh_thread.setDaemon(True)
        ssh_thread.start()
    return ssh_connect_queue

def stopSSHQueue():
    """Shut down the SSH Threads"""
    for t in threading.enumerate():
        if t.getName().startswith('SSHThread'):
            t.quit()
    return True

def queueSSHConnection(ssh_connect_queue, cmd):
    """Add files to the SSH Queue (ssh_connect_queue)"""
    ssh_connect_queue.put(cmd)
    return True


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

def paramikoConnect(ssh_job):
    """
    Connects to 'host' and returns a Paramiko transport object to use 
    in further communications
    """

    # FIXME: are these for loops right? We try to treat a password required
    # exception differently, but I can't see what we're actually doing with 
    # it.
    for port in ssh_job.ports:
        for auth in ssh_job.auths:
            
            ssh_job.error = None

            # this checks the case of a passphrase we can't decrypt
            try:
                pkey = get_pkey(auth)
            except paramiko.SSHException, detail:
                # paramiko throws an SSHException for pretty much everything... ;-<
                err = _("connection to %s:%s failed using auth class \"%s\" with error: \"%s\"") % (ssh_job.ip, port, auth.name, str(detail))
                log.error(err)
                ssh_job.error = err
                ssh = str(detail)
                continue

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            debug_str = "%s:%s/%s" % (ssh_job.ip, port, auth.name)
            try:
                log.info("trying: %s" % debug_str)

                ssh.connect(ssh_job.ip, port=int(port), 
                            username=auth.username,
                            password=auth.password,
                            pkey=pkey,
                            # FIXME: 
                            # we should probably set this somewhere
                            #allow_agent=False,
                            look_for_keys=False,
                            timeout=ssh_job.timeout)
                ssh_job.port = port
                ssh_job.auth = auth
                log.info("success: %s" % debug_str)
                break
            # FIXME: we can probably get rid of this case and rely on the catchall, the handling is the same... --akl
            except paramiko.PasswordRequiredException, detail:
                err = _("connection to %s:%s failed using auth class \"%s\" with error: \"%s\"") % (ssh_job.ip, port, auth.name, str(detail))
                ssh_job.error = err
                log.error(err)
                # FIXME: This is defined as a SSHCLient above, now it 
                # becomes a string?
                ssh = str(detail)

                # FIXME: Something seems wrong here too, I added the continue
                # to get past an issue where only the first auth was tried:

                # set the successful auth type and port
                continue
            except Exception, detail:
                # Connecting failed (for whatever reason)
                err = _("connection to %s:%s failed using auth class \"%s\" with error: \"%s\"") % (ssh_job.ip, port, auth.name,str(detail))
                log.error(err)
                ssh_job.error = err
                ssh = str(detail)
                log.debug(sys.exc_type())
#                log.debug(traceback.print_tb(sys.exc_info()[2]))
                continue

    # FIXME: Returning something here that's only defined in the for loop,
    # this may be returning None?
    return ssh

def executeCommands(transport, rho_commands):
    host = transport.get_host_keys().keys()[0]
    for rho_cmd in rho_commands:
        output = []
        for cmd_string in rho_cmd.cmd_strings:
            stdin, stdout, stderr = transport.exec_command(cmd_string)
            # one item in the list for each cmd stdout
            output.append((stdout.read(), stderr.read()))
        rho_cmd.populate_data(output)
    return rho_commands

def attemptConnection(ssh_job):
    # ssh_job is a SshJob object

    if ssh_job.ip != "":
        try:
            ssh = paramikoConnect(ssh_job)
            if type(ssh) == type(""): # If ssh is a string that means the connection failed and 'ssh' is the details as to why
                ssh_job.command_output = ssh
                ssh_job.connection_result = False
                return
            command_output = []
            executeCommands(transport=ssh, rho_commands=ssh_job.rho_cmds)
            ssh.close()

        except Exception, detail:
            # Connection failed
            print _("Exception: %s") % detail
            print sys.exc_type()
            print sys.exc_info()
            print traceback.print_tb(sys.exc_info()[2])
            ssh_job.connection_result = False
            ssh_job.command_output = detail
#            ssh.close()

