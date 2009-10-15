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

from rho.config import *

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

    def _add_common_options(self):
        """ Add options that apply to all sub-commands. """
        self.parser.add_option("--debug", dest="debug",
                help=_("enable debug output"))
        self.parser.add_option("--config", dest="config",
                help=_("config file name"))

    def _validate_options(self):
        """ 
        Sub-commands can override to do any argument validation they 
        require. """
        pass

    def _do_command(self):
        pass

    def main(self):
        (self.options, self.args) = self.parser.parse_args()

        self._validate_options()

        if len(sys.argv) < 2:
            print(self.parser.error(_("Please enter at least 2 args")))
            sys.edit(1)

        # do the work
        self._do_command()

class ScanCommand(CliCommand):
    def __init__(self):
        usage = _("usage: %prog scan [ip|ip_range|ip_range_profile|hostname]")
        shortdesc = _("scan given machines")
        desc = _("scans the given machines")

        CliCommand.__init__(self, "scan", usage, shortdesc, desc)

    def _do_command(self):
        print("scan called")

class ProfileShowCommand(CliCommand):
    def __init__(self):
        usage = _("usage: %prog profile show [options]")
        shortdesc = _("show the network profiles")
        desc = _("show the network profiles")

        CliCommand.__init__(self, "profile show", usage, shortdesc, desc)

    def _validate_options(self):
        pass

class ProfileClearCommand(CliCommand):
    def __init__(self):
        usage = _("usage: %prog profile clear [options]")
        shortdesc = _("clears profile list")
        desc = _("add a network profile")

        CliCommand.__init__(self, "profile clear", usage, shortdesc, desc)

        self.parser.add_option("--name", dest="name", metavar="NAME",
                help=_("profile name"))

    def _validate_options(self):
        pass

    def _do_command(self):
        pass

class ProfileAddCommand(CliCommand):
    def __init__(self):
        usage = _("usage: %prog profile add [options]")
        shortdesc = _("add a network profile")
        desc = _("add a network profile")

        CliCommand.__init__(self, "profile add", usage, shortdesc, desc)

        self.parser.add_option("--name", dest="name", metavar="NAME",
                help=_("profile name"))
        self.parser.add_option("--ip_start", dest="ipstart", metavar="IPSTART",
                help=_("beginning of ip range"))
        self.parser.add_option("--ip_end", dest="ipend", metavar="IPEND",
                help=_("end of ip range"))
        self.parser.add_option("--ports", dest="ports", metavar="PORTS",
                help=_("ssh ports to try i.e. '22, 2222, 5402'"))

    def _validate_options(self):
        pass

    def _create_range(self, start, end):
        pass

    def _do_command(self):
        pass
        # TODO: not quite ready for this yet
        #ports = self.options.ports.strip().split(",")
        #self._create_range(self.options.ipstart, self.options.ipend)
        #g = Group(name=self.options.name, ranges=None, credentials=None, ports=ports)
        #cred = {} 
        #cred['name'] = self.options.name
        #cred['range'] = [self.options.ipstart]
        #c.credentials.append(cred)

        ##print(json.dumps(c))
        #print(c.credentials)

class AuthClearCommand(CliCommand):
    def __init__(self):
        usage = _("usage: %prog auth clear")
        shortdesc = _("clears out the credentials")
        desc = _("clears out the crendentials")

        CliCommand.__init__(self, "auth clear", usage, shortdesc, desc)

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

# TODO not sure if we want to have separate classes for sub/subcommands
class AuthAddCommand(CliCommand):
    def __init__(self):
        usage = _("usage: %prog auth [add|show] [options]")
        shortdesc = _("auth short desc")
        desc = _("auth long desc")

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
        # file or username and password
        if not self.options.filename or not self.options.username and not self.options.password:
            print("option required")

    def _do_command(self):
        if self.options.filename:
            # using sshkey
            print("nothing needed")
        elif self.options.username and self.options.password:
            # using ssh
            cred = SshCredentials({"name":self.options.name,
                "username":self.options.username,
                "password":self.options.password,
                "type":"ssh"})
            conf = Config(credentials=[cred])
            print(conf.credentials)
            print(conf.__dict__)
            #f = open("rho.conf", 'w')
            #f.write(json.dumps(conf.__dict__))
            #f.close()
