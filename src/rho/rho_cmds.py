
# Copyright (c) 2009 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

"""cmds to run on machines being inventory"""


# basic idea, wrapper classes around the cli cmds we run on the machines
# to be inventories. the rho_cmd class will have a string for the 
# actually command to run, a name, a 'data' attrib storing the
# data retrivied (probably just a dict). I think it makes the most
# sense to go ahead and parse the results of the remote cmd when we
# run it and store it then in the data (as opposed to doing it at
# data read time). I think it's pretty small data sets either way, so
# not a big deal. 

# If we use a dict like class for the data, we maybe able to make
# the report generation as simple as python string formatting tricks. 
# I'd like to try to avoid type'ing the data fields and just treating
# everything as strings, since the primary target seems to be csv 
# output. 


class RhoCmd():
    name = "base"
    def __init__(self):
#        self.cmd_strings = cmd
        self.cmd_results = []
        self.data = {}


    # we're not actually running the class on the hosts, so
    # we will need to populate it with the output of the ssh stuff
    # we can send a list of commands, so we expect output to be a list
    # of output strings

    def populate_data(self, results):
        # results is a tuple of (stdout, stderr)
        self.cmd_results = results
        # where do we error check? In the parse_data() step I guess... -akl
        # 
        self.parse_data()

    # subclasses need to implement this, this is what parses the output
    # and packs in the self.data.
    def parse_data(self):

        # but more or less something like:


        raise NotImplementedError

    
class UnameRhoCmd(RhoCmd):
    name = "uname"
    cmd_strings = ["uname -s", "uname -n", "uname -p", "uname -i"]

    def parse_data(self):
        self.data['%s.os' % self.name] = self.cmd_results[0][0].strip()
        self.data['%s.hostname' % self.name] = self.cmd_results[1][0].strip()
        self.data['%s.processor' % self.name] = self.cmd_results[2][0].strip()
        if not self.cmd_results[3][1]:
            self.data['%s.hardware_platform' % self.name] = self.cmd_results[3][0].strip()

class RedhatReleaseRhoCmd(RhoCmd):
    name = "redhat-release"
    cmd_strings = ["""rpm -q --queryformat "%{NAME}\n%{VERSION}\n%{RELEASE}\n" --whatprovides redhat-release"""]

    def parse_data(self):
        # new line seperated string, one result only
        if self.cmd_results[0][1]:
            # and/or, something not dumb
            self.data = {'name':'error', 'version':'error', 'release':'error'}
            return
        fields = self.cmd_results[0][0].splitlines()
        self.data['%s.name' % self.name] = fields[0].strip()
        self.data['%s.version' % self.name ] = fields[1].strip()
        self.data['%s.release' % self.name ] = fields[2].strip()

class ScriptRhoCmd(RhoCmd):
    name = "script"
    cmd_strings = []

    def __init__(self, command):
        self.command = command
        self.cmd_strings = [self.command]
        RhoCmd.__init__(self)

    def parse_data(self):
        self.data['%s.output' % self.name] = self.cmd_results[0][0]
        self.data['%s.error' % self.name] = self.cmd_results[0][1]
        self.data['%s.command' % self.name] = self.command

class GetFileRhoCmd(RhoCmd):
    name = "file"
    cmd_strings = []
    
    def __init__(self):
        self.cmd_string_template = "if [ -f %s ] ; then cat %s ; fi"
        self.cmd_strings = [self.cmd_string_template % (self.filename, self.filename)]
        RhoCmd.__init__(self)

    def parse_data(self):
        self.data["%s.contents" % self.name] = "".join(self.cmd_results[0])

class InstnumRhoCmd(GetFileRhoCmd):
    name = "instnum"
    filename = "/etc/syconfig/rhn/instnum"


class SystemIdRhoCmd(GetFileRhoCmd):
    name = "systemid"
    filename = "/etc/sysconfig/rhn/systemid"

# the list of commands to run on each host
class RhoCmdList():
    def __init__(self):
        self.cmds = {}
        self.cmds['uname'] = UnameRhoCmd()
