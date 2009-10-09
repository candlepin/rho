#
# Based on sm-photo-tool cli.py: http://github.com/jmrodri/sm-photo-tool/
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

""" Rho Command Line Interface """

import sys
import os
import rho.clicommands




class CLI:
    def __init__(self):
        self.cli_commands = {}
        for clazz in rho.clicommands.__dict__.values():
            if isinstance(clazz, type) and  \
                    issubclass(clazz, rho.clicommands.CliCommand):

                cmd = clazz()
                # ignore the base class
                if cmd.name != "cli":
                    self.cli_commands[cmd.name] = cmd 

    def _add_command(self, cmd):
        self.cli_commands[cmd.name] = cmd
        
    def _usage(self):
        print _("\nUsage: %s [options] MODULENAME --help\n" %
            (os.path.basename(sys.argv[0])))
        print _("Supported modules:\n")
        for (name, cmd) in self.cli_commands.items():
            print("\t%-14s %-25s" % (name, cmd.shortdesc))
        print("")

    def main(self):
        if len(sys.argv) < 2 or not self.cli_commands.has_key(sys.argv[1]):
            self._usage()
            sys.exit(1)

        cmd = self.cli_commands[sys.argv[1]]
        cmd.main()

