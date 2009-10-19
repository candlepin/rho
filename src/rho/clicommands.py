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

import sys
import os

import gettext
t = gettext.translation('rho', 'locale', fallback=True)
_ = t.ugettext

from optparse import OptionParser
from getpass import getpass
import simplejson as json

from rho import config
from rho import crypto
from rho import scanner
from rho import ssh_jobs

RHO_PASSPHRASE = "RHO_PASSPHRASE"
DEFAULT_RHO_CONF = "~/.rho.conf"

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
        self.parser.add_option("--debug", dest="debug",
                help=_("enable debug output"))

        # Default is expanded later:
        self.parser.add_option("--config", dest="config",
                help=_("config file name"), default=DEFAULT_RHO_CONF)


    def _validate_options(self):
        """ 
        Sub-commands can override to do any argument validation they 
        require. 
        """
        pass

    def _do_command(self):
        pass

    def _read_config(self, filename, passphrase):
        if os.path.exists(filename):
            confstr = crypto.read_file(filename, passphrase)
            return config.ConfigBuilder().build_config(confstr)
        else:
            print _("Creating new config file: %s" % filename)
            return config.Config()

    def main(self):
        (self.options, self.args) = self.parser.parse_args()

        # Translate path to config file to something absolute and expanded:
        self.options.config = os.path.abspath(os.path.expanduser(
            self.options.config))

        self._validate_options()

        if len(sys.argv) < 2:
            print(self.parser.error(_("Please enter at least 2 args")))
            sys.exit(1)

        if RHO_PASSPHRASE in os.environ:
            self.passphrase = os.environ[RHO_PASSPHRASE]
        else:
            self.passphrase = getpass()

        self.config = self._read_config(self.options.config, self.passphrase)

        # do the work
        self._do_command()

class ScanCommand(CliCommand):
    def __init__(self):
        usage = _("usage: %prog scan [ip|ip_range|ip_range_profile|hostname]")
        shortdesc = _("scan given machines")
        desc = _("scans the given machines")

        CliCommand.__init__(self, "scan", usage, shortdesc, desc)

        self.parser.add_option("--all", dest="all", action="store_true",
                help=_("remove ALL profiles"))
        self.parser.add_option("--ip_start", dest="ipstart", metavar="IPSTART",
                help=_("beginning of ip range"))
        self.parser.add_option("--ip_end", dest="ipend", metavar="IPEND",
                help=_("end of ip range"))
        self.parser.add_option("--ip", dest="ip", metavar="IP",
                help=_("single ip/hostname to scan"))
        self.parser.add_option("--ports", dest="ports", metavar="PORTS",
                help=_("list of ssh ports to try i.e. '22, 2222, 5402'"))
        self.parser.add_option("--username", dest="username", metavar="USERNAME",
                help=_("user name for authenticating against target machine"))
        self.parser.add_option("--password", dest="password", metavar="PASSWORD",
                help=_("password for authenticating against target machine")),
        self.parser.add_option("--auth", dest="auth", metavar="AUTH",
                help=_("auth class name to use"))

    def _validate_options(self):
        CliCommand._validate_options(self)
        if not self.options.ip:
            print(self.parser.print_help())
            sys.exit(1)

    def _do_command(self):
        print("scan called")
        self.scanner = scanner.Scanner()
        if self.options.auth:
            auth = self.config.get_credentials(self.options.auth)
        else:
            # FIXME: need a more abstrct credentials class -akl
            auth=config.SshCredentials({'name':"clioptions", 
                                        'username':self.options.username,
                                        'password':self.options.password,
                                        'type':'ssh'})
        # this is all temporary, but make the tests pass
        if self.options.ip:
            self.scanner.scan(ip=self.options.ip, auth=auth)


class DumpConfigCommand(CliCommand):
    """
    Dumps the config file to stdout.
    """

    def __init__(self):
        usage = _("usage: %prog dumpconfig [--encrypted-file]")
        shortdesc = _("dumps the config file to stdout")
        desc = _("dumps the config file to stdout")

        CliCommand.__init__(self, "dumpconfig", usage, shortdesc, desc)
        self.parser.add_option("--pretty", dest="pretty", metavar="pretty",
                               help=_("pretty print config output"))

    def _validate_options(self):
        CliCommand._validate_options(self)

        if not os.path.exists(self.options.config):
            print _("No such file: %s" % self.options.config)
            sys.exit(1)

        if (not os.access(self.options.config, os.R_OK)):
            print(self.parser.print_help())
            sys.exit(1)


    def _do_command(self):
        """
        Executes the command.
        """
        content = crypto.read_file(self.options.config, self.passphrase)
        print(json.dumps(json.loads(content), sort_keys = True, indent = 4))

        
class ProfileShowCommand(CliCommand):
    def __init__(self):
        usage = _("usage: %prog profile show [options]")
        shortdesc = _("show the network profiles")
        desc = _("show the network profiles")

        CliCommand.__init__(self, "profile show", usage, shortdesc, desc)

    def _do_command(self):
        if not self.config.list_groups():
            print(_("No profiles found"))

        for g in self.config.list_groups():
            # make this a pretty table
            print(g.to_dict())

class ProfileClearCommand(CliCommand):
    def __init__(self):
        usage = _("usage: %prog profile clear [--name | --all] [options]")
        shortdesc = _("clears profile list")
        desc = _("add a network profile")

        CliCommand.__init__(self, "profile clear", usage, shortdesc, desc)

        self.parser.add_option("--name", dest="name", metavar="NAME",
                help=_("NAME of the profile to be removed"))
        self.parser.add_option("--all", dest="all", action="store_true",
                help=_("remove ALL profiles"))

        self.parser.set_defaults(all=False)

    def _validate_options(self):
        CliCommand._validate_options(self)

        if not self.options.name and not self.options.all:
            print(self.parser.print_help())
            sys.exit(1)

        if self.options.name and self.options.all:
            print(self.parser.print_help())
            sys.exit(1)

    def _do_command(self):
        if self.options.name:
            raise NotImplementedError
        elif self.options.all:
            self.config.clear_groups()
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
        self.parser.add_option("--ip_start", dest="ipstart", metavar="IPSTART",
                help=_("beginning of ip range"))
        self.parser.add_option("--ip_end", dest="ipend", metavar="IPEND",
                help=_("end of ip range"))
        self.parser.add_option("--ports", dest="ports", metavar="PORTS",
                help=_("list of ssh ports to try i.e. '22, 2222, 5402'"))

        self.parser.set_defaults(ports="22")

    def _validate_options(self):
        CliCommand._validate_options(self)

        if not self.options.name:
            print(self.parser.print_help())
            sys.exit(1)

    def _create_range(self, start, end):
        # TODO: need some ip address parsing code here
        if not start:
            return None

        if end:
            return "%s-%s" % (start, end)
        else:
            return start

    def _do_command(self):
        ports = []
        if self.options.ports:
            ports = self.options.ports.strip().split(",")
        ip_range = self._create_range(self.options.ipstart, self.options.ipend)
        g = config.Group(name=self.options.name, ranges=ip_range,
                         credential_names=[], ports=ports)
        self.config.add_group(g)
        c = config.ConfigBuilder().dump_config(self.config)
        print(c)
        crypto.write_file(self.options.config, c, self.passphrase)

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
            print(self.parser.print_help())
            sys.exit(1)

        if self.options.name and self.options.all:
            print(self.parser.print_help())
            sys.exit(1)

    def _do_command(self):
        if self.options.name:
            self.config.remove_credential(self.options.name)
        elif self.options.all:
            self.config.clear_credentials()

        c = config.ConfigBuilder().dump_config(self.config)
        crypto.write_file(self.options.config, c, self.passphrase)

# TODO not sure if we want to have separate classes for sub/subcommands
class AuthShowCommand(CliCommand):
    def __init__(self):
        usage = _("usage: %prog auth show [options]")
        shortdesc = _("show auth credentials")
        desc = _("show authentication crendentials")

        CliCommand.__init__(self, "auth show", usage, shortdesc, desc)

        self.parser.add_option("--keys", dest="keys", action="store_true",
                help=_("shows auth keys"))
        self.parser.add_option("--usernames", dest="usernames",
                action="store_true", help=_("shows auth keys"))

    def _do_command(self):
        if not self.config.list_credentials():
            print(_("No auth credentials found"))

        for c in self.config.list_credentials():
            # make this a pretty table
            print(c.to_dict())

# TODO not sure if we want to have separate classes for sub/subcommands
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
        self.parser.add_option("--username", dest="username", metavar="USERNAME",
                help=_("user name for authenticating against target machine"))
        self.parser.add_option("--password", dest="password", metavar="PASSWORD",
                help=_("password for authenticating against target machine"))

    def _validate_options(self):
        CliCommand._validate_options(self)

        if not self.options.name:
            print(self.parser.print_help())

        # need to pass in file or username and password combo
        if self.options.filename:
            if self.options.password:
                self.parser.error(
                    _("can not use --file with --username or --password"))
            return

        if not self.options.username or not self.options.password and not self.options.filename:
            print(self.parser.print_help())
            sys.exit(1)

    def _save_cred(self, cred):
        try:
            self.config.add_credentials(cred)
        except config.DuplicateNameError:
            #FIXME: need to handle this better... -akl
            print _("The auth name %s already exists" % cred.name)
            return
        c = config.ConfigBuilder().dump_config(self.config)
        crypto.write_file(self.options.config, c, self.passphrase)
        
    def _do_command(self):
        if self.options.filename:
            # using sshkey
            sshkeyfile = open(os.path.expanduser(os.path.expandvars(self.options.filename)), "r")
            sshkey = sshkeyfile.read()
            sshkeyfile.close()

            
            cred = config.SshKeyCredentials({"name": self.options.name,
                                             "key":sshkey,
                                             "username": self.options.username,
                                             "type":"ssh"})



            self._save_cred(cred)


        elif self.options.username and self.options.password:
            # using ssh
            cred = config.SshCredentials({"name":self.options.name,
                                             "username":self.options.username,
                                             "password":self.options.password,
                                             "type":"ssh"})
            self._save_cred(cred)
