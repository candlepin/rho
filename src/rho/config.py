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
AUTHS_KEY = "auths"
PROFILES_KEY = "profiles"
VERSION_KEY = "version"
NAME_KEY = "name"
TYPE_KEY = "type"
USERNAME_KEY = "username"
PASSWORD_KEY = "password"
SSHKEY_KEY = "key"
RANGE_KEY = "range"
PORTS_KEY = "ports"

SSH_TYPE = "ssh"
SSH_KEY_TYPE = "ssh_key"

# Current config version, bump this if we ever change the format:
CONFIG_VERSION = 2


class BadJsonException(Exception):
    pass


class ConfigError(Exception):
    pass


class DuplicateNameError(Exception):

    def __init__(self, value):
        self.dupe_name = value


class NoSuchAuthError(Exception):

    def __init__(self, value):
        self.authname = value


def verify_keys(check_dict, required=[], optional=None):
    """
    Verify that all required keys are present in the dict, and nothing
    extraneous is present.

    Assumes that if optional arguments is not specified, we're only checking
    for required keys and can safely pass over anything extra. Specify an
    empty list for optional if you wish to check for required tags and
    error out if anything extra is found.

    Will throw a ConfigError if anything is amiss.
    """
    for required_key in required:
        if required_key not in check_dict:
            raise ConfigError("Missing required key: %s" %
                              required_key)

    if optional is not None:
        for key in check_dict:
            if (key not in required) and (key not in optional):
                raise ConfigError("Extraneous key: %s" %
                                  required_key)


class Config(object):

    """ Simple object represeting Rho configuration. """

    def __init__(self, auths=None, profiles=None):
        """
        Create a config object from the given auths and profiles.
        """

        self._auths = []
        self._profiles = []
        # Will map auth key name to the auths object:
        self._auth_index = {}
        self._profile_index = {}

        # Need to iterate auths first:
        if auths:
            for c in auths:
                self.add_auth(c)

        if profiles:
            # Make sure none of the profiles reference invalid auth keys:
            for profile in profiles:
                self.add_profile(profile)

    def add_auth(self, c):

        if c.name in self._auth_index:
            raise DuplicateNameError(c.name)

        self._auths.append(c)
        self._auth_index[c.name] = c

    def remove_auth(self, cname):
        if cname in self._auth_index:
            c = self._auth_index[cname]
            self._auths.remove(c)
            del self._auth_index[cname]

            for profile in self._profiles:
                profile.remove_auth_name(cname)

        # TODO: need to raise error here, user shouldn't see nothing if
        # they botched their command to remove a auth
        else:
            raise NoSuchAuthError(cname)

    def get_auth(self, cname):
        if cname not in self._auth_index:
            raise NoSuchAuthError(cname)
        return self._auth_index.get(cname)

    def list_auths(self):
        """ Return a list of all auth objects in this configuration. """
        # TODO: Should this return a copy of list? Immutable?
        return self._auths

    def clear_auths(self):
        self._auths = []
        self._auth_index = {}

    def add_profile(self, profile):
        """
        Add a new profile to this configuration, and ensure it references valid
        auths.
        """
        if profile.name in self._profile_index:
            raise DuplicateNameError(profile.name)

        for c in profile.auth_names:
            if c not in self._auth_index:
                raise NoSuchAuthError(c)

        self._profiles.append(profile)
        self._profile_index[profile.name] = profile

    def list_profiles(self):
        """ Return a list of all profiles in this configuration. """
        return self._profiles

    def get_profile(self, gname):
        return self._profile_index.get(gname)

    def clear_profiles(self):
        self._profiles = []
        self._profile_index = {}

    def has_profile(self, pname):
        return pname in self._profile_index

    def remove_profile(self, gname):
        if gname in self._profile_index:
            g = self._profile_index[gname]
            self._profiles.remove(g)
            del self._profile_index[gname]
        # TODO: need to raise error here, user shouldn't see nothing if
        # they botched their command to remove a profile

    def to_dict(self):
        creds = []
        for c in self._auths:
            creds.append(c.to_dict())
        profiles = []
        for g in self._profiles:
            profiles.append(g.to_dict())
        return {
            VERSION_KEY: CONFIG_VERSION,
            AUTHS_KEY: creds,
            PROFILES_KEY: profiles
        }


class Auth(object):

    def to_dict(self):
        raise NotImplementedError


class SshAuth(Auth):

    def __init__(self, json_dict):

        verify_keys(json_dict, required=[NAME_KEY, TYPE_KEY,
                                         USERNAME_KEY, PASSWORD_KEY], optional=[])

        self.name = json_dict[NAME_KEY]
        self.username = json_dict[USERNAME_KEY]
        self.password = json_dict[PASSWORD_KEY]
        self.type = SSH_TYPE

    def to_dict(self):
        return {
            NAME_KEY: self.name,
            USERNAME_KEY: self.username,
            PASSWORD_KEY: self.password,
            TYPE_KEY: SSH_TYPE
        }


class SshKeyAuth(Auth):

    def __init__(self, json_dict):

        verify_keys(json_dict, required=[NAME_KEY, TYPE_KEY,
                                         USERNAME_KEY, SSHKEY_KEY], optional=[PASSWORD_KEY])

        self.name = json_dict[NAME_KEY]
        self.username = json_dict[USERNAME_KEY]
        self.key = json_dict[SSHKEY_KEY]
        self.type = SSH_KEY_TYPE

        # Password is optional for ssh keys.
        self.password = ''
        if PASSWORD_KEY in json_dict:
            self.password = json_dict[PASSWORD_KEY]

    def to_dict(self):
        return {
            NAME_KEY: self.name,
            USERNAME_KEY: self.username,
            PASSWORD_KEY: self.password,
            TYPE_KEY: SSH_KEY_TYPE,
            SSHKEY_KEY: self.key
        }


class Profile(object):

    def __init__(self, name, ranges, auth_names, ports):
        """
        Create a profile object.

        ranges is a list of strings specifying IP ranges. We just store the
        string.

        auth_names is a list of strings referencing auth *keys*.

        ports is a list of integers.
        """
        self.name = name
        self.ranges = ranges
        self.auth_names = auth_names
        self.ports = ports

    def to_dict(self):
        return {
            NAME_KEY: self.name,
            RANGE_KEY: self.ranges,
            AUTHS_KEY: self.auth_names,
            PORTS_KEY: self.ports
        }

    def remove_auth_name(self, auth_name):
        """
        Remove the given auth name, if this profile is associated with it.
        Otherwise do nothing.
        """
        if auth_name in self.auth_names:
            self.auth_names.remove(auth_name)


# Needs to follow the class definitions:
CREDENTIAL_TYPES = {
    SSH_TYPE: SshAuth,
    SSH_KEY_TYPE: SshKeyAuth
}


class ConfigBuilder(object):

    """
    Stateless object used to parse JSON into actual objects.

    Knows how to convert JSON text to dict, and form actual objects from those
    including validation checks to ensure the config is sane.

    Also converts the other direction turning objects into JSON text.
    """

    def build_config(self, json_text):
        """ Create Config object from JSON string. """
        config_dict = None
        try:
            config_dict = json.loads(json_text)
        except ValueError:
            raise BadJsonException

        verify_keys(config_dict, required=[VERSION_KEY, AUTHS_KEY,
                                           PROFILES_KEY], optional=[])

        # Credentials needs to be parsed first so we can check that the profiles
        # reference valid credential keys.
        auths_dict = config_dict[AUTHS_KEY]
        creds = self.build_auths(auths_dict)

        profiles_dict = config_dict[PROFILES_KEY]
        profiles = self.build_profiles(profiles_dict)

        config = Config(auths=creds, profiles=profiles)

        return config

    def build_auths(self, creds_list):
        """ Create a list of Credentials object. """
        creds = []
        for auths_dict in creds_list:
            # Omit optional, will verify these once we know what class to
            # instantiate.
            verify_keys(auths_dict, required=[NAME_KEY, TYPE_KEY])

            type_key = auths_dict[TYPE_KEY]

            if type_key not in CREDENTIAL_TYPES:
                raise ConfigError("Unsupported credential type: %s",
                                  auths_dict[TYPE_KEY])

            creds_obj = CREDENTIAL_TYPES[type_key](auths_dict)
            creds.append(creds_obj)
        return creds

    def build_profiles(self, profiles_list):
        """ Create a list of Credentials object. """

        profiles = []
        for profile_dict in profiles_list:
            verify_keys(profile_dict, required=[NAME_KEY, RANGE_KEY,
                                                AUTHS_KEY, PORTS_KEY], optional=[])
            name = profile_dict[NAME_KEY]
            ranges = profile_dict[RANGE_KEY]
            auth_names = profile_dict[AUTHS_KEY]

            ports = []
            for p in profile_dict[PORTS_KEY]:
                # Make sure we can cast to integers:
                try:
                    ports.append(int(p))
                except ValueError:
                    raise ConfigError("Invalid ssh port: %s" % p)

            profile_obj = Profile(name, ranges, auth_names, ports)
            profiles.append(profile_obj)

        return profiles

    def dump_config(self, config):
        """ Returns JSON text for the given Config object. """
        config_dict = config.to_dict()
        json_text = json.dumps(config_dict)
        return json_text
