
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
        self.cmd_outputs = []
        self.data = {}

    # we're not actually running the class on the hosts, so
    # we will need to populate it with the output of the ssh stuff
    # we can send a list of commands, so we expect output to be a list
    # of output strings
    def populate_data(self, output):
        self.cmd_outputs = output
        self.parse_data()

    # subclasses need to implement this, this is what parses the output
    # and packs in the self.data.
    def parse_data(self):
        raise NotImplementedError

    
class UnameRhoCmd(RhoCmd):
    name = "uname"
    cmd_strings = ["uname -s", "uname -n", "uname -p"]

    def parse_data(self):
        self.data['os'] = self.cmd_outputs[0]
        self.data['hostname'] = self.cmd_outputs[1]
        self.data['processor'] = self.cmd_outputs[2]


class RedhatReleaseRhoCmd(RhoCmd):
    name = "redhat-release"
    cmd_strings = ["""rpm -q --queryformat "%{NAME}\n%{VERSION}\n%{RELEASE}\n" --whatprovides redhat-release"""]

    def parse_data(self):
        # new line seperated string, one result only
        fields = self.cmd_outputs[0].splitlines()
        self.data['name'] = fields[0]
        self.data['version'] = fields[1]
        self.data['release'] = fields[2]

# the list of commands to run on each host
class RhoCmdList():
    def __init__(self):
        self.cmds = {}
        self.cmds['uname'] = UnameRhoCmd()
