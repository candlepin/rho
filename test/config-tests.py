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
    "version": 1,
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
"""
BAD_CREDNAME_CONFIG = """
{
    "version": 1,
    "credentials": [
        {
            "name": "bobslogin",
            "type": "ssh",
            "username": "bob",
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
            "credentials": ["nosuchcredentialname"],
            "ports": [22, 2222]
        }
    ]
}
"""


class ConfigBuilderTests(unittest.TestCase):

    def setUp(self):
        self.builder = ConfigBuilder()
        self.json_dict = json.loads(SAMPLE_CONFIG1)

    def test_bad_json_string(self):
        bad_json = "does this look valid to you?"
        self.assertRaises(BadJsonException, self.builder.build_config, bad_json)

    def test_build_config(self):
        config = self.builder.build_config(SAMPLE_CONFIG1)
        self.assertEquals(2, len(config.list_credentials()))
        self.assertEquals(2, len(config.list_groups()))

    def test_round_trip(self):
        config = self.builder.build_config(SAMPLE_CONFIG1)
        regenerated_json = self.builder.dump_config(config)
        config2 = self.builder.build_config(regenerated_json)


class ConfigTests(unittest.TestCase):

    def setUp(self):
        self.builder = ConfigBuilder()

    def test_group_references_invalid_credentials(self):
        self.assertRaises(ConfigError, 
                self.builder.build_config, BAD_CREDNAME_CONFIG)

    def test_new_config(self):
        config = Config()
        self.assertEquals([], config.list_credentials())
        self.assertEquals([], config.list_groups())
        json = self.builder.dump_config(config)
        config = self.builder.build_config(json)

    def test_to_dict(self):
        config = self.builder.build_config(SAMPLE_CONFIG1)
        config_dict = config.to_dict()
        self.assertEquals(3, len(config_dict))
        self.assertEquals(CONFIG_VERSION, config_dict[VERSION_KEY])
        self.assertTrue(CREDENTIALS_KEY in config_dict)
        self.assertTrue(GROUPS_KEY in config_dict)

    def test_duplicate_credential_names(self):
        config = Config()
        creds1 = SshCredentials({
            NAME_KEY: "creds1",
            TYPE_KEY: SSH_TYPE,
            USERNAME_KEY: "bob",
            PASSWORD_KEY: "password"})
        creds2 = SshCredentials({
            NAME_KEY: "creds1",
            TYPE_KEY: SSH_TYPE,
            USERNAME_KEY: "bob2",
            PASSWORD_KEY: "password2"})
        config.add_credentials(creds1)
        self.assertRaises(DuplicateNameError, config.add_credentials, 
                creds2)


class CredentialTests(unittest.TestCase):

    def setUp(self):
        self.builder = ConfigBuilder()
        self.credentials_list = [
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
        self.config_dict = {'credentials': self.credentials_list}

    def test_build_credentials(self):
        creds = self.builder.build_credentials(self.credentials_list)

        self.assertEquals(2, len(creds))
        self.assertEquals("ansshlogin", creds[0].name)
        self.assertEquals(SshCredentials, type(creds[0]))

        self.assertEquals("ansshkey", creds[1].name)
        self.assertEquals(SshKeyCredentials, type(creds[1]))

    def test_build_credentials_bad_type(self):
        self.credentials_list[0][TYPE_KEY] = "badtype"
        self.assertRaises(ConfigError,
            self.builder.build_credentials, self.credentials_list)

    def test_build_credentials_missing_type(self):
        self.credentials_list[0].pop(TYPE_KEY)
        self.assertRaises(ConfigError,
            self.builder.build_credentials, self.credentials_list)

    def test_build_credentials_missing_username(self):
        self.credentials_list[0].pop(USERNAME_KEY)
        self.assertRaises(ConfigError,
            self.builder.build_credentials, self.credentials_list)

    def test_build_credentials_key_no_passphrase(self):
        # I think we're going to support a passphraseless key for now:
        self.credentials_list[1].pop(PASSWORD_KEY)
        creds = self.builder.build_credentials(self.credentials_list)

    def test_ssh_creds_to_dict(self):
        creds = self.builder.build_credentials(self.credentials_list)
        ssh = creds[0]
        ssh_dict = ssh.to_dict()
        self.assertEquals(4, len(ssh_dict))
        self.assertEquals("ansshlogin", ssh_dict[NAME_KEY])
        self.assertEquals("ssh", ssh_dict[TYPE_KEY])
        self.assertEquals("bob", ssh_dict[USERNAME_KEY])
        self.assertEquals("password", ssh_dict[PASSWORD_KEY])

    def test_ssh_key_creds_to_dict(self):
        creds = self.builder.build_credentials(self.credentials_list)
        ssh = creds[1]
        ssh_dict = ssh.to_dict()
        self.assertEquals(5, len(ssh_dict))
        self.assertEquals("ansshkey", ssh_dict[NAME_KEY])
        self.assertEquals("ssh_key", ssh_dict[TYPE_KEY])
        self.assertEquals("bob", ssh_dict[USERNAME_KEY])
        self.assertEquals("password", ssh_dict[PASSWORD_KEY])
        self.assertEquals("whatever", ssh_dict[SSHKEY_KEY])


class GroupTests(unittest.TestCase):

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
        g = self.builder.build_groups([self.group_dict])[0]
        self.assertEquals("accounting", g.name)
        self.assertEquals(2, len(g.credential_names))
        self.assertEquals(2, len(g.ports))
        self.assertEquals(22, g.ports[0])
        self.assertEquals(2222, g.ports[1])

    def test_empty_range(self):
        self.group_dict[RANGE_KEY] = []
        # Just don't want to see an error:
        self.builder.build_groups([self.group_dict])

    def test_no_ports(self):
        self.group_dict[PORTS_KEY] = []
        # Just don't want to see an error:
        g = self.builder.build_groups([self.group_dict])

    def test_invalid_ports(self):
        self.group_dict[PORTS_KEY] = ["aslkjdh"]
        self.assertRaises(ConfigError,
                self.builder.build_groups, [self.group_dict])

    def test_name_required(self):
        self.group_dict.pop(NAME_KEY)
        self.assertRaises(ConfigError, 
                self.builder.build_groups, [self.group_dict])

    def test_to_dict(self):
        g = self.builder.build_groups([self.group_dict])[0]
        g_dict = g.to_dict()
        self.assertEquals(4, len(g_dict))
        self.assertEquals("accounting", g_dict[NAME_KEY])

        ranges = g_dict[RANGE_KEY]
        self.assertEquals(3, len(ranges))
        self.assertEquals(self.group_dict[RANGE_KEY], 
                g_dict[RANGE_KEY])

        credential_names = g_dict[CREDENTIALS_KEY]
        self.assertEquals(2, len(credential_names))
        self.assertEquals(self.group_dict[CREDENTIALS_KEY], 
                g_dict[CREDENTIALS_KEY])

        ports = g_dict[PORTS_KEY]
        self.assertEquals(2, len(ports))
        self.assertEquals(self.group_dict[PORTS_KEY], 
                g_dict[PORTS_KEY])


class MiscTests(unittest.TestCase):

    def test_verify_keys(self):
        verify_keys({'a': 1, 'b': 2}, required=['a'], optional=['b'])

    def test_verify_keys_all_optional(self):
        verify_keys({'a': 1, 'b': 2}, optional=['a', 'b'])

    def test_verify_keys_all_required(self):
        verify_keys({'a': 1, 'b': 2}, required=['a', 'b'])

    def test_verify_keys_missing_required(self):
        self.assertRaises(ConfigError,
                verify_keys, {'b': 2}, required=['a'], optional=['b'])

    def test_extraneous_keys(self):
        self.assertRaises(ConfigError, verify_keys, 
                {'a': 1, 'b': 2}, required=['a'], optional=[])

    def test_only_check_required(self):
        # b is ignored because we didn't specify optional keys.
        verify_keys({'a': 1, 'b': 2}, required=['a'])

