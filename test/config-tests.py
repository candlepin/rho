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

""" Tests for the config module """

import unittest

from rho.config import *
import simplejson as json

SAMPLE_CONFIG1 = """
{
    "config": {

        "credentials": [

            {
                "name": "bobslogin",
                "type": "ssh",
                "username": "bob",
                "password": "sekurity"
            },

            {
                "name": "bobskey",
                "type": "ssh_key",
                "username": "bob",
                "key": "-----BEGIN RSA PRIVATE KEY-----\\nProc-Type: 4,ENCRYPTED\\nDEK-Info:\\nBLHABLAHBLAHBLAH\\n-----END RSA PRIVATE KEY-----",
                "password": "sekurity"
            }

        ],

        "groups": [

            {
                "name": "accounting",
                "range": [
                    "192.168.0.0/24",
                    "192.168.1.1-192.168.1.10",
                    "192.168.5.0"
                ],
                "credentials": ["bobskey", "bobslogin"],
                "ports": [22, 2222]
            },

            {
                "name": "it",
                "range": [
                    "192.168.9.0/24"
                ],
                "credentials": ["bobskey"],
                "ports": []
            }

        ]

    }
}
"""


class ConfigParsingTests(unittest.TestCase):

    def setUp(self):
        self.builder = ConfigBuilder()
        self.json_dict = json.loads(SAMPLE_CONFIG1)

    def test_bad_json_string(self):
        bad_json = "does this look valid to you?"
        self.assertRaises(BadJsonException, self.builder.build_config, bad_json)

    def test_json_config_key(self):
        """ Verify top level of JSON dict is just a config key. """
        self.assertRaises(ConfigurationException, self.builder.build_config,
                "{}")
        self.assertRaises(ConfigurationException, self.builder.build_config,
                "{}")

    def test_build_config(self):
        config = self.builder.build_config(SAMPLE_CONFIG1)
        self.assertEquals(2, len(config.credentials))
        self.assertEquals(2, len(config.credential_keys))
        self.assertEquals(2, len(config.groups))

    def test_group_references_invalid_credentials(self):
        # Hack config to reference a credentials name that doesn't exist:
        self.json_dict[CONFIG_KEY][GROUPS_KEY][1][CREDENTIALS_KEY] = \
            ["nosuchcredentials"]
        self.assertRaises(ConfigurationException, Config,
                self.json_dict[CONFIG_KEY])


class CredentialParsingTests(unittest.TestCase):

    def setUp(self):
        self.credentials_dict = [
                {
                    NAME_KEY: "ansshlogin",
                    TYPE_KEY: "ssh",
                    USERNAME_KEY: "bob",
                    PASSWORD_KEY: "password"
                },
                {
                    NAME_KEY: "ansshkey",
                    TYPE_KEY: "ssh_key",
                    SSHKEY_KEY: "whatever",
                    USERNAME_KEY: "bob",
                    PASSWORD_KEY: "password"
                },
        ]
        self.config_dict = {'credentials': self.credentials_dict}

    def test_build_credentials(self):
        creds = Config(self.config_dict).credentials
        self.assertEquals(2, len(creds))
        self.assertEquals("ansshlogin", creds[0].name)
        self.assertEquals(SshCredentials, type(creds[0]))

        self.assertEquals("ansshkey", creds[1].name)
        self.assertEquals(SshKeyCredentials, type(creds[1]))

    def test_build_credentials_bad_type(self):
        self.credentials_dict[0][TYPE_KEY] = "badtype"
        self.assertRaises(ConfigurationException,
            Config, self.config_dict)

    def test_build_credentials_missing_type(self):
        self.credentials_dict[0].pop(TYPE_KEY)
        self.assertRaises(ConfigurationException,
            Config, self.config_dict)

    def test_build_credentials_missing_username(self):
        self.credentials_dict[0].pop(USERNAME_KEY)
        self.assertRaises(ConfigurationException,
            Config, self.config_dict)

    def test_build_credentials_key_no_passphrase(self):
        # I think we're going to support a passphraseless key for now:
        self.credentials_dict[1].pop(PASSWORD_KEY)
        creds = Config(self.config_dict).credentials


class GroupParsingTests(unittest.TestCase):

    def setUp(self):
        self.builder = ConfigBuilder()
        self.group_dict = {
                NAME_KEY: "accounting",
                RANGE_KEY: [
                    "192.168.0.0/24",
                    "192.168.1.1-192.168.1.10",
                    "192.168.5.0"
                    ],
                CREDENTIALS_KEY: ["bobskey", "bobslogin"],
                PORTS_KEY: [22, 2222]
            }

    def test_create_group(self):
        g = Group(self.group_dict)
        self.assertEquals("accounting", g.name)
        self.assertEquals(2, len(g.credentials))
        self.assertEquals(2, len(g.ports))
        self.assertEquals(22, g.ports[0])
        self.assertEquals(2222, g.ports[1])

    def test_empty_range(self):
        self.group_dict[RANGE_KEY] = []
        # Just don't want to see an error:
        g = Group(self.group_dict)

    def test_no_ports(self):
        self.group_dict[PORTS_KEY] = []
        # Just don't want to see an error:
        g = Group(self.group_dict)

    def test_invalid_ports(self):
        self.group_dict[PORTS_KEY] = ["aslkjdh"]
        self.assertRaises(ConfigurationException, Group, self.group_dict)

    def test_name_required(self):
        self.group_dict.pop(NAME_KEY)
        self.assertRaises(ConfigurationException, Group, self.group_dict)


class MiscTests(unittest.TestCase):

    def test_verify_keys(self):
        verify_keys({'a': 1, 'b': 2}, required=['a'], optional=['b'])

    def test_verify_keys_all_optional(self):
        verify_keys({'a': 1, 'b': 2}, optional=['a', 'b'])

    def test_verify_keys_all_required(self):
        verify_keys({'a': 1, 'b': 2}, required=['a', 'b'])

    def test_verify_keys_missing_required(self):
        self.assertRaises(ConfigurationException,
                verify_keys, {'b': 2}, required=['a'], optional=['b'])

    def test_extraneous_keys(self):
        self.assertRaises(ConfigurationException, verify_keys, 
                {'a': 1, 'b': 2}, required=['a'], optional=[])

    def test_only_check_required(self):
        # b is ignored because we didn't specify optional keys.
        verify_keys({'a': 1, 'b': 2}, required=['a'])

