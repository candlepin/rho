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

# Keys used in the configuration JSON:
CONFIG_KEY = "config"
CREDENTIALS_KEY = "credentials"
GROUPS_KEY = "groups"
NAME_KEY = "name"
TYPE_KEY = "type"
USERNAME_KEY = "username"
PASSWORD_KEY = "password"
SSHKEY_KEY = "key"
RANGE_KEY = "range"
PORTS_KEY = "ports"

SSH_TYPE = "ssh"
SSH_KEY_TYPE = "ssh_key"


class BadJsonException(Exception):
    pass


class ConfigurationException(Exception):
    pass


def verify_keys(check_dict, required=[], optional=None):
    """
    Verify that all required keys are present in the dict, and nothing
    extraneous is present.

    Assumes that if optional arguments is not specified, we're only checking
    for required keys and can safely pass over anything extra. Specify an
    empty list for optional if you wish to check for required tags and
    error out if anything extra is found.

    Will throw a ConfigurationException if anything is amiss.
    """
    for required_key in required:
        if required_key not in check_dict:
            raise ConfigurationException("Missing required key: %s" % 
                    required_key)

    if optional is not None:
        for key in check_dict:
            if (key not in required) and (key not in optional):
                raise ConfigurationException("Extraneous key: %s" %
                        required_key)


class Config(object):
    """ Simple object represeting Rho configuration. """

    def __init__(self, config_dict):
        """
        Create a config object from the incoming dict.

        dict is only used to instantiate members on the objects. Calling
        to_dict() will return a new dict with the current object state.
        """

        self.credentials = []
        self.groups = []

        # Credentials needs to be parsed first so we can check that the groups
        # reference valid credential keys.
        if CREDENTIALS_KEY in config_dict:
            credentials_dict = config_dict[CREDENTIALS_KEY]
            for creds in self._build_credentials(credentials_dict):
                self.credentials.append(creds)

        if GROUPS_KEY in config_dict:
            groups_dict = config_dict[GROUPS_KEY]
            for g in self._build_groups(groups_dict):
                self.groups.append(g)

    def _build_credentials(self, creds_list):
        """ Create a list of Credentials object. """
        creds = []

        for credentials_dict in creds_list:
            # Omit optional, will verify these once we know what class to
            # instantiate.
            verify_keys(credentials_dict, required=[NAME_KEY, TYPE_KEY])

            type_key = credentials_dict[TYPE_KEY]

            if type_key not in CREDENTIAL_TYPES:
                raise ConfigurationException("Unsupported credential type: %s",
                        credentials_dict[TYPE_KEY])

            creds_obj = CREDENTIAL_TYPES[type_key](credentials_dict)
            creds.append(creds_obj)

        return creds

    def _build_groups(self, groups_list):
        """ Create a list of Credentials object. """
        groups = []

        for group_dict in groups_list:

            group_obj = Group(group_dict)
            groups.append(group_obj)

        return groups


class Credentials(object):
    pass


class SshCredentials(Credentials):

    def __init__(self, json_dict):

        verify_keys(json_dict, required=[NAME_KEY, TYPE_KEY,
                USERNAME_KEY, PASSWORD_KEY], optional=[])

        self.name = json_dict[NAME_KEY]
        self.username = json_dict[USERNAME_KEY]
        self.password = json_dict[PASSWORD_KEY]


class SshKeyCredentials(Credentials):

    def __init__(self, json_dict):

        verify_keys(json_dict, required=[NAME_KEY, TYPE_KEY,
                USERNAME_KEY, SSHKEY_KEY], optional=[PASSWORD_KEY])

        self.name = json_dict[NAME_KEY]
        self.username = json_dict[USERNAME_KEY]
        self.key = json_dict[SSHKEY_KEY]

        # Password is optional for ssh keys.
        self.password = ''
        if PASSWORD_KEY in json_dict:
            self.password = json_dict[PASSWORD_KEY]


class Group(object):

    def __init__(self, group_dict):
        """
        Create a group object from the given dict. 
        """
        verify_keys(group_dict, required=[NAME_KEY, RANGE_KEY, CREDENTIALS_KEY,
                PORTS_KEY], optional=[])
        self.name = group_dict[NAME_KEY]
        self.range = group_dict[RANGE_KEY]
        self.credentials = group_dict[CREDENTIALS_KEY]

        self.ports = []
        for p in group_dict[PORTS_KEY]:
            # Make sure we can cast to integers:
            try:
                self.ports.append(int(p))
            except ValueError:
                raise ConfigurationException("Invalid ssh port: %s" % p)


# Needs to follow the class definitions:
CREDENTIAL_TYPES = {
        SSH_TYPE: SshCredentials,
        SSH_KEY_TYPE: SshKeyCredentials
}


class ConfigBuilder(object):
    """
    Stateless object used to parse JSON into actual objects.

    Really only exists to keep any JSON library specifics out of the other
    objects.
    """

    # TODO: This does almost nothing, bump it down to just a function.
    def build_config(self, json_text):
        """ Create Config object from JSON string. """
        json_dict = None
        try:
            json_dict = json.loads(json_text)
        except ValueError:
            raise BadJsonException

        verify_keys(json_dict, required=[CONFIG_KEY])
        config_dict = json_dict[CONFIG_KEY]

        config = Config(config_dict)

        return config


