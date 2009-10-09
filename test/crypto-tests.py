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

import os
import unittest

import rho.crypto

class CryptoTests(unittest.TestCase):

    def test_padding(self):
        plaintext = "some plaintext" # 14 bytes long
        expected = plaintext + str(0x02) + str(0x02)
        padded = rho.crypto.pad(plaintext)
        self.assertEquals(expected, padded)

    def test_padding_none_required(self):
        plaintext = "12345678" 
        padded = rho.crypto.pad(plaintext)
        self.assertEquals(plaintext, padded)

    def test_padding_unicode_exception(self):
        """ Ensure only strings can be padded. """
        plaintext = u'12345678'
        self.assertRaises(Exception, rho.crypto.pad, plaintext)

    def test_unpad_4_bytes(self):
        plaintext = "1234" # 14 bytes long
        padded = "12344444"
        result = rho.crypto.unpad(padded)
        self.assertEquals(plaintext, result)

    def test_unpad_1_bytes(self):
        plaintext = "1234567"
        padded = "12345671"
        result = rho.crypto.unpad(padded)
        self.assertEquals(plaintext, result)

    def test_unpad_integer_plaintext(self):
        plaintext = "12345677"
        result = rho.crypto.unpad(plaintext)
        self.assertEquals(plaintext, result)

    def test_unpad_invalid_length(self):
        self.assertRaises(Exception, rho.crypto.unpad, "1234")

    def test_unpad_nonstring(self):
        self.assertRaises(Exception, rho.crypto.unpad, u'khasd')

    def test_unpad_worst_case_scenario(self):
        # Actually testing for incorrect behavior here, see method doc on 
        # unpad for more info.
        plaintext = "77777777" # no padding required
        result = rho.crypto.unpad(plaintext)
        self.assertEquals("7", result) # should be unchanged but isn't...

    def test_encryption_padding_required(self):
        plaintext = "hey look at my text $"
        key = "sekurity is alsome"
        ciphertext = rho.crypto.encrypt(plaintext, key)
        decrypted = rho.crypto.decrypt(ciphertext, key)
        self.assertEquals(plaintext, decrypted)


class FileCryptoTests(unittest.TestCase):

    def test_encrypt_file(self):
        """ Test file encryption/decryption. """
        plaintext = "i'm going into a file!"
        key = "sekurity!"
        temp_file = '/tmp/rho-crypto-test.txt'
        try:
            rho.crypto.write_file(temp_file, plaintext, key)
            result = rho.crypto.read_file(temp_file, key)
            self.assertEquals(plaintext, result)
        finally:
            try:
                os.remove(temp_file)
            except:
                pass

    def test_bad_file_location(self):
        self.assertRaises(IOError, rho.crypto.write_file,
                "/nosuchdir/nosuchfile.txt", 'blah', 'blah')
        self.assertRaises(IOError, rho.crypto.read_file,
                "/nosuchdir/nosuchfile.txt", 'blah')

