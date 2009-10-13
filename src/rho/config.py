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

CONFIG_KEY = "config"
CREDENTIALS_KEY = "credentials"
GROUPS_KEY = "groups"
NAME_KEY = "name"
TYPE_KEY = "type"
USERNAME_KEY = "username"
PASSWORD_KEY = "password"
SSHKEY_KEY = "key"

SSH_TYPE = "ssh"
SSH_KEY_TYPE = "ssh_key"

class BadJsonException(Exception):
    pass


class ConfigurationException(Exception):
    pass


def verify_keys(check_hash, required=[], optional=None):
    """
    Verify that all required keys are present in the hash, and nothing
    extraneous is present.

    Assumes that if optional arguments is not specified, we're only checking
    for required keys and can safely pass over anything extra. Specify an
    empty list for optional if you wish to check for required tags and
    error out if anything extra is found.

    Will throw a ConfigurationException if anything is amiss.
    """
    for required_key in required:
        if required_key not in check_hash:
            raise ConfigurationException("Missing required key: %s" % 
                    required_key)

    if optional is not None:
        for key in check_hash:
            if (key not in required) and (key not in optional):
                raise ConfigurationException("Extraneous key: %s" %
                        required_key)


class Config(object):
    """ Simple object represeting Rho configuration. """

    def __init__(self):
        """
        Create a config object from the incoming hash.

        Hash is only used to instantiate members on the objects. Calling
        to_hash() will return a new hash with the current object state.
        """

        self.credentials = []
        self.groups = []


class Credentials(object):
    pass


class SshCredentials(Credentials):
    def __init__(self, json_hash):

        verify_keys(json_hash, required=[NAME_KEY, TYPE_KEY,
                USERNAME_KEY, PASSWORD_KEY], optional=[])

        self.name = json_hash[NAME_KEY]
        self.username = json_hash[USERNAME_KEY]
        self.password = json_hash[PASSWORD_KEY]


class SshKeyCredentials(Credentials):
    def __init__(self, json_hash):

        verify_keys(json_hash, required=[NAME_KEY, TYPE_KEY,
                USERNAME_KEY, SSHKEY_KEY], optional=[PASSWORD_KEY])

        self.name = json_hash[NAME_KEY]
        self.username = json_hash[USERNAME_KEY]
        self.key = json_hash[SSHKEY_KEY]

        # Password is optional for ssh keys.
        self.password = ''
        if PASSWORD_KEY in json_hash:
            self.password = json_hash[PASSWORD_KEY]


class Group(object):
    pass


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

    def build_config(self, json_text):
        """ Create Config object from JSON string. """
        json_hash = None
        try:
            json_hash = json.loads(json_text)
        except ValueError:
            raise BadJsonException

        verify_keys(json_hash, required=[CONFIG_KEY])
        config_hash = json_hash[CONFIG_KEY]

        config = Config()

        if CREDENTIALS_KEY in config_hash:
            credentials_hash = config_hash[CREDENTIALS_KEY]
            for creds in self.build_credentials(credentials_hash):
                config.credentials.append(creds)

        return config

    def build_credentials(self, all_credentials_hash):
        """ Create a list of Credentials object. """
        creds = []

        for credentials_hash in all_credentials_hash:
            # Omit optional, will verify these once we know what class to
            # instantiate.
            verify_keys(credentials_hash, required=[NAME_KEY, TYPE_KEY])

            type_key = credentials_hash[TYPE_KEY]

            if type_key not in CREDENTIAL_TYPES:
                raise ConfigurationException("Unsupported credential type: %s",
                        credentials_hash[TYPE_KEY])

            creds_obj = None

            creds_class = CREDENTIAL_TYPES[type_key]
            if type_key == SSH_TYPE:
                creds.append(SshCredentials(credentials_hash))
            if type_key == SSH_KEY_TYPE:
                creds.append(SshKeyCredentials(credentials_hash))

        return creds


