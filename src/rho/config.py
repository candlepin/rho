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

""" Configuration Objects and Parsing Module """

import simplejson as json


class BadJsonException(Exception):
    pass


class ConfigurationException(Exception):
    pass


def verify_keys(check_hash, required=[], optional=[]):
    """
    Verify that all required keys are present in the hash, and nothing
    extraneous is present.

    Will throw a ConfigurationException if anything is amiss.
    """
    for required_key in required:
        if required_key not in check_hash:
            raise ConfigurationException("Missing required key: %s" % 
                    required_key)

    for key in check_hash:
        if (key not in required) and (key not in optional):
            raise ConfigurationException("Extraneous key: %s" % 
                    required_key)


class ConfigBuilder(object):
    """ Stateless object used to parse JSON into actual objects. """

    def parse(self, json_text):
        """ Create Config object from JSON string. """
        config = Config()
        json_hash = None
        try:
            json_hash = json.loads(json_text)
        except ValueError:
            raise BadJsonException

        #print json_hash
        verify_keys(json_hash, required=["config"])
        config_hash = json_hash['config']

        config = Config()

        return config

    def parse_credentials_hash(self):
        pass


class Config(object):
    """ Simple object represeting Rho configuration. """

    def __init__(self):
        self.credentials = []
        self.groups = []


def Credentials(object):
    pass


def Group(object):
    pass
