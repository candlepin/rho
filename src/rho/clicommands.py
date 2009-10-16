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
import re
import simplejson as json

import gettext
t = gettext.translation('rho', 'locale', fallback=True)
_ = t.ugettext

from optparse import OptionParser
from getpass import getpass

from rho import config
from rho import crypto

RHO_PASSPHRASE = "RHO_PASSPHRASE"

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
        self.parser.add_option("--config", dest="config",
                help=_("config file name"))

        self.parser.set_defaults(config=os.path.expanduser("~/.rho.conf"))

    def _validate_options(self):
        """ 
        Sub-commands can override to do any argument validation they 
        require. """
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

    def _do_command(self):
        print("scan called")
        print self.config
        

class ProfileShowCommand(CliCommand):
    def __init__(self):
        usage = _("usage: %prog profile show [options]")
        shortdesc = _("show the network profiles")
        desc = _("show the network profiles")

        CliCommand.__init__(self, "profile show", usage, shortdesc, desc)

    def _validate_options(self):
        pass

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
        range = self._create_range(self.options.ipstart, self.options.ipend)
        g = config.Group(name=self.options.name, ranges=range,
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

    def _do_command(self):
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

    def _validate_options(self):
        pass

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
                help=_("auth credential name"))
        self.parser.add_option("--file", dest="filename", metavar="FILENAME",
                help=_("file containing SSH key"))
        self.parser.add_option("--username", dest="username", metavar="USERNAME",
                help=_("user name for authenticating against target machine"))
        self.parser.add_option("--password", dest="password", metavar="PASSWORD",
                help=_("password for authenticating against target machine"))

    def _validate_options(self):
        # need to pass in file or username and password combo
        pass

    def _do_command(self):
        if self.options.filename:
            # using sshkey
            print("nothing needed")
        elif self.options.username and self.options.password:
            # using ssh
            cred = config.SshCredentials({"name":self.options.name,
                "username":self.options.username,
                "password":self.options.password,
                "type":"ssh"})
            self.config.add_credentials(cred)
            print(self.config.list_credentials())
            c = config.ConfigBuilder().dump_config(self.config)
            print(c)
            print("[%s]" % self.passphrase)
            crypto.write_file(self.options.config, c, self.passphrase)
