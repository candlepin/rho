# clicommands.py 
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the 
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

""" Rho CLI Commands """

import sys
import os
import re

from optparse import OptionParser

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
                help="enable debug output")

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
            print(parser.error("Please enter at least 2 args"))
            sys.edit(1)


class CreateCommand(CliCommand):
    def __init__(self):
        usage = "usage: %prog lulz [options]"
        shortdesc = "this is not a real command kekekeke"
        desc = "totally a fake command!"

        CliCommand.__init__(self, "lulz", usage, shortdesc, desc)

    def _validate_options(self):
        pass

