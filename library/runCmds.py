#!/usr/bin/python
# Copyright (c) 2009-2016 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#


import gettext
import json
import subprocess as sp
import string
# for parsing systemid
import xmlrpclib
# for expat exceptions...
import xml
import ast
import re
from ansible.module_utils.basic import AnsibleModule

t = gettext.translation('rho', 'locale', fallback=True)
_ = t.ugettext

"""cmds to run on machines being inventory"""


class RhoCmd(object):
    # RhoCmd and its sub-classes are wrapper classes around
    # the cli cmds we run on the host machines. The
    # rho_cmd class will have five dictionaries.

    # The cmd_names dictionary maps all the commands that are associated
    # with the class to the corresponding fields(facts) requested.
    # The cmd_strings dictionary maps each command name to the
    # actual command string that is run in the cli. The results
    # so obtained are stored in the cmd_results dictionary whose
    # keys are the command names. The fields dictionary stores
    # the localized versions of the field names and the data
    # dictionary is responsible for storing all the facts collected
    # from all the classes ever invoked.

    def __init__(self):
        self.cmd_results = {}
        self.data = {}
        self.cmd_strings = {}
        self.cmd_names = {}
        self.name = "cmd_name"

    # run_cmd is what runs the command strings associated
    # to corresponding facts in cli of the host boxes. It
    # accepts an input variable 'facts' which can either be
    # 'all' or a list of facts the user wants to collect
    # associated with the particular RhoCmd. Passing in
    # 'all' would run all the command strings associated
    # with the RhoCmd thereby collecting all facts. Passing
    # in a list of facts would make the method run only
    # the command strings related to those facts.

    def run_cmd(self, facts):

        if not self.cmd_names:
            print "RhoCmd has undefined 'cmd_names'"
            return

        if not self.cmd_strings:
            print "RhoCmd has undefined 'cmd_strings'"
            return

        requested_cmd_names = []

        if type(facts) == list:
            for fact in facts:
                for cmd_name in self.cmd_names.keys():
                    if fact in self.cmd_names[cmd_name]:
                        requested_cmd_names.append(cmd_name)

        elif type(facts) == str:
            if facts == 'all':
                requested_cmd_names = self.cmd_names.keys()
            else:
                print "Invalid string for 'facts'. Only permitted string " \
                      "is 'all'."
                return
        else:
            print "Invalid input for facts. Acceptable inputs are  " \
                  "the string 'all' or a list of strings (one for each fact)"
            return

        for cmd_name in requested_cmd_names:
            cmd_string = self.cmd_strings[cmd_name]
            try:
                process = sp.Popen(cmd_string, shell=True,
                                   stdout=sp.PIPE, stderr=sp.PIPE)
                out, err = process.communicate()
                self.cmd_results[cmd_name] = (out, err)
            except OSError as e:
                print "OSError > ", e.errno
                print "OSError > ", e.strerror
                print "OSError > ", e.filename
                return 1

        self.parse_data()

    # Used to parse the information collected from cli
    # in order to fill in the appropriate values in
    # the data dictionary of a RhoCmd. Defined in
    # sub-class since data collected from cli differs
    # according to the command_string run. This method
    # has been documented according to sub-class
    # specifics.

    def parse_data(self):

        raise NotImplementedError


class DateRhoCmd(RhoCmd):
    # DateRhoCmd has primarily one cmd_string i.e.'data'
    # which is run to grab the system date.

    def __init__(self):
        super(DateRhoCmd, self).__init__()
        self.name = "date"
        self.cmd_names['date'] = ['date.date']
        self.cmd_strings['date'] = 'date'
        self.fields = {'date.date': _('date')}

    # This method parses the result of the cli command
    # 'date' and stores it in the only field date.date.

    def parse_data(self):
        self.data['date.date'] = self.cmd_results['date'][0].strip()


class UnameRhoCmd(RhoCmd):
    # UnameRhoCmd is the wrapper for all cli commands
    # to do with 'uname -<parameter>'. There are six
    # fields currently associated with this class.
    # There are 6 command strings in total that map
    # one on one to each of the 6 fields.

    def __init__(self):
        super(UnameRhoCmd, self).__init__()

        self.name = "uname"

        self.cmd_strings["uname.os"] = "uname -s"
        self.cmd_strings["uname.hostname"] = "uname -n"
        self.cmd_strings["uname.processor"] = "uname -p"
        self.cmd_strings["uname.kernel"] = "uname -r"
        self.cmd_strings["uname.all"] = "uname -a"
        self.cmd_strings["uname.hardware_platform"] = "uname -i"

        self.cmd_names["uname.os"] = ["uname.os"]
        self.cmd_names["uname.hostname"] = ["uname.hostname"]
        self.cmd_names["uname.processor"] = ["uname.processor"]
        self.cmd_names["uname.kernel"] = ["uname.kernel"]
        self.cmd_names["uname.all"] = ["uname.all"]
        self.cmd_names["uname.hardware_platform"] = ["uname.hardware_platform"]

        self.fields = {'uname.os': _('uname -s (os)'),
                       'uname.hostname': _('uname -n (hostname)'),
                       'uname.processor': _('uname -p (processor)'),
                       'uname.kernel': _('uname -r (kernel)'),
                       'uname.all': _('uname -a (all)'),
                       'uname.hardware_platform': _('uname -i '
                                                    '(hardware_platform)')}

    # This method loops through all requested cmd_strings'
    # results and stores maps them to the respective
    # fields in the report.

    def parse_data(self):
        for cmd_name in self.cmd_names.keys():
            if cmd_name in self.cmd_results.keys():
                if not (cmd_name == 'uname.kernel'
                        and self.cmd_results[cmd_name][1]):
                    self.data[self.cmd_names[cmd_name][0]] \
                        = self.cmd_results[cmd_name][0].strip()


class SubmanFactsRhoCmd(RhoCmd):
    # This class wraps around the command strings
    # that are meant to collect all information
    # related to subscription-manager. It has
    # 6 fields associated to it currently. In total
    # it contains 2 command strings one of which maps
    # to the field subman.has_facts_file while the other
    # maps to the rest: 'subman.cpu.core(s)_per_socket',
    # 'subman.cpu.cpu(s)', 'subman.cpu.cpu_socket(s)',
    # 'subman.virt.host_type', and  'subman.virt.is_guest'.

    def __init__(self):
        super(SubmanFactsRhoCmd, self).__init__()

        self.name = "subscription-manager"

        self.cmd_strings["subman_facts_list"] \
            = 'subscription-manager facts --list'
        self.cmd_strings["subman_has_facts"] \
            = 'ls /etc/rhsm/facts | grep .facts'

        self.cmd_names['subman_facts_list'] \
            = ['subman.cpu.core(s)_per_socket',
               'subman.cpu.cpu(s)',
               'subman.cpu.cpu_socket(s)',
               'subman.virt.host_type',
               'subman.virt.is_guest']
        self.cmd_names['subman_has_facts'] = ['subman.hash_facts_file']

        self.fields = {'subman.cpu.core(s)_per_socket': _('cpu.core(s)_'
                                                          'per_socket '
                                                          '(from '
                                                          'subscription'
                                                          '-manager '
                                                          'facts --list)'),
                       'subman.cpu.cpu(s)': _('cpu.cpu(s)'
                                              '(from subscription'
                                              '-manager'
                                              ' facts --list)'),
                       'subman.cpu.cpu_socket(s)': _('cpu.cpu_socket(s)'
                                                     '(from'
                                                     'subscription-manager'
                                                     ' facts --list)'),
                       'subman.virt.host_type': _('virt.host_type'
                                                  '(from '
                                                  'subscription-manager'
                                                  ' facts --list)'),
                       'subman.virt.is_guest': _('virt.is_guest '
                                                 '(from '
                                                 'subscription-manager '
                                                 'facts --list)'),
                       'subman.has_facts_file': _('Whether '
                                                  'subscription-manager'
                                                  ' has a facts file')}

    # This method parses the output depending on which
    # command string was requested to be run.

    def parse_data(self):
        if 'subman_facts_list' in self.cmd_results.keys():
            if self.cmd_results['subman_facts_list'][0] \
                    and not self.cmd_results['subman_facts_list'][1]:
                result = self.cmd_results['subman_facts_list'][0].strip()
                result = [line.split(': ') for line in result.splitlines()]
                subman_facts = [("subman.%s" % field, value)
                                for field, value in result
                                if "subman.%s" % field
                                in self.fields.keys()]
                self.data.update(subman_facts)

        # Checks for the existence of at least
        # one .facts file in /etc/rhsm/facts
        if 'subman_has_facts' in self.cmd_results.keys():
            if self.cmd_results['subman_has_facts'][0] \
                    and not self.cmd_results['subman_has_facts'][1]:
                fact_files_list = \
                    self.cmd_results['subman_has_facts'][0].strip().split('\n')
                self.data['subman.has_facts_file'] = "Y" \
                    if len(fact_files_list) > 0 else "N"


class RedhatPackagesRhoCmd(RhoCmd):
    # This class wraps around the cli commands
    # that are used to obtain information about
    # Redhat packages installed on the box. Currently
    # there are 5 fields associated with this class.
    # There is only one command string that has to be
    # run for all the 5 fields.

    def __init__(self):
        super(RedhatPackagesRhoCmd, self).__init__()

        self.name = "packages"

        self.cmd_strings['get_package_info'] = 'rpm -qa --qf ' \
                                               '"%{NAME}|%{VERSION}' \
                                               '|%{RELEASE}'' \
                                               ''|%{INSTALLTIME}' \
                                               '|%{VENDOR}' \
                                               '|%{BUILDTIME}' \
                                               '|%{BUILDHOST}'' \
                                               ''|%{SOURCERPM}' \
                                               '|%{LICENSE}' \
                                               '|%{PACKAGER}'' \
                                               ''|%{INSTALLTIME:date}' \
                                               '|%{BUILDTIME:date}\n"'

        self.cmd_names['get_package_info'] = ['redhat-packages.is_redhat',
                                              'redhat-'
                                              'packages.num_rh_packages',
                                              'redhat-'
                                              'packages.num_'
                                              'installed_packages',
                                              'redhat-'
                                              'packages.last_installed',
                                              'redhat-'
                                              'packages.last_built']

    class PkgInfo(object):
        # This is an inner class for RedhatPackagesRhoCmd
        # class and provides functionality to parse the
        # results of running the (only) command string
        # named 'get_package_info'. This is purely to
        # make the parsing cleaner and understandable.

        def __init__(self, outer, row, separator):
            self.outer = outer
            cols = row.split(separator)
            if len(cols) < 10:
                raise outer.PkgInfoParseException()
            else:
                self.name = cols[0]
                self.version = cols[1]
                self.release = cols[2]
                self.install_time = long(cols[3])
                self.vendor = cols[4]
                self.build_time = long(cols[5])
                self.build_host = cols[6]
                self.source_rpm = cols[7]
                self.license = cols[8]
                self.packager = cols[9]
                self.install_date = cols[10]
                self.build_date = cols[11]
                self.is_red_hat = False
                if ('redhat.com' in self.build_host and
                        'fedora' not in self.build_host and
                        'rhndev' not in self.build_host):
                    self.is_red_hat = True

                # Helper methods to help with recording data in
                # requested fields.

        def is_red_hat_pkg(self):
            return self.is_red_hat

        def details_built(self):
            return "%s Built: %s" % (self.details(), self.build_date)

        def details_install(self):
            return "%s Installed: %s" % (self.details(), self.install_date)

        def details(self):
            return "%s-%s-%s" % (self.name, self.version, self.release)

    class PkgInfoParseException(BaseException):
        pass

    # Main method to parse data and to handle errors if
    # the command string returns invalid results.

    def parse_data(self):
        if self.cmd_results['get_package_info'][1]:
            self.data['redhat-packages.is_redhat'] = "error"
            self.data['redhat-packages.num_rh_packages'] = "error"
            self.data['redhat-packages.num_installed_packages'] = "error"
            self.data['redhat-packages.last_installed'] = "error"
            self.data['redhat-packages.last_built'] = "error"
            return
        installed_packages = [self.PkgInfo(self, line, "|")
                              for line in
                              self.cmd_results['get_package_info'][0]
                                  .splitlines()]
        rh_packages = filter(self.PkgInfo.is_red_hat_pkg,
                             installed_packages)
        if len(rh_packages) > 0:
            last_installed = 0
            last_built = 0
            max_install_time = float("-inf")
            max_build_time = float("-inf")
            for x in rh_packages:
                if x.install_time > max_install_time:
                    max_install_time = x.install_time
                    last_installed = x
                if x.build_time > max_build_time:
                    max_build_time = x.build_time
                    last_built = x

            is_red_hat = "Y" if len(rh_packages) > 0 else "N"

            self.data['redhat-packages.is_redhat'] = is_red_hat
            self.data['redhat-packages.num_rh_packages'] = len(rh_packages)
            self.data['redhat-packages.num_installed_packages'] \
                = len(installed_packages)
            self.data['redhat-packages.last_installed'] \
                = last_installed.details_install()
            self.data['redhat-packages.last_built'] \
                = last_built.details_built()
        else:
            last_installed = ""
            last_built = ""
            is_red_hat = ""

            self.data['redhat-packages.is_redhat'] = is_red_hat
            self.data['redhat-packages.num_rh_packages'] = len(rh_packages)
            self.data['redhat-packages.num_installed_packages'] \
                = len(installed_packages)
            self.data['redhat-packages.last_installed'] = last_installed
            self.data['redhat-packages.last_built'] = last_built


class RedhatReleaseRhoCmd(RhoCmd):
    # This class wraps around a single command string
    # whose result is parsed to populate 4 possible
    # fields, redhat-release.name, version and release.

    def __init__(self):
        super(RedhatReleaseRhoCmd, self).__init__()
        self.name = "redhat-release"
        self.cmd_strings["get_release_info"] = """rpm -q --queryformat
                                                  "%{NAME}\n
                                                  %{VERSION}\n
                                                  %{RELEASE}\n"
                                                  --whatprovides
                                                   redhat-release"""
        self.cmd_names["get_release_info"] = ["redhat-release.name",
                                              "redhat-release.version",
                                              "redhat-release.release"]
        self.fields = {'redhat-release.name': _("name of"
                                                " package that "
                                                "provides 'red"
                                                "hat-release'"),
                       'redhat-release.version': _("version of "
                                                   "package that "
                                                   "provides 'red"
                                                   "hat-release'"),
                       'redhat-release.release': _("release of"
                                                   " package that "
                                                   "provides 'red"
                                                   "hat-release'")}

    # This method handles errors for invalid result
    # and does simple parsing to obtain the three
    # fields' info.

    def parse_data(self):
        # new line seperated string, one result only
        if self.cmd_results["get_release_info"][1]:
            # and/or, something not dumb
            self.data = {'redhat-release.name': 'error',
                         'redhat-release.version': 'error',
                         'redhat-release.release': 'error'}
            return
        fields = self.cmd_results["get_release_info"][0].splitlines()
        # no shell gives a single bogus line of output, we expect 3
        if len(fields) >= 3:
            self.data['redhat-release.name'] = fields[0].strip()
            self.data['redhat-release.version'] = fields[1].strip()
            self.data['redhat-release.release'] = fields[2].strip()


class EtcReleaseRhoCmd(RhoCmd):
    # This class wraps around the command strings that
    # get release information for boxes that contain
    # non-Redhat packages installed in them. This wraps
    # around a single command (which is an sh script)
    # that 'echo's the name, version and release info
    # (along with a boolean value)and this information
    # is captured in the corresponding fields.

    def __init__(self):
        super(EtcReleaseRhoCmd, self).__init__()

        self.name = "release"

        self.cmd_names["get_release_info"] = ["etc_release.name",
                                              "etc_release.version",
                                              "etc_release.release"]

        cmd_string = """if [ -f /etc/lsb-release ]; then
         . /etc/lsb-release
         os=$DISTRIB_ID
         ver=$DISTRIB_RELEASE
        elif [ -f /etc/debian_version ]; then
            os=Debian  # XXX or Ubuntu??
            ver=$( cat /etc/debian_version )
        elif [ -f /etc/redhat-release ]; then
            rel=$( cat /etc/redhat-release )
            boolean=1
        elif [ -f /etc/release ]; then
            rel=$( cat /etc/release )
            boolean=1
        elif [ -f /etc/SuSE-release ]; then
            rel=$( cat /etc/SuSE-release )
            boolean=1
        elif [ -f /etc/mandriva-release ]; then
            rel=$( cat /etc/mandriva-release )
            boolean=1
        elif [ -f /etc/enterprise-release ]; then
            rel=$( cat /etc/enterprise-release )
            boolean=1
        elif [ -f /etc/sun-release ]; then
            rel=$( cat /etc/sun-release )
            boolean=1
        elif [ -f /etc/slackware-release ]; then
            rel=$( cat /etc/slackware-release )
            boolean=1
        elif [ -f /etc/ovs-release ]; then
            rel=$( cat /etc/ovs-release )
            boolean=1
        elif [ -f /etc/arch-release ]; then
            rel=$( cat /etc/arch-release )
            boolean=1
        else
            os=$(uname -s)
            ver=$(uname -r)
        fi
        echo $boolean
        echo $os
        echo $ver
        echo $rel"""
        self.cmd_strings["get_release_info"] = cmd_string

    # The run_cmd method is overwritten for this
    # class because of the additional requirement
    # to parse the results according to the boolean
    # value returned. A boolean value 1 means that
    # the box contains redhat_release, SuSE-release
    # mandriva-release, enterprise-release,
    # sun-release, slackware-release, ovs-release, or
    # arch-release and not 1 implies lsb-release,
    # debian or for none of the above.

    def run_cmd(self, facts):
        try:
            process_set = sp.Popen(self.cmd_strings["get_release_info"],
                                   shell=True, stdout=sp.PIPE,
                                   stderr=sp.PIPE)
            res = process_set.communicate()[0].split()
            boolean = res[0].strip()
            if boolean == 1:
                rel = res[3].strip()
                rel_list = rel.split('release')
                rel_name = rel_list[0].strip()
                rel_version = rel_list[1].strip()
                self.data['etc_release.name'] = rel_name
                self.data['etc_release.version'] = rel_version
                self.data['etc_release.release'] = rel.strip()
            else:
                os_name = res[1].strip()
                ver = res[2].strip()
                release = os_name + " " + ver
                self.data['etc_release.name'] = os_name
                self.data['etc_release.version'] = ver
                self.data['etc_release.release'] = release
        except OSError as e:
            print "OSError > ", e.errno
            print "OSError > ", e.strerror
            print "OSError > ", e.filename

        # Functionality for this method included in
        # run_cmd.

    def parse_data(self):
        pass


class CpuRhoCmd(RhoCmd):
    # This class wraps around just one
    # command string when run gives a
    # result this is parsed to fill
    # 8 fields.

    def __init__(self):
        super(CpuRhoCmd, self).__init__()

        self.name = "cpu"

        self.cmd_names["get_cpu_info"] = ["cpu.count",
                                          "cpu.socket_count",
                                          "cpu.vendor_id",
                                          "cpu.bogomips",
                                          "cpu.cpu_family",
                                          "cpu.model_name",
                                          "cpu.model_ver"]

        self.cmd_strings["get_cpu_info"] = "cat /proc/cpuinfo"

        self.fields = {'cpu.count': _('number of processors'),
                       'cpu.socket_count': _('number of sockets'),
                       'cpu.vendor_id': _("cpu vendor name"),
                       'cpu.bogomips': _("bogomips"),
                       'cpu.cpu_family': _("cpu family"),
                       'cpu.model_name': _("name of cpu model"),
                       'cpu.model_ver': _("cpu model version")}

    def parse_data(self):
        self.data = self.parse_data_cpu(self.cmd_results)

    # Helper method to parse results related
    # to CpuRhoCmd and it's sub-classes. It runs
    # a subprocess to run the command to obtain
    # dmidecode information which is required
    # for populating the cpu_socket count field.
    # Creates a dictionary cpu_dict to store
    # specific information which is later recorded
    # into the data dictionary for the csv.

    def parse_data_cpu(self, results):
        data = {}
        cpu_count = 0
        process = sp.Popen("dmidecode -t 4",
                           shell=True,
                           stdout=sp.PIPE,
                           stderr=sp.PIPE)
        dmidecode = process.communicate()
        for line in results["get_cpu_info"][0].splitlines():
            if line.find("processor") == 0:
                cpu_count += 1
        data["cpu.count"] = cpu_count
        data['cpu.socket_count'] = dmidecode[1] if dmidecode[1] else \
            len(re.findall('Socket Designation', dmidecode[0]))

        cpu_dict = {}
        for line in results["get_cpu_info"][0].splitlines():
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
        # but it's a lot of ugly code (see read_cpuinfo() in smolt.py
        # from smolt[I know it's ugly, I wrote it...]) That code also
        # needs the value of uname() available to it, which we don't
        #  currently have a way of plumbing in. So
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

    # Helper method to finally record the
    # data from cpu_dict to the fields
    # for the csv.

    def get_x86_cpu_info(self, data, cpu_dict):
        data["cpu.vendor_id"] = cpu_dict.get("vendor_id")
        # model name should help find kvm/qemu guests...
        data["cpu.model_name"] = cpu_dict.get("model name")
        # they would take my linux card away if I didn't include bogomips
        data["cpu.bogomips"] = cpu_dict.get("bogomips")
        data["cpu.cpu_family"] = cpu_dict.get("cpu family")
        data["cpu.model_ver"] = cpu_dict.get("model")


class _GetFileRhoCmd(RhoCmd):
    # This is a private superclass that does not
    # directly wrap around particular command
    # string(s) but is used as a stencil for
    # classes that wrap around command strings
    # related to getting information by reading
    # files on the box.

    def __init__(self):
        super(_GetFileRhoCmd, self).__init__()

        self.name = "file"

        self.filename = None

        self.cmd_string_template = "if [ -f %s ] ; then cat %s ; fi"

        self.cmd_names["get_file"] = ["%s.contents" % self.name]

    # Method that contains the functionality to
    # parse results and populate the file name
    # field depending on what file it's trying
    # to access.

    def parse_data(self):
        self.data["%s.contents" % self.name] = "".join(
            self.cmd_results[self.cmd_names.keys()[0]][0])


class EtcIssueRhoCmd(_GetFileRhoCmd):
    # This class wraps around the command string
    # to obtain information from the file '/etc/issue'.

    def __init__(self):
        super(EtcIssueRhoCmd, self).__init__()

        self.name = "etc-issue"

        self.filename = "/etc/issue"

        cmd_string = self.cmd_string_template % (self.filename, self.filename)
        self.cmd_strings['get_file'] = cmd_string

        self.cmd_names["get_file"].append('etc-issue.etc-issue')

        self.fields = {'etc-issue.etc-issue': _('contents of /etc/issue')}

    # This method parses ad fills the information
    # for the field 'etc-issue'.

    def parse_data(self):
        super(EtcIssueRhoCmd, self).parse_data()
        self.data["etc-issue.etc-issue"] = string.strip(
            self.cmd_results[self.cmd_names.keys()[0]][0])


class InstnumRhoCmd(_GetFileRhoCmd):
    # This class wraps around the command string
    # to obtain info from the file '/etc/sysconfig/rhn/install-num'

    def __init__(self):
        super(InstnumRhoCmd, self).__init__()

        self.name = "instnum"

        self.filename = "/etc/sysconfig/rhn/install-num"

        cmd_string = self.cmd_string_template % (self.filename, self.filename)
        self.cmd_strings['get_file'] = cmd_string

        self.cmd_names["get_file"].append('instnum.instnum')

        self.fields = {'instnum.instnum': _('installation number')}

    def parse_data(self):
        super(InstnumRhoCmd, self).parse_data()
        self.data["instnum.instnum"] = string.strip(
            self.cmd_results[self.cmd_names.keys()[0]][0])


class SystemIdRhoCmd(_GetFileRhoCmd):
    # This class wraps around the command string to
    # obtain infro from the file '/etc/sysconfig/rhn/systemid'.

    def __init__(self):
        super(SystemIdRhoCmd, self).__init__()
        self.name = "systemid"
        self.filename = "/etc/sysconfig/rhn/systemid"
        cmd_string = self.cmd_string_template % (self.filename, self.filename)
        self.cmd_strings['get_file'] = cmd_string
        # FIXME: there are more fields here, # not sure it's worth including
        # FIXME: them as options
        self.cmd_names["get_file"].append('systemid.system_id')
        self.cmd_names["get_file"].append('systemid.username')
        self.fields = {'systemid.system_id': _('Red Hat Network system id'),
                       'systemid.username': _('Red Hat Network username')}

    # This method parses results and fills in
    # information for the fields system_id and
    # username.

    def parse_data(self):
        super(SystemIdRhoCmd, self).parse_data()
        # if file is empty, or we get errors, skip...
        if not self.cmd_results[self.cmd_names.keys()[0]][0] \
                or self.cmd_results[self.cmd_names.keys()[0]][1]:
            # no file, nothing to parse
            return
        blob = "".join(self.cmd_results[self.cmd_names.keys()[0]])
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
    # This class wraps around all bios related
    # command strings and currently maps the,
    # one on one to 4 fields.

    # note this test doesn't work well, or at all, for non root
    # users by default.

    def __init__(self):
        super(DmiRhoCmd, self).__init__()
        self.name = "dmi"

        self.fields = {'dmi.bios-vendor': _('BIOS vendor info from DMI'),
                       'dmi.bios-version': _('BIOS version info from DMI'),
                       'dmi.system-manufacturer': _(
                           'System manufacturer from DMI'),
                       'dmi.processor-family': _('Processor family from DMI')}

        self.cmd_names["bios_vendor"] = ['dmi.bios-vendor']
        self.cmd_names["bios_version"] = ['dmi.bios-version']
        self.cmd_names["bios_sys_manu"] = ['dmi.system-manufacturer']
        self.cmd_names["bios_processor_fam"] = ['dmi.processor-family']

        self.cmd_strings["bios_vendor"] = "dmidecode -s bios-vendor"
        self.cmd_strings["bios_version"] = "dmidecode -s bios-version"
        self.cmd_strings["bios_sys_manu"] = "dmidecode -s system-manufacturer"
        self.cmd_strings["bios_processor_fam"] = "dmidecode -s " \
                                                 "processor-family"

    # This method loops through all
    # requested bios fields and parses
    # the results and fills the data dictionary
    # as required.

    def parse_data(self):
        for k in self.cmd_names.keys():
            if k in self.cmd_results.keys():
                if self.cmd_results[k][0] and not self.cmd_results[k][1]:
                    self.data[self.cmd_names[k]] = string.strip(
                        self.cmd_results[k][0])


class VirtWhatRhoCmd(RhoCmd):
    # This class wraps around the command string
    # that is run to obtain information about
    # virt-what i.e. virt-what.type.

    def __init__(self):
        super(VirtWhatRhoCmd, self).__init__()

        self.name = "virt-what"

        self.fields = {'virt-what.type': _(
            "What type of virtualization"
            " a system is running,"""
            " as determined by virt-what")}

        self.cmd_names["virt_what"] = ['virt-what.type']

        cmd_string = "virt-what;echo $?"
        self.cmd_strings["virt_what"] = cmd_string

    # This method handles errors due to invalid results
    # and populates the virt-what.type field accordingly.

    def parse_data(self):
        if self.cmd_results[self.cmd_names.keys()[0]][0] \
                and not self.cmd_results[self.cmd_names.keys()[0]][1]:
            results = [line for line in self.cmd_results[
                self.cmd_names.keys()[0]][0].strip().split('\n')]
            error = int(results[-1:][0])
            virt_what_output = results[:len(results) - 1]
            if error == 0:
                if len(virt_what_output) > 0:
                    # quote the results and join on
                    # ',' as virt-what can return multiple values
                    self.data['virt-what.type'] = '"%s"' % "," \
                        .join(virt_what_output)
                else:
                    self.data['virt-what.type'] = "bare metal"


class VirtRhoCmd(CpuRhoCmd):
    # This class wraps around the command strings
    # to get information for fields like sys_manu,
    # xen_guest etc (currently 6 in total).

    # try to determine if we are a virt guest, a host, or bare metal

    def __init__(self):
        super(VirtRhoCmd, self).__init__()
        self.name = 'VirtRhoCmd'

        self.fields = {'virt.virt': _("If a host is a virt guest,"
                                      " host, or bare metal"),
                       'virt.type': _("What type of virtualization"
                                      " a system is running"),
                       'virt.num_guests': _("The number of "
                                            "virtualized guests"),
                       'virt.num_running_guests': _("The number"
                                                    " of running"
                                                    "virtualized "
                                                    "guests")}

        cmd_template = "if [ -e %s ] ;" \
                       " then echo \"true\"; else echo \"false\"; fi"

        self.cmd_names["sys_manu"] = ["virt.virt", "virt.type"]
        self.cmd_names["xen_guest"] = ["virt.virt", "virt.type"]
        self.cmd_names["privcmd"] = ["virt.virt", "virt.type"]
        self.cmd_names["kvm"] = ["virt.virt", "virt.type"]
        self.cmd_names["virt_all_list"] = ["virt.num_guests"]
        self.cmd_names["virt_running_list"] = ["virt.num_running_guests"]

        self.cmd_strings["sys_manu"] = "dmidecode -s system-manufacturer"
        self.cmd_strings["xen_guest"] = "ps aux | grep xend | grep -v grep"
        self.cmd_strings["privcmd"] = cmd_template % "/proc/xen/privcmd"
        self.cmd_strings["kvm"] = cmd_template % "/dev/kvm"
        self.cmd_strings["virt_all_list"] = "virsh -c qemu" \
                                            ":///system --readonly" \
                                            " list --all"
        self.cmd_strings["virt_running_list"] = "virsh -c qemu:///" \
                                                "system --readonly " \
                                                "list --uuid"

    # Method to parse results of command strings
    # for all required fields.

    def parse_data(self):
        self.data["virt.virt"] = ""
        self.data["virt.type"] = ""

        # calculate number of guests
        self._num_guests()

        # calculate number of running guests
        self._num_running_guests()

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
    # and if so, what kind. Mainly looking for xen/kvm here, but if anything
    # else is easy to detect, try that too.

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
        if "kvm" in self.cmd_results.keys():
            dev_kvm = None
            if self.cmd_results["kvm"][0] and not self.cmd_results["kvm"][1]:
                dev_kvm = string.strip(self.cmd_results["kvm"][0])
            if dev_kvm == "true":
                self.data["virt.type"] = "kvm"
                self.data["virt.virt"] = "virt-host"

    # look at the results of dmidecode for hints about what type of
    # virt we have. could probably also track vmware esx version with
    # bios version. None of this works as non root, so it's going to
    # fail most of the time.

    def _check_dmidecode(self):
        if "sys_manu" in self.cmd_results.keys():
            manuf = None
            if self.cmd_results["sys_manu"][0] \
                    and not self.cmd_results["sys_manu"][1]:
                manuf = string.strip(self.cmd_results["sys_manu"][0])
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
        #
        if "xen_guest" in self.cmd_results.keys():
            if self.cmd_results["xen_guest"][0] \
                    and not self.cmd_results["xen_guest"][1]:
                # is xend running? must be a xen host
                # ugly...
                self.data["virt.type"] = "xen"
                self.data["virt.virt"] = "virt-host"

    def _check_for_xen(self):
        # look for /proc/xen/privcmd
        # Note: xen show "qemu" as cputype as well, so we do this
        # after looking at cpuinfo
        if "privcmd" in self.cmd_results.keys():
            if self.cmd_results["privcmd"][0] \
                    and not self.cmd_results["privcmd"][1]:
                if string.strip(self.cmd_results["privcmd"][0]) == "true":
                    self.data["virt.type"] = "xen"
                    self.data["virt.virt"] = "virt-guest"

    def _num_guests(self):
        if "virt_all_list" in self.cmd_results.keys():
            if self.cmd_results["virt_all_list"][0] \
                    and not self.cmd_results["virt_all_list"][1]:
                # we want to remove the title and
                # seperator lines of virsh output
                output = self.cmd_results["virt_all_list"][0].strip().split(
                    '\n')[2:]
                self.data["virt.num_guests"] = len(output)
            else:
                self.data["virt.num_guests"] = 0

    def _num_running_guests(self):
        if "virt_running_list" in self.cmd_results.keys():
            if self.cmd_results["virt_running_list"][0] \
                    and not self.cmd_results["virt_running_list"][1]:
                self.data['virt.num_running_guests'] = \
                    len(self.cmd_results["virt_running_list"][0].strip())
            else:
                self.data['virt.num_running_guests'] = 0


# List of default commands
DEFAULT_CMDS = [UnameRhoCmd,
                RedhatReleaseRhoCmd,
                InstnumRhoCmd,
                SystemIdRhoCmd,
                CpuRhoCmd,
                EtcReleaseRhoCmd,
                EtcIssueRhoCmd,
                DmiRhoCmd,
                VirtRhoCmd,
                RedhatPackagesRhoCmd,
                VirtWhatRhoCmd,
                DateRhoCmd,
                SubmanFactsRhoCmd
                ]

# Dictionary mapping class keywords
# passed in through the playbook (attached
# to the field requested using an '_').

DEFAULT_CMD_DICT = {"Username": UnameRhoCmd,
                    "RedhatRelease": RedhatReleaseRhoCmd,
                    "Instnum": InstnumRhoCmd,
                    "SysId": SystemIdRhoCmd,
                    "Cpu": CpuRhoCmd,
                    "EtcRelease": EtcReleaseRhoCmd,
                    "EtcIssue": EtcIssueRhoCmd,
                    "Dmi": DmiRhoCmd,
                    "Virt": VirtRhoCmd,
                    "RedhatPackages": RedhatPackagesRhoCmd,
                    "VirtWhat": VirtWhatRhoCmd,
                    "Date": DateRhoCmd,
                    "SubmanFacts": SubmanFactsRhoCmd}


class RunCommands(object):
    # Class that contains the functionality to
    # parse the inputs from the playbook and stores
    # the requested facts in an instance variable
    # called 'facts_requested'.

    def __init__(self, module):
        self.name = module.params["name"]
        self.facts_requested = {}

        # exception used to see if the input from playbook
        # is a list of facts or just a string so that
        # it can be converted to python data structures
        # as suited.

        try:
            self.fact_names = ast.literal_eval(module.params["fact_names"])
        except:
            self.fact_names = module.params["fact_names"]

        # Split each requested fact on the first '_' so as to obtain
        # the RhoCmd sub-class that's being requested and store the
        # string to the right of '_' as one of the facts requested
        # for that respective rho command class (so the class knows)
        # which command strings to run by using the two dictionaries,
        # cmd_strings and cmd_names. Of course, this is only valid
        # when the input is in the form of a list of fact_names.

        if type(self.fact_names) == list:
            for f_name in self.fact_names:
                f_name_list = f_name.strip().split('_', 1)
                rho_cmd = DEFAULT_CMD_DICT[f_name_list[0]]
                fact = f_name_list[1]
                if rho_cmd in DEFAULT_CMDS:
                    if rho_cmd in self.facts_requested.keys():
                        self.facts_requested[rho_cmd].append(fact)
                    else:
                        self.facts_requested[rho_cmd] = [fact]

                    # If type of input is a string then the only allowed,
                    # string is 'default' which means the user has requested
                    # all RhoCmds subclasses and all of their cmd strings will
                    # be run to fill in all corresponding fields.

        elif type(self.fact_names) == str:
            if self.fact_names.lower().strip() == "default":
                for def_cmd in DEFAULT_CMDS:
                    self.facts_requested[def_cmd] = "all"
            else:
                print "FACT NOT AVAILABLE. EXITING"
                return
        else:
            print "INVALID FACT TYPE. EXITING"
            return

        # Method that creates instances of all RhoCmd subclasses
        # requested in the playbook and runs the command strings
        # desired to get the corresponding fields information.

    def execute_commands(self):
        # Goes through all the default commands
        # and executes them on the box's shell
        info_dict = {}
        for rho_cmd in self.facts_requested.keys():
            rcmd = rho_cmd()
            rcmd.run_cmd(self.facts_requested[rho_cmd])
            info_dict.update(rcmd.data)

        if 'all' not in self.facts_requested.values():

            # list that stores out the flattened out
            # values list of the facts_requested dictionary
            # to keep track of all fields requested so
            # that only those can be reported.

            facts_requested_list = [item
                                    for sublist
                                    in self.facts_requested.values()
                                    for item in sublist]

            if 'all' not in facts_requested_list:
                for k in info_dict.keys():
                    if k not in facts_requested_list:
                        info_dict.pop(k, None)

        return info_dict


# Creates an instance of an AnsibleModule that grabs information
# from the playbook about the facts that need to be collected.

def main():
    module = AnsibleModule(argument_spec=dict(name=dict(required=True),
                                              fact_names=dict(required=False)))
    my_runner = RunCommands(module=module)
    if my_runner == 1:
        response = "failed"
        module.exit_json(changed=False, meta=response)
    info_dict = my_runner.execute_commands()
    response = json.dumps(info_dict)
    module.exit_json(changed=False, meta=response)


if __name__ == '__main__':
    main()
