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

import logging

LEVELS = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'warning': logging.WARNING,
          'error': logging.ERROR,
          'critical': logging.CRITICAL}

def setup_logging(filename, level):
    """
    Configure logging to the given filename.

    Specify level as a string, we'll map 'debug' to logging.DEBUG internally.
    """
    log_level = LEVELS[level.lower()]
    logging.basicConfig(filename=filename, level=log_level, filemode='w',
            format="%(asctime)s %(levelname)s - %(message)s (%(module)s/%(lineno)d)")

log = logging.getLogger()
