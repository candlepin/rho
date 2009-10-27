
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

import string
# for parsing systemid
import xmlrpclib
# for expat exceptions...
import xml

import gettext
t = gettext.translation('rho', 'locale', fallback=True)
_ = t.ugettext

from rho.log import log

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
    fields = {}
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
        # FIXME: how do we handle errors in rho_cmds? we could add a "errors" list
        # to the ssh_job and include the info about each job that failed? --akl
        self.parse_data()


    # subclasses need to implement this, this is what parses the output
    # and packs in the self.data.
    def parse_data(self):

        # but more or less something like:


        raise NotImplementedError

    
class UnameRhoCmd(RhoCmd):
    name = "uname"
    cmd_strings = ["uname -s", "uname -n", "uname -p", "uname -r", "uname -a", "uname -i"]

    fields = {'uname.os':_('uname -s (os)'),
              'uname.hostname':_('uname -n (hostname)'),
              'uname.processor':_('uname -p (processor)'),
              'uname.kernel':_('uname -r (kernel)'),
              'uname.all':_('uname -a (all)'),
              'uname.hardware_platform':_('uname -i (hardware_platform)')}

    def parse_data(self):
        self.data['uname.os'] = self.cmd_results[0][0].strip()
        self.data['uname.hostname'] = self.cmd_results[1][0].strip()
        self.data['uname.processor'] = self.cmd_results[2][0].strip()
        self.data['uname.kernel'] = self.cmd_results[3][0].strip()
        self.data['uname.all'] = self.cmd_results[4][0].strip()
        if not self.cmd_results[3][1]:
            self.data['uname.hardware_platform'] = self.cmd_results[5][0].strip()

class RedhatReleaseRhoCmd(RhoCmd):
    name = "redhat-release"
    cmd_strings = ["""rpm -q --queryformat "%{NAME}\n%{VERSION}\n%{RELEASE}\n" --whatprovides redhat-release"""]
    fields = {'redhat-release.name':_("name of package that provides 'redhat-release'"),
              'redhat-release.version':_("version of package that provides 'redhat-release'"),
              'redhat-release.release':_("release of package that provides 'redhat-release'")}

    def parse_data(self):
        # new line seperated string, one result only
        if self.cmd_results[0][1]:
            # and/or, something not dumb
            self.data = {'name':'error', 'version':'error', 'release':'error'}
            return
        fields = self.cmd_results[0][0].splitlines()
        # no shell gives a single bogus line of output, we expect 3
        if len(fields) >= 3:
            self.data['redhat-release.name'] = fields[0].strip()
            self.data['redhat-release.version'] = fields[1].strip()
            self.data['redhat-release.release'] = fields[2].strip()

# take a blind drunken flailing stab at guessing the os
class EtcReleaseRhoCmd(RhoCmd):
    name = "etc-release"
    fields = {'etc-release.etc-release':_('contents of /etc/release (or equilivent)')}
    def __init__(self):
        release_files = ["/etc/redhat-release", "/etc/release",
                         "/etc/debian_release", "/etc/Suse-release",
                         "/etc/mandriva-release", "/etc/enterprise-release",
                         "/etc/ovs-release", "/etc/arch-release"]
        cmd_string = """for i in %s; do if [ -f "$i" ] ; then cat $i; fi ;  done""" % string.join(release_files, ' ')
        self.cmd_strings = [cmd_string]
        RhoCmd.__init__(self)
 
    def parse_data(self):
        self.data['etc-release.etc-release'] = string.join(self.cmd_results[0]).strip()


class ScriptRhoCmd(RhoCmd):
    name = "script"
    cmd_strings = []
    fields = {'script.output':_('output of script'),
              'script.error':_('error output of script'),
              'script.command':_('name of script')}

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

# linux only...
class CpuRhoCmd(RhoCmd):
    name = "cpu"
    fields = {'cpu.count':_('number of processors')}
    
    def __init__(self):
        self.cmd_strings = ["cat /proc/cpuinfo"] 
        RhoCmd.__init__(self)

    def parse_data(self):
        cpu_count = 0
        for line in self.cmd_results[0][0].splitlines():
            if line.find("processor") == 0:
                cpu_count = cpu_count + 1
        self.data["cpu.count"] = cpu_count



class EtcIssueRhoCmd(GetFileRhoCmd):
    name = "etc-issue"
    filename = "/etc/issue"
    fields = {'etc-issue.etc-issue':_('contents of /etc/issue')}

    def parse_data(self):
        self.data["etc-issue.etc-issue"] = string.strip(self.cmd_results[0][0])
    
class InstnumRhoCmd(GetFileRhoCmd):
    name = "instnum"
    filename = "/etc/sysconfig/rhn/install-num"
    fields = {'instnum.instnum':_('installation number')}

    def parse_data(self):
        self.data["instnum.instnum"] =  string.strip(self.cmd_results[0][0])

class SystemIdRhoCmd(GetFileRhoCmd):
    name = "systemid"
    filename = "/etc/sysconfig/rhn/systemid"
    #FIXME: there are more fields here, not sure it's worth including them as options
    fields = {'systemid.system_id':_('Red Hat Network system id'),
              'systemid.username':_('Red Hat Network username')}
    def parse_data(self):
        # if file is empty, or we get errors, skip...
        if not self.cmd_results[0][0] or self.cmd_results[0][1]:
            # no file, nothing to parse
            return
        blob = "".join(self.cmd_results[0])
        # loads returns param/methodname, we just want the params
        # and only the first param at that
        try:
            systemid = xmlrpclib.loads(blob)[0][0]
        except xml.parsers.expat.ExpatError:
            # log here? not sure it would help...
            return
        for key in systemid:
            self.data["%s.%s" % (self.name, key)] = systemid[key]
        

# the list of commands to run on each host
class RhoCmdList():
    def __init__(self):
        self.cmds = {}
        self.cmds['uname'] = UnameRhoCmd()
