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

""" Rho CLI Commands """

import csv
import os
import string
import sys


import gettext
t = gettext.translation('rho', 'locale', fallback=True)
_ = t.ugettext

from optparse import OptionParser
from getpass import getpass
import simplejson as json
import paramiko

from rho.log import log, setup_logging

from rho import config
from rho import crypto
from rho import rho_ips
from rho import scanner
from rho import scan_report


RHO_PASSWORD = "RHO_PASSWORD"
RHO_AUTH_PASSWORD = "RHO_AUTH_PASSWORD"
DEFAULT_RHO_CONF = "~/.rho.conf"


def _read_key_file(filename):
    keyfile = open(os.path.expanduser(
        os.path.expandvars(filename)), "r")
    sshkey = keyfile.read()
    keyfile.close()
    return sshkey

# figure out if a key is encrypted
# basically, just try to read the key sans password
# and see if it works... Pass in a passphrase to
# see if it is the correct passphrase


def ssh_key_passphrase_is_good(filename, password=None):
    good_key = True
    try:
        get_key_from_file(filename, password=password)
    except paramiko.PasswordRequiredException:
        good_key = False
    except paramiko.SSHException:
        good_key = False
    return good_key


def get_key_from_file(filename, password=None):
    pkey = None
    keyfile = open(os.path.expanduser(
        os.path.expandvars(filename)), "r")
    if keyfile.readline().find("-----BEGIN DSA PRIVATE KEY-----") > -1:
        keyfile.seek(0)
        pkey = paramiko.DSSKey.from_private_key_file(filename, password=password)
    keyfile.seek(0)
    if keyfile.readline().find("-----BEGIN RSA PRIVATE KEY-----") > -1:
        keyfile.seek(0)
        pkey = paramiko.RSAKey.from_private_key_file(filename, password=password)
    return pkey


def get_passphrase(for_key):
    passphrase = ""
    passphrase = getpass(_("Passphrase for '%s':" % for_key))
    return passphrase


def get_password(for_username, env_var_to_check):
    password = ""
    if env_var_to_check in os.environ:
        log.info("Using password from %s environment variable." %
                 env_var_to_check)
        password = os.environ[env_var_to_check]
    else:
        password = getpass(_("Password for '%s':" % for_username))
    return password


def _read_hosts_file(filename):
    result = None
    try:
        hosts = file(os.path.expanduser(os.path.expandvars(filename)))
        result = hosts.readlines()
        hosts.close()
    except EnvironmentError, e:
        sys.stderr.write('Error reading from %s: %s\n' % (filename, e))
        hosts.close()
    return result


class OutputPrinter(object):

    def __init__(self, keys, delimeter="\t", pad=2, dontpad=[]):
        self.keys = keys
        # seed the rows with the header
        self.writer = csv.writer(sys.stdout, delimiter=delimeter)

        sepline = []
        for k in keys:
            sepline.append("-" * (len(k) + pad))

        self.rows = [keys, sepline]
        self.pad = pad
        self.dontpad = dontpad

    def add_row(self, row):
        line = []
        for k in self.keys:
            if k in row:
                if isinstance(row[k], list):
                    line.append(", ".join(["%s" % i for i in row[k]]))
                else:
                    line.append(str(row[k]))
            else:
                line.append("")

        self.rows.append(line)

    def write(self):
        # find the max length of each column
        # store them in order in collens.
        collens = []

        i = 0
        for key in self.keys:
            length = len(key) + self.pad
            if key not in self.dontpad:
                length = max(len(r[i]) for r in self.rows) + self.pad

            collens.append(length)
            i += 1

        for i in range(0, len(self.keys)):
            length = max(len(r[i]) for r in self.rows) + self.pad
            collens.append(length)

        # for each row pad the column to the value in
        # collens[i]

        for row in self.rows:
            line = []
            lenidx = 0
            for col in row:
                line.append(col.ljust(collens[lenidx]))
                lenidx += 1

            self.writer.writerow(line)


class ProfilePrinter(object):

    def __init__(self, profiles):
        self.profiles = profiles

    def write(self):
        for p in self.profiles:
            print("\nname: %s" % p.name)

            print("    auths:")
            for auth in p.auth_names:
                print("        %s" % auth)

            print("    ports:")
            for port in p.ports:
                print("        %s" % port)

            print("    ranges:")
            for ip_range in p.ranges:
                print("        %s" % ip_range)


class ReportPrinter(object):

    def __init__(self, reports):
        self.reports = reports

    def write(self):
        for r in self.reports:
            print("\nname: %s" % r.name)

            print("    output_filename:\n        %s" % r.output_filename)
            print("    fields:")
            for field in r.report_format:
                print("        %s" % field)


class CliCommand(object):

    """ Base class for all sub-commands. """
    def __init__(self, name="cli", usage=None, shortdesc=None,
                 description=None):

        self.shortdesc = shortdesc
        if shortdesc is not None and description is None:
            description = shortdesc
        self.parser = OptionParser(usage=usage, description=description)
        self._add_common_options()
        self.name = name
        self.passphrase = None

    def _add_common_options(self):
        """ Add options that apply to all sub-commands. """

        # Default is expanded later:
        self.parser.add_option("--config", dest="config",
                               help=_("config file name"), default=DEFAULT_RHO_CONF)

        self.parser.add_option("--log", dest="log_file", metavar="FILENAME",
                               help=_("log file name (will be overwritten)"))
        self.parser.add_option("--log-level", dest="log_level",
                               default="critical", metavar="LEVEL",
                               help=_("log level (debug/info/warning/error/critical)"))

    def _validate_port(self, port):
        try:
            int(port)
        except ValueError:
            # aka, we get a string here...
            return False
        if int(port) < 1 or int(port) > 65535:
            return False
        return True

    def _validate_ports(self, ports):
        # magic numbers, but these are valid tcp port ranges
        for port in ports:
            if not self._validate_port(port):
                print _("%s includes an invalid port number. "
                        "Ports should be between 1 and 65535") % string.join(ports, ",")
                sys.exit(1)

    # see if the ip address we are given are at least sort of valid...
    def _validate_ranges(self, ipranges):
        for iprange in ipranges:
            ipr = rho_ips.RhoIpRange(iprange)
            if not ipr.valid:
                print _("""ip range "%s" is invalid""" % string.join(ipranges, ','))
                sys.exit(1)

    def _validate_options(self):
        """
        Sub-commands can override to do any argument validation they
        require.
        """
        pass

    def _do_command(self):
        pass

    def _read_config(self, filename, password):
        """
        Read config file and decrypt with the given password.

        Note that password here is the password provided by the user, not the
        actual salted AES key.
        """
        if os.path.exists(filename):
            try:
                confstr = crypto.read_file(filename, password)
            except crypto.DecryptionException:
                print self.parser.error(_("Error decrypting configuration file"))

            try:
                return config.ConfigBuilder().build_config(confstr)
            except config.BadJsonException:
                print self.parser.error(_("Cannot parse configuration, check encryption password"))

        else:
            new_config = config.Config()
            print (_("Creating new config file: %s") % self.options.config)
            self._write_config(new_config)
            return new_config

    def _write_config(self, new_config):
        c = config.ConfigBuilder().dump_config(new_config)
        crypto.write_file(self.options.config, c, self.passphrase)

    def main(self):

        (self.options, self.args) = self.parser.parse_args()
        # we dont need argv[0] in this list...
        self.args = self.args[1:]

        # Setup logging, this must happen early!
        setup_logging(self.options.log_file, self.options.log_level)
        log.debug("Running cli command: %s" % self.name)

        # Translate path to config file to something absolute and expanded:
        self.options.config = os.path.abspath(os.path.expanduser(
            self.options.config))
        log.debug("Absolute config file: %s" % self.options.config)

        self._validate_options()

        if len(sys.argv) < 2:
            print(self.parser.error(_("Please enter at least 2 args")))
        if RHO_PASSWORD in os.environ:
            log.info("Using passphrase from %s environment variable." %
                     RHO_PASSWORD)
            self.passphrase = os.environ[RHO_PASSWORD]
        else:
            self.passphrase = getpass(_("Config Encryption Password:"))

        self.config = self._read_config(self.options.config, self.passphrase)

        # do the work, catch most common errors here:
        try:
            self._do_command()
        except config.DuplicateNameError as e:
            print _("ERROR: Name already exists: %s") % e.dupe_name
            sys.exit(1)
        except config.NoSuchAuthError as e:
            print _("ERROR: No such auth: %s") % e.authname
            sys.exit(1)


class InitConfigCommand(CliCommand):

    def __init__(self):
        usage = _("usage: %prog initconfig [options]")
        shortdesc = _("initialize rho config")
        desc = _("Adds a few defaults to the config to help getting started using rho\n")

        CliCommand.__init__(self, "initconfig", usage, shortdesc, desc)

    # need to stub out _read_config to avoid accidentally allowing _read_config to create a new empty config
    def _read_config(self, filename, password):
        pass

    def _do_command(self):
        # add any default config stuff here
        auths = []
        profiles = []
        # a default set of reports (including pack-scan)
        reports = [
            config.Report("pack-scan", ['date.date',
                                        'uname.hostname', 'redhat-release.release',
                                        'redhat-packages.is_redhat',
                                        'redhat-packages.num_rh_packages',
                                        'redhat-packages.num_installed_packages',
                                        'redhat-packages.last_installed',
                                        'redhat-packages.last_built',
                                        'date.anaconda_log', 'date.machine_id',
                                        'date.filesystem_create', 'date.yum_history',
                                        'virt-what.type', 'virt.virt',
                                        'virt.num_guests', 'virt.num_running_guests',
                                        'cpu.count', 'cpu.socket_count', 'ip', 'port',
                                        'auth.name', 'auth.type', 'auth.username', 'error',
                                        'dmi.system-manufacturer', 'etc-release.etc-release',
                                        'instnum.instnum', 'redhat-release.version',
                                        'subman.virt.host_type', 'systemid.system_id',
                                        'subman.virt.is_guest', 'uname.hardware_platform']),
        ]
        new_config = config.Config(auths=auths, profiles=profiles, reports=reports)
        print (_("Creating new config with defaults: %s") % self.options.config)
        self._write_config(new_config)


class ScanCommand(CliCommand):

    def __init__(self):
        usage = _("usage: %prog scan [options] PROFILE")
        shortdesc = _("scan given host profile")
        desc = _("scans the host profile")

        CliCommand.__init__(self, "scan", usage, shortdesc, desc)

        self.parser.add_option("--range", dest="ranges", action="append",
                               metavar="RANGE", default=[],
                               help=_("IP range to scan. See 'man rho' for supported formats."))

        self.parser.add_option("--ports", dest="ports", metavar="PORTS",
                               help=_("list of ssh ports to try i.e. '22, 2222, 5402'"))
        self.parser.add_option("--username", dest="username",
                               metavar="USERNAME",
                               help=_("user name for authenticating against target machine"))
        self.parser.add_option("--auth", dest="auth", action="append",
                               metavar="AUTH", default=[],
                               help=_("auth class name to use"))
        self.parser.add_option("--output", dest="reportfile",
                               metavar="REPORTFILE",
                               help=_("write out to this file"),
                               default="")
        self.parser.add_option("--profile", dest="profiles", action="append",
                               metavar="PROFILE", default=[],
                               help=_("profile class to scan")),
        self.parser.add_option("--cache", dest="cachefile",
                               metavar="PASTREPORTFILE",
                               help=_("past output, used to cache successful credentials and ports"))
        self.parser.add_option("--allow-agent", dest="allowagent", action="store_true",
                               metavar="ALLOWAGENT", default=False,
                               help=_("Use keys from local ssh-agent"))
        self.parser.add_option("--show-fields", dest="showfields", action="store_true",
                               metavar="SHOWFIELDS",
                               help=_("show fields available for reports"))
        self.parser.add_option("--hosts", dest="hosts", action="store",
                               metavar="HOSTS",
                               help=_("File of hostnames to scan."),
                               default="")
        self.parser.add_option("--report-format", dest="reportformat",
                               metavar="REPORTFORMAT",
                               help=_("specify report format (see --show-fields for options)"),
                               default="")
        self.parser.add_option("--report", dest="report",
                               metavar="REPORT",
                               help=_("specify the report to run"),
                               action="store",
                               default="")

        self.parser.set_defaults(ports="22")

    def _validate_options(self):
        CliCommand._validate_options(self)

        # We support two ways to specify profiles, with --profile=blah, or
        # without --profile= and just list profiles in the command. Hack here
        # to treat those raw args as --profiles so the subsequent code has just
        # one path.
        self.options.profiles.extend(self.args)

        hasRanges = len(self.options.ranges) > 0
        hasProfiles = len(self.options.profiles) > 0
        hasAuths = len(self.options.auth) > 0
        hasHosts = len(self.options.hosts) > 0
        hasReportFormat = len(self.options.reportformat) > 0
        hasReport = len(self.options.report) > 0
        hasReportFile = len(self.options.reportfile) > 0

        if self.options.cachefile:
            self.options.cachefile = os.path.abspath(os.path.expanduser(
                self.options.cachefile))
            log.debug("Using cached output: %s" % self.options.cachefile)
            if not os.path.exists(self.options.cachefile):
                self.parser.error(_("No such file: %s" % self.options.cachefile))

        if hasRanges:
            self._validate_ranges(self.options.ranges)

        if not hasRanges and not hasProfiles and not self.options.showfields and not hasHosts:
            self.parser.print_help()
            sys.exit(1)

        if hasRanges and hasProfiles:
            self.parser.error(_("Cannot scan ranges and profiles at the same time."))

        if self.options.username and hasAuths:
            self.parser.error(_("Cannot specify both --username and --auth"))

        if hasProfiles and hasAuths:
            self.parser.error(_("Cannot specify both auths and ranges."))

        if hasRanges and not (self.options.username or hasAuths):
            self.parser.error(_(
                "--username or --auth required to scan a range."))
        if hasReport:
            if hasReportFormat:
                self.parser.error(_(
                    "Cannot specify both report-format and report."))
            if hasReportFile:
                self.parser.error(_(
                    "Cannot specify both report and output filename."))

    def _build_cache(self, report_filename):
        """
        Reads in the results of a past report, parses them, and builds a dict
        such as:

        {
            "192.168.1.50": {'port': 22, 'authname': 'myauthname'},
        }
        """
        cache = {}
        f = open(report_filename)
        reader = csv.DictReader(f)
        for row in reader:
            if row['ip'] == '' or row['auth.name'] == '':
                # Looks like we couldn't login to this machine last time.
                continue

            cache[row['ip']] = {'port': int(row['port']), 'auth': row['auth.name']}
            log.debug("Found cached results for: %s" % row['ip'])

        f.close()
        return cache

    def _do_command(self):
        cache = {}
        if self.options.cachefile:
            cache = self._build_cache(self.options.cachefile)

        self.scanner = scanner.Scanner(config=self.config, cache=cache,
                                       allow_agent=self.options.allowagent)

        # If username was specified, we need to prompt for a password
        # to go with it:
        user_password = ""
        if self.options.username:
            user_password = get_password(self.options.username,
                                         RHO_AUTH_PASSWORD)

        # hmm, some possible report values don't come from cmds...
        if self.options.showfields:
            fields = self.scanner.get_cmd_fields()
            fields.update(scan_report.report_fields)
            field_keys = sorted(fields.keys())
            for field_key in field_keys:
                print "%s:%s" % (field_key, fields[field_key])
            sys.exit(0)

        if len(self.options.auth) > 0:
            auths = []
            for auth in self.options.auth:
                a = self.config.get_auth(auth)
                if a:
                    auths.append(a)
        else:
            # FIXME: need a more abstract credentials class -akl
            auth = config.SshAuth({'name': "clioptions",
                                   'username': self.options.username,
                                   'password': user_password,
                                   'type': 'ssh'})
            self.config.add_auth(auth)
            # if we are specifing auth stuff not in the config, add it to
            # the config class as "clioptions" and set the auth name to
            # the same
            self.options.auth = ["clioptions"]

        if self.options.hosts:
            self.options.ranges += _read_hosts_file(self.options.hosts)
        # this is all temporary, but make the tests pass
        if len(self.options.ranges) > 0:
            # create a temporary profile named "clioptions" for anything
            # specified on the command line
            ports = []
            if self.options.ports:
                ports = self.options.ports.strip().split(",")
                self._validate_ports(ports)

            g = config.Profile(name="clioptions", ranges=self.options.ranges,
                               auth_names=self.options.auth, ports=ports)

            self.config.add_profile(g)
            self.scanner.scan_profiles(["clioptions"])

        if len(self.options.profiles) > 0:

            for profile in self.options.profiles:
                if not self.config.has_profile(profile):
                    print(_("ERROR: No such profile: %s") % profile)
                    sys.exit(1)
                if len(self.config.get_profile(profile).auth_names) == 0:
                    print(_("ERROR: Profile %s has no auths to try.") %
                          profile)
                    sys.exit(1)

            missing = self.scanner.scan_profiles(self.options.profiles)
            if missing:
                print _("The following profile names were not found:")
                for name in missing:
                    print name

        fileobj = sys.stdout
        fields = None

        if self.options.report:
            reportobj = self.config.get_report(self.options.report)

            # if report doesn't exist exit gracefully. If it is pack-scan, the
            # default report, the user didn't run initconfig. Instead of
            # exiting we simply add it to the in-memory config before running
            # the scan. While it seems like a good idea to write the report to
            # the config, we modify the config with other temporary runtime
            # options which would pollute the config if written. For now, we
            # are opting to simply add the report in-memory.
            if reportobj is None:
                if self.options.report == 'pack-scan':
                    # automatically add pack-scan to the config
                    reportobj = config.Report(
                       name="pack-scan",
                       report_format=['date.date',
                                      'uname.hostname',
                                      'redhat-release.release',
                                      'redhat-packages.is_redhat',
                                      'redhat-packages.num_rh_packages',
                                      'redhat-packages.num_installed_packages',
                                      'redhat-packages.last_installed',
                                      'redhat-packages.last_built',
                                      'date.anaconda_log', 'date.machine_id',
                                      'date.filesystem_create',
                                      'date.yum_history', 'virt-what.type',
                                      'virt.virt', 'virt.num_guests',
                                      'virt.num_running_guests', 'cpu.count',
                                      'cpu.socket_count', 'ip', 'port',
                                      'auth.name', 'auth.type',
                                      'auth.username', 'error',
                                      'dmi.system-manufacturer',
                                      'etc-release.etc-release',
                                      'instnum.instnum',
                                      'redhat-release.version',
                                      'subman.virt.host_type',
                                      'systemid.system_id',
                                      'subman.virt.is_guest',
                                      'uname.hardware_platform'],
                       output_filename="pack-scan.csv")

                    self.config.add_report(reportobj)
                else:
                    print(_("ERROR: Report %s was not found.") %
                          self.options.report)
                    sys.exit(1)

            fileobj = open(os.path.expanduser(os.path.expandvars(
                reportobj.output_filename)), "w")
            fields = reportobj.report_format

        elif self.options.reportfile:
            fileobj = open(os.path.expanduser(os.path.expandvars(
                self.options.reportfile)), "w")

        if not fields and self.options.reportformat:
            fields = string.split(self.options.reportformat, ',')
        self.scanner.report(fileobj, report_format=fields)
        fileobj.close()


class DumpConfigCommand(CliCommand):

    """
    Dumps the config file to stdout.
    """

    def __init__(self):
        usage = _("usage: %prog dumpconfig [--config]")
        shortdesc = _("dumps the config file to stdout")
        desc = _("dumps the config file to stdout")

        CliCommand.__init__(self, "dumpconfig", usage, shortdesc, desc)

    def _validate_options(self):
        CliCommand._validate_options(self)

        if not os.path.exists(self.options.config):
            print _("No such file: %s" % self.options.config)
            sys.exit(1)

        if (not os.access(self.options.config, os.R_OK)):
            self.parser.print_help()
            sys.exit(1)

    def _do_command(self):
        """
        Executes the command.
        """
        try:
            content = crypto.read_file(self.options.config, self.passphrase)
        except crypto.DecryptionException:
            print self.parser.error(_("Error decrypting configuration file"))
        print(json.dumps(json.loads(content), sort_keys=True, indent=4))


class ImportConfigCommand(CliCommand):

    """
    Import a plaintext config file.
    """

    def __init__(self):
        usage = _("usage: %prog importconfig [--from-file]")
        shortdesc = _("import a plaintext config file")
        desc = _("imports a plaintext config file, encrypts it, and write to the destination config file.")

        CliCommand.__init__(self, "importconfig", usage, shortdesc, desc)

        self.parser.add_option("--from-file", dest="sourcefile",
                               metavar="FROMFILE",
                               help=_("import configuration from raw json file"))

    def _validate_options(self):
        CliCommand._validate_options(self)

        if not self.options.sourcefile:
            self.parser.error(_(
                "--from-file is required"))

        self.options.sourcefile = os.path.abspath(os.path.expanduser(
            self.options.sourcefile))

        # Ensure the source file exists:
        if not os.path.exists(self.options.sourcefile):
            self.parser.error(_("File does not exist") %
                              self.options.sourcefile)

        # Make sure destination config file *doesn't* already exist, don't
        # want to accidentally overwrite config with this command.
        if os.path.exists(self.options.config):
            self.parser.error(_("Destination config file already exists: %s") %
                              self.options.config)

    def _do_command(self):
        """
        Executes the command.
        """
        f = open(self.options.sourcefile, 'r')
        json_buf = f.read()
        imported_config = config.ConfigBuilder().build_config(json_buf)
        c = config.ConfigBuilder().dump_config(imported_config)

        crypto.write_file(self.options.config, c, self.passphrase)


class ReportShowCommand(CliCommand):

    def __init__(self):
        usage = _("usage: %prog report show [options]")
        shortdesc = _("show a rho report")
        desc = _("show a rho report")

        CliCommand.__init__(self, "report show", usage, shortdesc, desc)

        self.parser.add_option("--name", dest="name", metavar="NAME",
                               help=_("report name - REQUIRED"))

    def _validate_options(self):
        CliCommand._validate_options(self)

        if not self.options.name:
            self.parser.print_help()
            sys.exit(1)

    def _do_command(self):
        if not self.config.list_reports():
            print(_("No reports found"))

        r = self.config.get_report(self.options.name)

        if not r:
            print (_("No report '%s' found.") % self.options.name)
            return

        printer = ReportPrinter([r])
        printer.write()


class ReportListCommand(CliCommand):

    def __init__(self):
        usage = _("usage: %prog report list [options]")
        shortdesc = _("list the rho reports")
        desc = _("list the rho reports")

        CliCommand.__init__(self, "report list", usage, shortdesc, desc)

    def _do_command(self):

        if not self.config.list_reports():
            print(_("No reports found"))
            return

        # using OutputPrinter didn't look so
        # nice for profiles
        printer = ReportPrinter(self.config.list_reports())
        printer.write()


class ReportEditCommand(CliCommand):

    def __init__(self):
        usage = _("usage: %prog report edit [options]")
        shortdesc = _("edits a given report")
        desc = _("edit a given report")

        CliCommand.__init__(self, "report edit", usage, shortdesc, desc)

        self.parser.add_option("--name", dest="name", metavar="NAME",
                               help=_("NAME of the report - REQUIRED"))
        self.parser.add_option("--fields", "--report-format", dest="fields",
                               metavar="FIELDS", help=_("Replace fields of the report with FIELDS"),
                               action="store", default=[])
        self.parser.add_option("--remove", "-r", dest="remove", action="store_true", default=False,
                               help=_("Update report by removing field(s) provided by --fields option (REQUIRES --fields)"))
        self.parser.add_option("--add", "--append", "-a", dest="add", action="store_true", default=False,
                               help=_("Update report by appending field(s) provided by --fields option (REQUIRES --fields)"))
        self.parser.add_option("--output", dest="output_filename",
                               metavar="FILENAME", help=_("Change output filename to FILENAME"), action="store", default=None)

    def _validate_options(self):
        CliCommand._validate_options(self)

        if self.options.remove and self.options.add:
            print (_("--add cannot be used with --remove\n"))
            sys.exit(1)

        if (self.options.remove or self.options.add) and not self.options.fields:
            option = "--add" if self.options.add else "--remove"
            print(_("%s requires --fields\n") % option)
            sys.exit(1)

        if not self.options.name:
            self.parser.print_help()
            sys.exit(1)

    def _do_command(self):
        r = self.config.get_report(self.options.name)

        if not r:
            print(_("report %s does not exist.") % self.options.name)
            sys.exit(1)

        if self.options.output_filename:
            r.output_filename = self.options.output_filename

        if self.options.fields:
            fields = self.options.fields.strip().split(",")
            if self.options.add:
                r.report_format.extend(fields)
            elif self.options.remove:
                r.report_format = [field for field in r.report_format if field not in fields]
            else:
                r.report_format = fields

        c = config.ConfigBuilder().dump_config(self.config)
        crypto.write_file(self.options.config, c, self.passphrase)
        print(_("Report %s edited" % self.options.name))


class ReportClearCommand(CliCommand):

    def __init__(self):
        usage = _("usage: %prog report clear [--name | --all] [options]")
        shortdesc = _("removes 1 or all reports from list")
        desc = _("removes reports")

        CliCommand.__init__(self, "report clear", usage, shortdesc, desc)

        self.parser.add_option("--name", dest="name", metavar="NAME",
                               help=_("NAME of the report to be removed"))
        self.parser.add_option("--all", dest="all", action="store_true",
                               help=_("remove ALL reports"))

        self.parser.set_defaults(all=False)

    def _validate_options(self):
        CliCommand._validate_options(self)

        if not self.options.name and not self.options.all:
            self.parser.print_help()
            sys.exit(1)

        if self.options.name and self.options.all:
            self.parser.print_help()
            sys.exit(1)

    def _do_command(self):
        if self.options.name:
            if self.config.has_report(self.options.name):
                self.config.remove_report(self.options.name)
                c = config.ConfigBuilder().dump_config(self.config)
                crypto.write_file(self.options.config, c, self.passphrase)
                print(_("report %s removed" % self.options.name))
            else:
                print(_("ERROR: No such report: %s") % self.options.name)
                sys.exit(1)
        elif self.options.all:
            self.config.clear_reports()
            c = config.ConfigBuilder().dump_config(self.config)
            crypto.write_file(self.options.config, c, self.passphrase)
            print(_("All reports removed"))


class ReportAddCommand(CliCommand):

    def __init__(self):
        usage = _("usage: %prog report add [options]")
        shortdesc = _("add a report")
        desc = _("add a report")

        CliCommand.__init__(self, "report add", usage, shortdesc, desc)

        self.parser.add_option("--name", dest="name", metavar="NAME",
                               help=_("NAME of the report - REQUIRED"))
        self.parser.add_option("--fields", "--report-format", dest="fields",
                               metavar="FIELDS", help=_("set what FIELDS the report has - REQUIRED"),
                               action="store", default=[])
        self.parser.add_option("--output", dest="output_filename",
                               metavar="FILENAME", help=_("output report to FILENAME"), action="store", default=None)

    def _validate_options(self):
        CliCommand._validate_options(self)

        if not self.options.name or not self.options.fields:
            self.parser.print_help()
            sys.exit(1)

    def _do_command(self):
        fields = self.options.fields.strip().split(',')

        g = config.Report(name=self.options.name,
                          report_format=fields,
                          output_filename=self.options.output_filename)
        self.config.add_report(g)
        c = config.ConfigBuilder().dump_config(self.config)
        crypto.write_file(self.options.config, c, self.passphrase)


class ProfileShowCommand(CliCommand):

    def __init__(self):
        usage = _("usage: %prog profile show [options]")
        shortdesc = _("show a network profile")
        desc = _("show a network profile")

        CliCommand.__init__(self, "profile show", usage, shortdesc, desc)

        self.parser.add_option("--name", dest="name", metavar="NAME",
                               help=_("profile name - REQUIRED"))

    def _validate_options(self):
        CliCommand._validate_options(self)

        if not self.options.name:
            self.parser.print_help()
            sys.exit(1)

    def _do_command(self):
        if not self.config.list_profiles():
            print(_("No profiles found"))

        p = self.config.get_profile(self.options.name)

        if not p:
            print(_("No profile '%s' found.") % self.options.name)
            return

        # using OutputPrinter didn't look so
        # nice for profiles
        printer = ProfilePrinter([p])
        printer.write()


class ProfileListCommand(CliCommand):

    def __init__(self):
        usage = _("usage: %prog profile list [options]")
        shortdesc = _("list the network profiles")
        desc = _("list the network profiles")

        CliCommand.__init__(self, "profile list", usage, shortdesc, desc)

    def _do_command(self):

        if not self.config.list_profiles():
            print(_("No profiles found"))
            return

        # using OutputPrinter didn't look so
        # nice for profiles
        printer = ProfilePrinter(self.config.list_profiles())
        printer.write()


class ProfileEditCommand(CliCommand):

    def __init__(self):
        usage = _("usage: %prog profile edit [options]")
        shortdesc = _("edits a given profile")
        desc = _("edit a given profile")

        CliCommand.__init__(self, "profile edit", usage, shortdesc, desc)

        self.parser.add_option("--name", dest="name", metavar="NAME",
                               help=_("NAME of the profile - REQUIRED"))
        self.parser.add_option("--range", dest="ranges", action="append",
                               metavar="RANGE", default=[],
                               help=_("IP range to scan. See 'man rho' for supported formats."))
        self.parser.add_option("--hosts", dest="hosts", action="store",
                               metavar="HOST", default='',
                               help=_("File of hostnames to scan."))
        self.parser.add_option("--ports", dest="ports", metavar="PORTS",
                               help=_("list of ssh ports to try i.e. '22, 2222, 5402'")),
        self.parser.add_option("--auth", dest="auth", metavar="AUTH",
                               action="append", default=[],
                               help=_("auth class to associate with profile"))

        self.parser.set_defaults(ports="22")

    def _validate_options(self):
        CliCommand._validate_options(self)

        if self.options.ranges:
            self._validate_ranges(self.options.ranges)

        if not self.options.name:
            self.parser.print_help()
            sys.exit(1)

    def _do_command(self):
        g = self.config.get_profile(self.options.name)

        if not g:
            print(_("Profile %s does not exist.") % self.options.name)
            sys.exit(1)

        if self.options.ranges:
            g.ranges = self.options.ranges

        if self.options.hosts:
            g.ranges += _read_hosts_file(self.options.hosts)

        if self.options.ports:
            g.ports = self.options.ports.strip().split(",")
            self._validate_ports(g.ports)
        if len(self.options.auth) > 0:
            g.auth_names = []
            for auth in self.options.auth:
                for a in auth.strip().split(","):
                    g.auth_names.append(a)

        # unfortunately can't valid these in _validate_options
        # as we don't have a config at that point
        for auth in self.options.auth:
            for a in auth.strip().split(","):
                try:
                    self.config.get_auth(a)
                except config.NoSuchAuthError as e:
                    print _("ERROR: No such auth: %s") % e.authname
                    sys.exit(1)

        c = config.ConfigBuilder().dump_config(self.config)
        crypto.write_file(self.options.config, c, self.passphrase)
        print(_("Profile %s edited" % self.options.name))


class ProfileClearCommand(CliCommand):

    def __init__(self):
        usage = _("usage: %prog profile clear [--name | --all] [options]")
        shortdesc = _("removes 1 or all profiles from list")
        desc = _("removes profiles")

        CliCommand.__init__(self, "profile clear", usage, shortdesc, desc)

        self.parser.add_option("--name", dest="name", metavar="NAME",
                               help=_("NAME of the profile to be removed"))
        self.parser.add_option("--all", dest="all", action="store_true",
                               help=_("remove ALL profiles"))

        self.parser.set_defaults(all=False)

    def _validate_options(self):
        CliCommand._validate_options(self)

        if not self.options.name and not self.options.all:
            self.parser.print_help()
            sys.exit(1)

        if self.options.name and self.options.all:
            self.parser.print_help()
            sys.exit(1)

    def _do_command(self):
        if self.options.name:
            if self.config.has_profile(self.options.name):
                self.config.remove_profile(self.options.name)
                c = config.ConfigBuilder().dump_config(self.config)
                crypto.write_file(self.options.config, c, self.passphrase)
                print(_("Profile %s removed" % self.options.name))
            else:
                print(_("ERROR: No such profile: %s") % self.options.name)
                sys.exit(1)
        elif self.options.all:
            self.config.clear_profiles()
            c = config.ConfigBuilder().dump_config(self.config)
            crypto.write_file(self.options.config, c, self.passphrase)
            print(_("All network profiles removed"))


class ProfileAddCommand(CliCommand):

    def __init__(self):
        usage = _("usage: %prog profile add [options]")
        shortdesc = _("add a network profile")
        desc = _("add a network profile")

        CliCommand.__init__(self, "profile add", usage, shortdesc, desc)

        self.parser.add_option("--name", dest="name", metavar="NAME",
                               help=_("NAME of the profile - REQUIRED"))
        self.parser.add_option("--range", dest="ranges", action="append",
                               metavar="RANGE", default=[],
                               help=_("IP range to scan. See 'man rho' for supported formats."))
        self.parser.add_option("--hosts", dest="hosts", action="store",
                               metavar="HOST", default='',
                               help=_("File of hostnames to scan."))
        self.parser.add_option("--ports", dest="ports", metavar="PORTS",
                               help=_("list of ssh ports to try i.e. '22, 2222, 5402'")),
        self.parser.add_option("--auth", dest="auth", metavar="AUTH",
                               action="append", default=[],
                               help=_("auth class to associate with profile"))

        self.parser.set_defaults(ports="22")

    def _validate_options(self):
        CliCommand._validate_options(self)

        if self.options.ranges:
            self._validate_ranges(self.options.ranges)

        if not self.options.name:
            self.parser.print_help()
            sys.exit(1)

    def _do_command(self):
        ports = []
        if self.options.ports:
            ports = self.options.ports.strip().split(",")
            self._validate_ports(ports)
        if self.options.hosts:
            self.options.ranges += _read_hosts_file(self.options.hosts)

        auth_names = []
        for auth in self.options.auth:
            for a in auth.strip().split(","):
                auth_names.append(a)

        # unfortunately can't valid these in _validate_options
        # as we don't have a config at that point
        for auth in self.options.auth:
            for a in auth.strip().split(","):
                try:
                    self.config.get_auth(a)
                except config.NoSuchAuthError as e:
                    print _("ERROR: No such auth: %s") % e.authname
                    sys.exit(1)

        g = config.Profile(name=self.options.name, ranges=self.options.ranges,
                           auth_names=auth_names, ports=ports)
        self.config.add_profile(g)
        c = config.ConfigBuilder().dump_config(self.config)
        crypto.write_file(self.options.config, c, self.passphrase)


class AuthEditCommand(CliCommand):

    def __init__(self):
        usage = _("usage: %prog auth edit [options]")
        shortdesc = _("edits a given auth")
        desc = _("edit a given auth")

        CliCommand.__init__(self, "auth edit", usage, shortdesc, desc)

        self.parser.add_option("--name", dest="name", metavar="NAME",
                               help=_("NAME of the auth - REQUIRED"))

        self.parser.add_option("--file", dest="filename", metavar="FILENAME",
                               help=_("file containing SSH key"))
        self.parser.add_option("--username", dest="username",
                               metavar="USERNAME",
                               help=_("user name for authenticating against target machine - REQUIRED"))
        self.parser.add_option("--password", dest="password",
                               action="store_true",
                               help=_("password for authenticating against target machine"))

        self.parser.set_defaults(password=False)

    def _validate_options(self):
        CliCommand._validate_options(self)

        if not self.options.name:
            self.parser.print_help()
            sys.exit(1)

    def _do_command(self):
        a = self.config.get_auth(self.options.name)

        if not a:
            print(_("Auth %s does not exist.") % self.options.name)
            sys.exit(1)

        if self.options.username:
            a.username = self.options.username

        if self.options.password:
            a.password = get_password(a.username, RHO_AUTH_PASSWORD)

        if self.options.filename:

            sshkey = _read_key_file(self.options.filename)

            if a.type == config.SSH_TYPE:
                cred = config.SshKeyAuth({"name": a.name,
                                          "key": sshkey,
                                          "username": a.username,
                                          "password": a.password,
                                          "type": "ssh_key"})
                # remove the old ssh, and new key type
                self.config.remove_auth(self.options.name)
                self.config.add_auth(cred)

            elif a.type == config.SSH_KEY_TYPE:
                a.key = sshkey

        c = config.ConfigBuilder().dump_config(self.config)
        crypto.write_file(self.options.config, c, self.passphrase)
        print(_("Auth %s updated" % self.options.name))


class AuthClearCommand(CliCommand):

    def __init__(self):
        usage = _("usage: %prog auth clear")
        shortdesc = _("clears out the credentials")
        desc = _("clears out the crendentials")

        CliCommand.__init__(self, "auth clear", usage, shortdesc, desc)

        self.parser.add_option("--name", dest="name", metavar="NAME",
                               help=_("NAME of the auth credential to be removed"))
        self.parser.add_option("--all", dest="all", action="store_true",
                               help=_("remove ALL auth credentials"))

    def _validate_options(self):
        CliCommand._validate_options(self)

        if not self.options.name and not self.options.all:
            self.parser.print_help()
            sys.exit(1)

        if self.options.name and self.options.all:
            self.parser.print_help()
            sys.exit(1)

    def _do_command(self):
        if self.options.name:
            self.config.remove_auth(self.options.name)
        elif self.options.all:
            self.config.clear_auths()

        c = config.ConfigBuilder().dump_config(self.config)
        crypto.write_file(self.options.config, c, self.passphrase)


class AuthShowCommand(CliCommand):

    def __init__(self):
        usage = _("usage: %prog auth show [options]")
        shortdesc = _("show auth credential")
        desc = _("show authentication crendential")

        CliCommand.__init__(self, "auth show", usage, shortdesc, desc)

        self.parser.add_option("--name", dest="name", metavar="NAME",
                               help=_("auth credential name - REQUIRED"))
        self.parser.add_option("--showkeys", dest="keys", action="store_true",
                               help=_("show ssh keys in the list"))

    def _validate_options(self):
        CliCommand._validate_options(self)

        if not self.options.name:
            self.parser.print_help()
            sys.exit(1)

    def _do_command(self):
        if not self.config.list_auths():
            print(_("No auth credentials found"))

        keys = ["name", "type", "username", "password", "key"]
        out = OutputPrinter(keys, dontpad=["key"])

        c = self.config.get_auth(self.options.name)
        c1 = dict(**c.to_dict())

        c1["password"] = "********"

        if c.type == "ssh_key" and not self.options.keys:
            c1["key"] = "*******"

        out.add_row(c1)
        out.write()
        print("")


class AuthListCommand(CliCommand):

    def __init__(self):
        usage = _("usage: %prog auth list [options]")
        shortdesc = _("list auth credentials")
        desc = _("list authentication crendentials")

        CliCommand.__init__(self, "auth list", usage, shortdesc, desc)

        self.parser.add_option("--showkeys", dest="keys", action="store_true",
                               help=_("show ssh keys in the list"))

    def _do_command(self):
        if not self.config.list_auths():
            print(_("No auth credentials found"))
            return

        keys = ["name", "type", "username", "password", "key"]
        out = OutputPrinter(keys, dontpad=["key"])

        for c in self.config.list_auths():
            # copy it
            c1 = dict(**c.to_dict())

            c1["password"] = "********"

            if c.type == "ssh_key" and not self.options.keys:
                c1["key"] = "*******"

            out.add_row(c1)
        out.write()
        print("")


class AuthAddCommand(CliCommand):

    def __init__(self):
        usage = _("usage: %prog auth add [options]")
        shortdesc = _("add auth credentials to config")
        desc = _("adds the authorization credentials to the config")

        CliCommand.__init__(self, "auth add", usage, shortdesc, desc)

        self.parser.add_option("--name", dest="name", metavar="NAME",
                               help=_("auth credential name - REQUIRED"))
        self.parser.add_option("--file", dest="filename", metavar="FILENAME",
                               help=_("file containing SSH key"))
        self.parser.add_option("--username", dest="username",
                               metavar="USERNAME",
                               help=_("user name for authenticating against target machine - REQUIRED"))

    def _validate_options(self):
        CliCommand._validate_options(self)

        if not self.options.name:
            self.parser.print_help()
            sys.exit(1)

        # need to pass in file or username:
        if not self.options.username:
            self.parser.print_help()
            sys.exit(1)

    def _save_cred(self, cred):
        self.config.add_auth(cred)
        c = config.ConfigBuilder().dump_config(self.config)
        crypto.write_file(self.options.config, c, self.passphrase)

    def _validate_key_and_passphrase(self):
        self.auth_passphrase = ""
        # if key works sans a password, we dont need one
        if not ssh_key_passphrase_is_good(self.options.filename):
            self.auth_passphrase = get_passphrase(self.options.filename)
            # validate the passphrase for the key is correct
            if not ssh_key_passphrase_is_good(self.options.filename, self.auth_passphrase):
                print _("Wrong passphrase for %s" % self.options.filename)
                sys.exit(1)

    def _do_command(self):
        if self.options.filename:
            # using sshkey
            self._validate_key_and_passphrase()
            sshkey = _read_key_file(self.options.filename)

            cred = config.SshKeyAuth({"name": self.options.name,
                                      "key": sshkey,
                                      "username": self.options.username,
                                      "password": self.auth_passphrase,
                                      "type": "ssh_key"})

            self._save_cred(cred)

        elif self.options.username:
            auth_password = get_password(self.options.username,
                                         RHO_AUTH_PASSWORD)

            # using ssh
            cred = config.SshAuth({"name": self.options.name,
                                   "username": self.options.username,
                                   "password": auth_password,
                                   "type": "ssh"})
            self._save_cred(cred)
