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
                "type": "sshkey",
                "username": "bob",
                "sshkey": "-----BEGIN RSA PRIVATE KEY-----\\nProc-Type: 4,ENCRYPTED\\nDEK-Info:\\nBLHABLAHBLAHBLAH\\n-----END RSA PRIVATE KEY-----",
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
                "credentials": ["bobskey"]
            }

        ]

    }
}
"""


class ConfigParsingTests(unittest.TestCase):

    def test_config1(self):
        config = json.loads(SAMPLE_CONFIG1)
        #print config
