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

""" Tests for the crypto module """

import unittest

import rho.crypto

from Crypto.Cipher import Blowfish

class CryptoTests(unittest.TestCase):

    def test_padding(self):
        pt = "some plaintext" # 14 bytes long
        expected = pt + str(0x02) + str(0x02)
        padded = rho.crypto.pad(pt)
        self.assertEquals(expected, padded)

    def test_padding_none_required(self):
        pt = "12345678" 
        padded = rho.crypto.pad(pt)
        self.assertEquals(pt, padded)

    def test_padding_unicode_exception(self):
        pt = u"12345678" 
        self.assertRaises(Exception, rho.crypto.pad, pt)

    def test_something(self):
        obj = Blowfish.new('mykey', Blowfish.MODE_CBC)
        plain = "hello world"

        # Plaintext needs to have a multiple of 8 bytes:
        if len(plain) % 8 != 0:
            plain = plain + 'X' * (8 - (len(plain) % 8))

        ciphertext = obj.encrypt(plain)
        self.assertTrue(plain != ciphertext)

        obj = Blowfish.new('mykey', Blowfish.MODE_CBC)
        decrypt = obj.decrypt(ciphertext)
        self.assertEquals(plain, decrypt)

