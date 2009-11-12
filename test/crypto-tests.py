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
import rho.config

class CryptoTests(unittest.TestCase):

    def setUp(self):
        self.salt = os.urandom(8)
        self.iv = os.urandom(16)

    def test_encryption1(self):
        plaintext = "hey look at my text $"
        key = "sekurity is alsome"
        ciphertext = rho.crypto.encrypt(plaintext, key, self.salt, self.iv)
        decrypted = rho.crypto.decrypt(ciphertext, key, self.salt, self.iv)
        self.assertEquals(plaintext, decrypted)

    def test_encryption2(self):
        plaintext = "hey look at my text $"
        key = "sekurity is alsome"
        ciphertext = rho.crypto.encrypt(plaintext, key, self.salt, self.iv)
        decrypted = rho.crypto.decrypt(ciphertext, key, self.salt, self.iv)
        self.assertEquals(plaintext, decrypted)

    def test_encryption_no_data(self):
        plaintext = ""
        key = "math is hard"
        ciphertext = rho.crypto.encrypt(plaintext, key, self.salt, self.iv)
        decrypted = rho.crypto.decrypt(ciphertext, key, self.salt, self.iv)
        self.assertEquals(plaintext, decrypted)
        
    # just trying to hit what might be corner cases for crypto bits with
    # padding/unpadding, etc
    def test_encryption_16_bytes(self):
        plaintext = "a" * 16
        key = "math is hard"
        ciphertext = rho.crypto.encrypt(plaintext, key, self.salt, self.iv)
        decrypted = rho.crypto.decrypt(ciphertext, key, self.salt, self.iv)
        self.assertEquals(plaintext, decrypted)

    def test_encryption_8_bytes(self):
        plaintext = "a" * 8
        key = "math is hard"
        ciphertext = rho.crypto.encrypt(plaintext, key, self.salt, self.iv)
        decrypted = rho.crypto.decrypt(ciphertext, key, self.salt, self.iv)
        self.assertEquals(plaintext, decrypted)


    def test_encryption_big_key(self):
        plaintext = "hey look at my text $"
        key = """asldhaslkjdhaslkdhliufdygd87gy35kjhnflksjdhfsodjkfhlskhf
                lkasjdhlkajsdhlakshdlkajsdhlakhdlakjsdhalkjsdhalkjsdhlaks
                klajsdhakjsdhlakjsdhalksjdhalkjsdhlkasjhdlkajshdlkajsdhla
                alskdhalksjdlakdhlakjsdhlakjsdhlkajshdlkjasdhlkjafhiouryg
                """
        ciphertext = rho.crypto.encrypt(plaintext, key, self.salt, self.iv)
        decrypted = rho.crypto.decrypt(ciphertext, key, self.salt, self.iv)
        self.assertEquals(plaintext, decrypted)

    def test_decryption_bad_key(self):
        plaintext = "hey look at my text $"
        key = "sekurity is alsome"
        ciphertext = rho.crypto.encrypt(plaintext, key, self.salt, self.iv)
        result = None
        try:
            result = rho.crypto.decrypt(ciphertext, 'badkey', self.salt, self.iv)
        except:
            # now the unpadding method throws a assertion if the ciphertext doesn't
            # decrypt correctly
            pass
        # TODO: Guess we can't really verify if decryption failed:
        #self.assertRaises(rho.crypto.BadKeyException,
        #        rho.crypto.decrypt, ciphertext, 'badkey')
        self.assertNotEqual(plaintext, result)


class FileCryptoTests(unittest.TestCase):

    # NOTE: Not a true unit test, does write a temp file, comment out?
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

    def test_end_to_end_config_encryption(self):
        c = rho.config.Config()
        builder = rho.config.ConfigBuilder()
        text = builder.dump_config(c)

        key = "sekurity!"
        temp_file = '/tmp/rho-crypto-test.txt'
        try:
            rho.crypto.write_file(temp_file, text, key)
            result = rho.crypto.read_file(temp_file, key)
            self.assertEquals(text, result)
        finally:
            try:
                os.remove(temp_file)
            except:
                pass

    def test_bad_file_location(self):
        self.assertRaises(IOError, rho.crypto.write_file,
                "/nosuchdir/nosuchfile.txt", 'blah', 'blah')
        self.assertRaises(rho.crypto.NoSuchFileException, 
                rho.crypto.read_file,
                "/nosuchfile.txt", 'blah')

