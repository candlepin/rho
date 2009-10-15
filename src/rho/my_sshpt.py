#!/usr/bin/env python

#import ssh_jobs
# Import built-in Python modules
import getpass, threading, Queue, sys, os, re, datetime
from optparse import OptionParser
from time import sleep

import paramiko

class GenericThread(threading.Thread):
    """A baseline thread that includes the functions we want for all our threads so we don't have to duplicate code."""
    def quit(self):
        self.quitting = True

class OutputThread(GenericThread):
    """This thread is here to prevent SSHThreads from simultaneously writing to the same file and mucking it all up.  Essentially, it allows sshpt to write results to an outfile as they come in instead of all at once when the program is finished.  This also prevents a 'kill -9' from destroying report resuls and also lets you do a 'tail -f <outfile>' to watch results in real-time.
    
        output_queue: Queue.Queue(): The queue to use for incoming messages.
        verbose - Boolean: Whether or not we should output to stdout.
    """
    def __init__(self, output_queue, verbose=True):
        """Name ourselves and assign the variables we were instanciated with."""
        threading.Thread.__init__(self, name="OutputThread")
        self.output_queue = output_queue
        self.verbose = verbose
        self.quitting = False

    def run(self):
        while not self.quitting:
            queueObj = self.output_queue.get()
            if queueObj == "quit":
                self.quit()

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

    def run (self):
        try:
            while not self.quitting:
                queueObj = self.ssh_connect_queue.get()
#                if queueObj == 'quit':
#                    self.quit()
                    
#                success, command_output = attemptConnection(host, username, password, timeout, commands)
                attemptConnection(queueObj)

                #hmm, this is weird...
                if queueObj.connection_status:
                    queueObj.connection_result = "SUCCESS"
                else:
                    queueObj.connection_result = "FAILED"

                self.output_queue.put(queueObj)
                self.ssh_connect_queue.task_done()
                # just for progress, etc...
                if queueObj.output_callback:
                    queueObj.output_callback()
        except Exception, detail:
            print detail
            self.quit()

def startOutputThread(verbose, outfile):
    """Starts up the OutputThread (which is used by SSHThreads to print/write out results)."""
    output_queue = Queue.Queue()
    output_thread = OutputThread(output_queue, verbose, outfile)
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



def paramikoConnect(ssh_job):
    """Connects to 'host' and returns a Paramiko transport object to use in further communications"""
    # Uncomment this line to turn on Paramiko debugging (good for troubleshooting why some servers report connection failures)
    #paramiko.util.log_to_file('paramiko.log')
    ssh = paramiko.SSHClient()

    # FIXME: akl
    # this is probably the place to try the different auth in order, and set some
    # value on the ssh_job type so we can update config properly
    try:
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ssh_job.ip, port=ssh_job.port, 
                    username=ssh_job.auth.username,
                    password=ssh_job.auth.password, 
                    timeout=ssh_job.timeout)
    except Exception, detail:
        # Connecting failed (for whatever reason)
        ssh = str(detail)
    return ssh


def excecuteCommands(tranport, rho_commands):
    host = transport.get_host_keys().keys()[0]
    output = []
    for rho_cmd in rho_commands:
        for cmd_string in rho_cmd.cmd_strings:
            stdin, stdout, stderr = transport.exec_command(cmd_string)
            # one item in the list for each cmd stdout
            output.append(stdout.readlines(), stderr.readlines())
        rho_cmd.populate_data(output)
    return rho_commands

def attemptConnection(ssh_job):
    # ssh_job is a SshJob object

    if host != "":
        try:
            ssh = paramikoConnect(ssh_job)
            if type(ssh) == type(""): # If ssh is a string that means the connection failed and 'ssh' is the details as to why
                ssh_job.command_output = ssh
                ssh_job.connection_result = False
            command_output = []
            executeCommands(transport=ssh, commands=ssh_job.rho_cmds)
            ssh.close()

        except Exception, detail:
            # Connection failed
            #print "Exception: %s" % detail
            
            ssh_job.connection_result = False
            ssh_job.command_output = detail
            ssh.close()

