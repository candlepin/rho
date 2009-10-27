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

# this is based on "sshpt"  http://code.google.com/p/sshpt/

import gettext
t = gettext.translation('rho', 'locale', fallback=True)
_ = t.ugettext


from rho.log import log 

from optparse import OptionParser
import os
import re
import StringIO
import sys
import threading
import traceback
import Queue
import socket

import paramiko

import config
import time

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
    def __init__ (self, id, ssh_connect_queue, output_queue, callback=None):
        threading.Thread.__init__(self, name="SSHThread-%d" % (id,))
        self.ssh_connect_queue = ssh_connect_queue
        self.output_queue = output_queue
        self.id = id
        self.quitting = False
        self.callback = callback

    def quit(self):
	print "quitting"
        self.quitting = True

    def run (self):
        try:
            while not self.quitting:
                queueObj = self.ssh_connect_queue.get()
                if queueObj == 'quit':
		    print "foo", self.id
                    self.quit()
                    
#                if callback:
#                    callback(queueObj)
#                success, command_output = attemptConnection(host, username, password, timeout, commands)
                attemptConnection(queueObj, progress_callback=self.callback)

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


def stopSSHQueue():
    """Shut down the SSH Threads"""
    for t in threading.enumerate():
        if t.getName().startswith('SSHThread'):
            t.quit()
    return True

