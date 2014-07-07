
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

import sys
import time
import re

import gettext
t = gettext.translation('rho', 'locale', fallback=True)
_ = t.ugettext


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

# any command in this list will not be automatically added to the default list of commands
NONDEFAULT_CMDS = ['base', 'file', 'script']

class RhoCmd(object):
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

# a RhoCmd subclass for commands that don't fit elsewhere
class MiscRhoCmd(RhoCmd):
    name = "misc"
    cmd_strings = ['date']

    fields = {'misc.date': _('date')}

    def parse_data(self):

        self.data['misc.date'] = self.cmd_results[0][0].strip()

class UnameRhoCmd(RhoCmd):
    name = "uname"
    cmd_strings = ["uname -s", "uname -n", "uname -p", "uname -r", "uname -a", "uname -i"]

    fields = {'uname.os': _('uname -s (os)'),
              'uname.hostname': _('uname -n (hostname)'),
              'uname.processor': _('uname -p (processor)'),
              'uname.kernel': _('uname -r (kernel)'),
              'uname.all': _('uname -a (all)'),
              'uname.hardware_platform': _('uname -i (hardware_platform)')}

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
    fields = {'redhat-release.name': _("name of package that provides 'redhat-release'"),
              'redhat-release.version': _("version of package that provides 'redhat-release'"),
              'redhat-release.release': _("release of package that provides 'redhat-release'")}

    def parse_data(self):
        # new line seperated string, one result only
        if self.cmd_results[0][1]:
            # and/or, something not dumb
            self.data = {'name': 'error', 'version': 'error', 'release': 'error'}
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
    fields = {'etc-release.etc-release': _('contents of /etc/release (or equilivent)')}

    def __init__(self):
        release_files = ["/etc/redhat-release", "/etc/release", "/etc/lsb-release",
                         "/etc/debian_release", "/etc/SuSE-release",
                         "/etc/mandriva-release", "/etc/enterprise-release",
                         "/etc/sun-release", "/etc/slackware-release",
                         "/etc/ovs-release", "/etc/arch-release"]
        cmd_string = """for i in %s; do if [ -f "$i" ] ; then cat $i; fi ;  done""" % string.join(release_files, ' ')
        self.cmd_strings = [cmd_string]
        RhoCmd.__init__(self)

    def parse_data(self):
        self.data['etc-release.etc-release'] = string.join(self.cmd_results[0]).strip()


class ScriptRhoCmd(RhoCmd):
    name = "script"
    cmd_strings = []
    fields = {'script.output': _('output of script'),
              'script.error': _('error output of script'),
              'script.command': _('name of script')}

    def __init__(self, command):
        self.command = command
        self.cmd_strings = [self.command]
        RhoCmd.__init__(self)

    def parse_data(self):
        self.data['%s.output' % self.name] = self.cmd_results[0][0]
        self.data['%s.error' % self.name] = self.cmd_results[0][1]
        self.data['%s.command' % self.name] = self.command


# linux only...
class CpuRhoCmd(RhoCmd):
    name = "cpu"
    fields = {'cpu.count': _('number of processors'),
              'cpu.vendor_id': _("cpu vendor name"),
              'cpu.bogomips': _("bogomips"),
              'cpu.cpu_family': _("cpu family"),
              'cpu.model_name': _("name of cpu model"),
              'cpu.model_ver': _("cpu model version")}

    def __init__(self):
        self.cmd_strings = ["cat /proc/cpuinfo"]
        RhoCmd.__init__(self)

    def parse_data(self):
        self.data = self.parse_data_cpu(self.cmd_results)

    def parse_data_cpu(self, results):
        data = {}
        cpu_count = 0
        for line in results[0][0].splitlines():
            if line.find("processor") == 0:
                cpu_count = cpu_count + 1
        data["cpu.count"] = cpu_count

        cpu_dict = {}
        for line in results[0][0].splitlines():
            # first blank line should be end of first cpu
            # for this case, we are only grabbing the fields from the first
            # cpu and the total count. Should be close enough.
            if line == "":
                break
            parts = line.split(':')
            # should'nt be ':', but just in case, join all parts and strip
            cpu_dict[parts[0].strip()] = ("".join(parts[1:])).strip()

        # we don't need everything, just parse out the interesting bits

        # FIXME: this only supports i386/x86_64. We could add support for more
        # but it's a lot of ugly code (see read_cpuinfo() in smolt.py from smolt
        # [I know it's ugly, I wrote it...]) That code also needs the value of uname()
        # available to it, which we don't currently have a way of plumbing in. So
        # x86* only for now... -akl
        # empty bits to return if we are on say, ia64
        data.update({'cpu.vendor_id': '',
                     'cpu.model_name': '',
                     'cpu.bogomips': '',
                     'cpu.cpu_family': '',
                     'cpu.model_ver': ''})

        try:
            self.get_x86_cpu_info(data, cpu_dict)
        except:
            pass

        return data

    def get_x86_cpu_info(self, data, cpu_dict):
        data["cpu.vendor_id"] = cpu_dict.get("vendor_id")
        # model name should help find kvm/qemu guests...
        data["cpu.model_name"] = cpu_dict.get("model name")
        # they would take my linux card away if I didn't include bogomips
        data["cpu.bogomips"] = cpu_dict.get("bogomips")
        data["cpu.cpu_family"] = cpu_dict.get("cpu family")
        data["cpu.model_ver"] = cpu_dict.get("model")


class _GetFileRhoCmd(RhoCmd):
    name = "file"
    cmd_strings = []
    filename = None

    def __init__(self):
        self.cmd_string_template = "if [ -f %s ] ; then cat %s ; fi"
        self.cmd_strings = [self.cmd_string_template % (self.filename, self.filename)]
        RhoCmd.__init__(self)

    def parse_data(self):
        self.data["%s.contents" % self.name] = "".join(self.cmd_results[0])


class EtcIssueRhoCmd(_GetFileRhoCmd):
    name = "etc-issue"
    filename = "/etc/issue"
    fields = {'etc-issue.etc-issue': _('contents of /etc/issue')}

    def parse_data(self):
        self.data["etc-issue.etc-issue"] = string.strip(self.cmd_results[0][0])


class InstnumRhoCmd(_GetFileRhoCmd):
    name = "instnum"
    filename = "/etc/sysconfig/rhn/install-num"
    fields = {'instnum.instnum': _('installation number')}

    def parse_data(self):
        self.data["instnum.instnum"] = string.strip(self.cmd_results[0][0])


class SystemIdRhoCmd(_GetFileRhoCmd):
    name = "systemid"
    filename = "/etc/sysconfig/rhn/systemid"
    # FIXME: there are more fields here, not sure it's worth including them as options
    fields = {'systemid.system_id': _('Red Hat Network system id'),
              'systemid.username': _('Red Hat Network username')}

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


class DmiRhoCmd(RhoCmd):
    # note this test doesn't work well, or at all, for non root
    # users by default.
    name = "dmi"
    fields = {'dmi.bios-vendor': _('BIOS vendor info from DMI'),
              'dmi.bios-version': _('BIOS version info from DMI'),
              'dmi.system-manufacturer': _('System manufacturer from DMI'),
              'dmi.processor-family': _('Processor family from DMI')}

    def __init__(self):
        self.cmd_strings = ["dmidecode -s bios-vendor",
                            "dmidecode -s bios-version",
                            "dmidecode -s system-manufacturer",
                            "dmidecode -s processor-family"]
        RhoCmd.__init__(self)

    def parse_data(self):
        if self.cmd_results[0][0] and not self.cmd_results[0][1]:
            self.data['dmi.bios-vendor'] = string.strip(self.cmd_results[0][0])
        if self.cmd_results[1][0] and not self.cmd_results[1][1]:
            self.data['dmi.bios-version'] = string.strip(self.cmd_results[1][0])
        if self.cmd_results[2][0] and not self.cmd_results[2][1]:
            self.data['dmi.system-manufacturer'] = string.strip(self.cmd_results[2][0])
        if self.cmd_results[3][0] and not self.cmd_results[3][1]:
            self.data['dmi.processor-family'] = string.strip(self.cmd_results[3][0])


class VirtRhoCmd(CpuRhoCmd):
    # try to determine if we are a virt guest, a host, or bare metal
    name = "virt"
    fields = {'virt.virt': _("If a host is a virt guest, host, or bare metal"),
              'virt.type': _("What type of virtualization a system is running")}

    def __init__(self):
        CpuRhoCmd.__init__(self)
        cmd_template = "if [ -e %s ] ; then echo \"true\"; else echo \"false\"; fi"
        self.cmd_strings.extend(["dmidecode -s system-manufacturer",
                                 "ps aux | grep xend | grep -v grep",
                                 cmd_template % "/proc/xen/privcmd",
                                 cmd_template % "/dev/kvm",
                                 "virt-what",
                                 "echo $?"]
                                 )

    def parse_data(self):
        self.data["virt.virt"] = ""
        self.data["virt.type"] = ""
        # Run virt-what and return if it was successful
        if not self._check_virt_what():
            # check /proc/cpuinfo to see if we are Qemu/kvm
            self._check_cpuinfo_for_qemu()

            self._check_for_dev_kvm()
            # run dmidecode again, see what system-manufacturer is and
            # and if know it (also, check to see if dmidecode fails, like it
            # will for non root)
            self._check_dmidecode()
            # look for xen files (proc/xen/privcmd, /proc/xen/capabilities)
            #
            self._check_for_xen()
            # see if we are running xend...
            self._check_for_xend()


    # We are going to try a variety of hacks and kluges to see if we are virt,
    # and if so, what kind. Mainly looking for xen/kvm here, but if anything else
    # is easy to detect, try that too.

    # based heavily on "virt-what" and facters virt detections
    # can't use virt-what since it's not on most systems
    # it's also relys on root access...

    def _check_cpuinfo_for_qemu(self):
        # look at model name of /proc/cpuinfo
        data = self.parse_data_cpu(self.cmd_results)
        # model_name can be an empty string...
        if data["cpu.model_name"] and data["cpu.model_name"][:4] == "QEMU":
            # hmm, it could be regular old qemu here, but
            # this is probably close enough for reporting
            self.data["virt.type"] = "kvm"
            self.data["virt.virt"] = "virt-guest"
            return True
        return False

    def _check_for_dev_kvm(self):
        dev_kvm = None
        if self.cmd_results[4][0] and not self.cmd_results[4][1]:
            dev_kvm = string.strip(self.cmd_results[4][0])
        if dev_kvm == "true":
            self.data["virt.type"] = "kvm"
            self.data["virt.virt"] = "virt-host"
    # look at the results of dmidecode for hints about what type of
    # virt we have. could probably also track vmware esx version with
    # bios version. None of this works as non root, so it's going to
    # fail most of the time.

    def _check_dmidecode(self):
        manuf = None
        if self.cmd_results[1][0] and not self.cmd_results[1][1]:
            manuf = string.strip(self.cmd_results[1][0])
        if manuf:
            if manuf.find("VMware") > -1:
                self.data["virt.type"] = "vmware"
                self.data["virt.virt"] = "virt-guest"

            if manuf.find("innotek GmbH") > -1:
                self.data["virt.type"] = "virtualbox"
                self.data["virt.virt"] = "virt-guest"

            if manuf.find("Microsoft") > -1:
                self.data["virt.type"] = "virtualpc"
                self.data["virt.virt"] = "virt-guest"

    def _check_for_xend(self):
        # It would be way cooler if we could poke the cpuid and see if
        # is a xen guest, but that requires a util to do it, and root
        # access.
        if self.cmd_results[2][0] and not self.cmd_results[2][1]:
            # is xend running? must be a xen host
            # ugly...
            self.data["virt.type"] = "xen"
            self.data["virt.virt"] = "virt-host"

    def _check_for_xen(self):
        # look for /proc/xen/privcmd
        # Note: xen show "qemu" as cputype as well, so we do this
        # after looking at cpuinfo

        if self.cmd_results[3][0] and not self.cmd_results[3][1]:
            if string.strip(self.cmd_results[3][0]) == "true":
                self.data["virt.type"] = "xen"
                self.data["virt.virt"] = "virt-guest"

    def _check_virt_what(self):
        result = False
        if self.cmd_results[5][0] and not self.cmd_results[5][1]:
            output = self.cmd_results[5][0].strip()
            exitcode = int(self.cmd_results[6][0].strip())
            if exitcode == 0:
                if output != "virt-what: this script must be run as root":
                    if output != "":
                        self.data["virt.type"] = output
                        self.data["virt.virt"] = "virt-guest"
                        result = True
                    else:
                        self.data["virt.type"] = "unknown"
                        self.data["virt.virt"] = "virt-host"
        return result


# the list of commands to run on each host
class RhoCmdList(object):

    def __init__(self):
        self.cmds = {}
        self.cmds['uname'] = UnameRhoCmd()

def default_cmds():
    return filter(is_rho_cmd, list(sys.modules[__name__].__dict__.values()))

# essentially from rho cli. Determines if a given class is an RhoCmd that we want as a default
def is_rho_cmd(clazz):
    return isinstance(clazz, type) and \
        issubclass(clazz, sys.modules[__name__].RhoCmd) and \
        clazz.name not in NONDEFAULT_CMDS
