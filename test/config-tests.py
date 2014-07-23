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
    "version": 3,
    "auths": [
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
    "profiles": [
        {
            "name": "accounting",
            "range": [
                "192.168.0.0/24",
                "192.168.1.1-192.168.1.10",
                "192.168.5.0"
            ],
            "auths": ["bobskey", "bobslogin"],
            "ports": [22, 2222]
        },
        {
            "name": "it",
            "range": [
                "192.168.9.0/24"
            ],
            "auths": ["bobskey"],
            "ports": []
        }
    ],
    "reports": [
        {
            "name": "pack-scan",
            "output_filename": "pack-scan.csv",
            "report_format": [
                "date.date",
                "uname.hostname",
                "redhat-release.release",
                "redhat-packages.is_redhat",
                "redhat-packages.num_rh_packages",
                "redhat-packages.num_installed_packages",
                "redhat-packages.last_installed",
                "redhat-packages.last_built",
                "virt-what.type",
                "virt.virt",
                "virt.num_guests",
                "virt.num_running_guests",
                "cpu.count",
                "cpu.socket_count",
                "ip",
                "port"
            ]
        }
    ]
}
"""
BAD_CREDNAME_CONFIG = """
{
    "version": 1,
    "auths": [
        {
            "name": "bobslogin",
            "type": "ssh",
            "username": "bob",
            "password": "sekurity"
        }
    ],
    "profiles": [
        {
            "name": "accounting",
            "range": [
                "192.168.0.0/24",
                "192.168.1.1-192.168.1.10",
                "192.168.5.0"
            ],
            "auths": ["nosuchcredentialname"],
            "ports": [22, 2222]
        }
    ],
    "reports": [
        {
            "name": "pack-scan",
            "output_filename": "pack-scan.csv",
            "report_format": [
                "date.date",
                "uname.hostname",
                "redhat-release.release",
                "redhat-packages.is_redhat",
                "redhat-packages.num_rh_packages",
                "redhat-packages.num_installed_packages",
                "redhat-packages.last_installed",
                "redhat-packages.last_built",
                "virt-what.type",
                "virt.virt",
                "virt.num_guests",
                "virt.num_running_guests",
                "cpu.count",
                "cpu.socket_count",
                "ip",
                "port"
            ]
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
        self.assertEquals(2, len(config.list_auths()))
        self.assertEquals(2, len(config.list_profiles()))

    def test_round_trip(self):
        config = self.builder.build_config(SAMPLE_CONFIG1)
        regenerated_json = self.builder.dump_config(config)
        config2 = self.builder.build_config(regenerated_json)


class ConfigTests(unittest.TestCase):

    def setUp(self):
        self.builder = ConfigBuilder()

    def test_profile_references_invalid_auths(self):
        self.assertRaises(NoSuchAuthError,
                          self.builder.build_config, BAD_CREDNAME_CONFIG)

    def test_new_config(self):
        config = Config()
        self.assertEquals([], config.list_auths())
        self.assertEquals([], config.list_profiles())
        json = self.builder.dump_config(config)
        config = self.builder.build_config(json)

    def test_to_dict(self):
        config = self.builder.build_config(SAMPLE_CONFIG1)
        config_dict = config.to_dict()
        self.assertEquals(4, len(config_dict))
        self.assertEquals(CONFIG_VERSION, config_dict[VERSION_KEY])
        self.assertTrue(AUTHS_KEY in config_dict)
        self.assertTrue(PROFILES_KEY in config_dict)
        self.assertTrue(REPORTS_KEY in config_dict)

    def test_duplicate_credential_names(self):
        config = self.builder.build_config(SAMPLE_CONFIG1)
        # This name is already used in the SAMPLE_CONFIG1
        creds1 = SshAuth({
            NAME_KEY: "bobslogin",
            TYPE_KEY: SSH_TYPE,
            USERNAME_KEY: "bob",
            PASSWORD_KEY: "password"})
        self.assertRaises(DuplicateNameError, config.add_auth,
                          creds1)

    def test_duplicate_profile_names(self):
        config = self.builder.build_config(SAMPLE_CONFIG1)
        g = Profile("accounting", ["192.168.1.1/24"], ["bobslogin"],
                    [22])

        self.assertRaises(DuplicateNameError, config.add_profile, g)

    def test_delete_auth_used_in_profile(self):
        config = self.builder.build_config(SAMPLE_CONFIG1)
        config.remove_auth("bobskey")
        config = self.builder.build_config(
            self.builder.dump_config(config))
        self.assertEquals(1, len(config.list_auths()))
        self.assertEquals(1, len(config.get_profile("accounting").auth_names))
        self.assertEquals(0, len(config.get_profile("it").auth_names))

    def test_remove_no_such_auth(self):
        config = self.builder.build_config(SAMPLE_CONFIG1)
        self.assertRaises(NoSuchAuthError, config.remove_auth,
                          "nosuchname")


class CredentialTests(unittest.TestCase):

    def setUp(self):
        self.builder = ConfigBuilder()
        self.auths_list = [
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
        self.config_dict = {'auths': self.auths_list}

    def test_build_auths(self):
        creds = self.builder.build_auths(self.auths_list)

        self.assertEquals(2, len(creds))
        self.assertEquals("ansshlogin", creds[0].name)
        self.assertEquals(SshAuth, type(creds[0]))

        self.assertEquals("ansshkey", creds[1].name)
        self.assertEquals(SshKeyAuth, type(creds[1]))

    def test_build_auths_bad_type(self):
        self.auths_list[0][TYPE_KEY] = "badtype"
        self.assertRaises(ConfigError,
                          self.builder.build_auths, self.auths_list)

    def test_build_auths_missing_type(self):
        self.auths_list[0].pop(TYPE_KEY)
        self.assertRaises(ConfigError,
                          self.builder.build_auths, self.auths_list)

    def test_build_auths_missing_username(self):
        self.auths_list[0].pop(USERNAME_KEY)
        self.assertRaises(ConfigError,
                          self.builder.build_auths, self.auths_list)

    def test_build_auths_key_no_passphrase(self):
        # I think we're going to support a passphraseless key for now:
        self.auths_list[1].pop(PASSWORD_KEY)
        creds = self.builder.build_auths(self.auths_list)

    def test_ssh_creds_to_dict(self):
        creds = self.builder.build_auths(self.auths_list)
        ssh = creds[0]
        ssh_dict = ssh.to_dict()
        self.assertEquals(4, len(ssh_dict))
        self.assertEquals("ansshlogin", ssh_dict[NAME_KEY])
        self.assertEquals("ssh", ssh_dict[TYPE_KEY])
        self.assertEquals("bob", ssh_dict[USERNAME_KEY])
        self.assertEquals("password", ssh_dict[PASSWORD_KEY])

    def test_ssh_key_creds_to_dict(self):
        creds = self.builder.build_auths(self.auths_list)
        ssh = creds[1]
        ssh_dict = ssh.to_dict()
        self.assertEquals(5, len(ssh_dict))
        self.assertEquals("ansshkey", ssh_dict[NAME_KEY])
        self.assertEquals("ssh_key", ssh_dict[TYPE_KEY])
        self.assertEquals("bob", ssh_dict[USERNAME_KEY])
        self.assertEquals("password", ssh_dict[PASSWORD_KEY])
        self.assertEquals("whatever", ssh_dict[SSHKEY_KEY])


class ProfileTests(unittest.TestCase):

    def setUp(self):
        self.builder = ConfigBuilder()
        self.profile_dict = {
            NAME_KEY: "accounting",
            RANGE_KEY: [
                "192.168.0.0/24",
                "192.168.1.1-192.168.1.10",
                "192.168.5.0"
            ],
            AUTHS_KEY: ["bobskey", "bobslogin"],
            PORTS_KEY: [22, 2222]
        }

    def test_create_profile(self):
        g = self.builder.build_profiles([self.profile_dict])[0]
        self.assertEquals("accounting", g.name)
        self.assertEquals(2, len(g.auth_names))
        self.assertEquals(2, len(g.ports))
        self.assertEquals(22, g.ports[0])
        self.assertEquals(2222, g.ports[1])

    def test_remove_auth(self):
        g = self.builder.build_profiles([self.profile_dict])[0]
        g.remove_auth_name("bobskey")
        self.assertEquals(1, len(g.auth_names))
        g.remove_auth_name("notthere")
        self.assertEquals(1, len(g.auth_names))

    def test_empty_range(self):
        self.profile_dict[RANGE_KEY] = []
        # Just don't want to see an error:
        self.builder.build_profiles([self.profile_dict])

    def test_no_ports(self):
        self.profile_dict[PORTS_KEY] = []
        # Just don't want to see an error:
        g = self.builder.build_profiles([self.profile_dict])

    def test_invalid_ports(self):
        self.profile_dict[PORTS_KEY] = ["aslkjdh"]
        self.assertRaises(ConfigError,
                          self.builder.build_profiles, [self.profile_dict])

    def test_name_required(self):
        self.profile_dict.pop(NAME_KEY)
        self.assertRaises(ConfigError,
                          self.builder.build_profiles, [self.profile_dict])

    def test_to_dict(self):
        g = self.builder.build_profiles([self.profile_dict])[0]
        g_dict = g.to_dict()
        self.assertEquals(4, len(g_dict))
        self.assertEquals("accounting", g_dict[NAME_KEY])

        ranges = g_dict[RANGE_KEY]
        self.assertEquals(3, len(ranges))
        self.assertEquals(self.profile_dict[RANGE_KEY],
                          g_dict[RANGE_KEY])

        credential_names = g_dict[AUTHS_KEY]
        self.assertEquals(2, len(credential_names))
        self.assertEquals(self.profile_dict[AUTHS_KEY],
                          g_dict[AUTHS_KEY])

        ports = g_dict[PORTS_KEY]
        self.assertEquals(2, len(ports))
        self.assertEquals(self.profile_dict[PORTS_KEY],
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
