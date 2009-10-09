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

        # want the output sorted
        items = self.cli_commands.items()
        items.sort()
        for (name, cmd) in items:
            print("\t%-14s %-25s" % (name, cmd.shortdesc))
        print("")

    def _find_best_match(self, args):
        possiblecmd = []
        for arg in args[1:]:
            if not arg.startswith("-"):
                possiblecmd.append(arg)

        cmd = None
        key = " ".join(possiblecmd)
        if self.cli_commands.has_key(" ".join(possiblecmd)):
            cmd = self.cli_commands[key]

        i = -1
        while cmd == None:
            key = " ".join(possiblecmd[:i])
            if self.cli_commands.has_key(key):
                cmd = self.cli_commands[key]
            i -= 1

        return cmd

    def main(self):
        if len(sys.argv) < 2 or not self._find_best_match(sys.argv):
            self._usage()
            sys.exit(1)

        cmd = self._find_best_match(sys.argv)
        cmd.main()

