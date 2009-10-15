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
        outfile - String: Path to the file where we'll store results.
    """
    def __init__(self, output_queue, verbose=True, outfile=None):
        """Name ourselves and assign the variables we were instanciated with."""
        threading.Thread.__init__(self, name="OutputThread")
        self.output_queue = output_queue
        self.verbose = verbose
        self.outfile = outfile
        self.quitting = False

    def run(self):
        while not self.quitting:
            queueObj = self.output_queue.get()
            if queueObj == "quit":
                self.quit()
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
                    
                # These variable assignments are just here for readability further down
                host = queueObj.ip
                username = queueObj.auth.username
                password = queueObj.auth.password
                timeout = queueObj.timeout
                commands = queueObj.cmds
                
                success, command_output = attemptConnection(host, username, password, timeout, commands)
                if success:
                    queueObj.connection_result = "SUCCESS"
                else:
                    queueObj.connection_result = "FAILED"
                queueObj.command_output = command_output
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

def paramikoConnect(host, username, password, timeout):
    """Connects to 'host' and returns a Paramiko transport object to use in further communications"""
    # Uncomment this line to turn on Paramiko debugging (good for troubleshooting why some servers report connection failures)
    #paramiko.util.log_to_file('paramiko.log')
    ssh = paramiko.SSHClient()
    try:
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, port=22, username=username, password=password, timeout=timeout)
    except Exception, detail:
        # Connecting failed (for whatever reason)
        ssh = str(detail)
    return ssh

def executeCommand(transport, command, password=None):
    """Executes the given command via the specified Paramiko transport object.  Will execute as sudo if passed the necessary variables (sudo=True, password, run_as).
    Returns stdout (after command execution)"""
    host = transport.get_host_keys().keys()[0]
    stdin, stdout, stderr = transport.exec_command(command)
    command_output = stdout.readlines()
    command_output = "".join(command_output)
    return command_output

def attemptConnection(
        host,
        username,
        password,
        timeout=30, # Connection timeout
        commands=False, # Either False for no commnads or a list
        ):

    connection_result = True
    command_output = []

    if host != "":
        try:
            ssh = paramikoConnect(host, username, password, timeout)
            if type(ssh) == type(""): # If ssh is a string that means the connection failed and 'ssh' is the details as to why
                connection_result = False
                command_output = ssh
                return connection_result, command_output
            command_output = []
            if commands:
                for command in commands: # This makes a list of lists (each line of output in command_output is it's own item in the list)
                    command_output.append(executeCommand(transport=ssh, command=command, password=password))
            elif commands is False and execute is False: # If we're not given anything to execute run the uptime command to make sure that we can execute *something*
                command_output = executeCommand(transport=ssh, command='uptime',  password=password)

            ssh.close()
            command_count = 0
            for output in command_output: # Clean up the command output
                command_output[command_count] = output
                command_count = command_count + 1
        except Exception, detail:
            # Connection failed
            #print "Exception: %s" % detail
            connection_result = False
            command_output = detail
            ssh.close()
        return connection_result, command_output

def sshpt(
        hostlist, # List - Hosts to connect to
        username,
        password,
        max_threads=10, # Maximum number of simultaneous connection attempts
        timeout=30, # Connection timeout
        commands=False, # List - Commands to execute on hosts (if False nothing will be executed)
        verbose=True, # Whether or not we should output connection results to stdout
        outfile=None, # Path to the file where we want to store connection results
        output_queue=None # Queue.Queue() where connection results should be put().  If none is given it will use the OutputThread default (output_queue)
        ):

    if output_queue is None:
        output_queue = startOutputThread(verbose, outfile)
    # Start up the Output and SSH threads
    ssh_connect_queue = startSSHQueue(output_queue, max_threads)
    
    if not commands and not local_filepath: # Assume we're just doing a connection test
        commands = ['echo CONNECTION TEST',]

    while len(hostlist) != 0: # Only add items to the ssh_connect_queue if there are available threads to take them.
        for host in hostlist:
            if ssh_connect_queue.qsize() <= max_threads:
                queueSSHConnection(ssh_connect_queue, host, username, password, timeout, commands)
                hostlist.remove(host)
        sleep(1)
    ssh_connect_queue.join() # Wait until all jobs are done before exiting
    return output_queue

