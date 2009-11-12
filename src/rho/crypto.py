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

""" Configuration Encryption Module """

import os
import os.path
import string

from rho.log import log

# From the python-crypto package
from Crypto.Cipher import  AES

from rho.PBKDF2 import PBKDF2

from config import CONFIG_VERSION

class BadKeyException(Exception):
    pass


class NoSuchFileException(Exception):
    pass


class AESEncrypter(object):
    """
    Simple to use object for AES-128 encryption.

    Based on contribution from Steve Milner.
    """

    def __init__(self, password, salt, iv, key_length=16 ):
        """
        Creates a new instance of AESEncrypter.

        :Parameters:
            - `key`: encryption/decryption key
            - `pad_char`: ASCII character to pad with.
        """
        self.__key_length = key_length
        self.__key = self.__create_key(salt, password)

        if self.__key_length != len(self.__key):
            raise Exception("Key does not match length: %s" %
                    self.__key_length)

        self.__pad_char = " "
        self.__cipher_obj = AES.new(self.__key,AES.MODE_CFB, iv)

    def __create_key(self, salt, password):
        """
        Creates a key to use for encryption using the given password.
        """
        return PBKDF2(password, salt).read(self.__key_length)

    def encrypt(self, data):
        """
        Pads and encrypts the data.

        :Parameters:
           - `data`: pad and data to encrypt.
        """
        data = self.pad(data, self.__cipher_obj.block_size)
        return self.__cipher_obj.encrypt(data)

    def decrypt(self, ciphertext):
        """
        Decrypts data and removes padding.

        :Parameters:
           - `data`: the data to decrypt and removing padding on.
        """
        data = self.__cipher_obj.decrypt(ciphertext)
        if len(data):
            data = self.unpad(data, self.__cipher_obj.block_size)
        return data

    # see http://tools.ietf.org/html/rfc3852#section-6.3
    def pad(self, data, length):
        assert length < 256
        assert length > 0
        padlen = length - len(data) % length
        assert padlen <= length
        assert padlen > 0
        return data + padlen * chr(padlen)

    def unpad(self, data, length):
        assert length < 256
        assert length > 0
        padlen = ord(data[-1])
        assert padlen <= length
        assert padlen > 0
        assert data[-padlen:] == padlen * chr(padlen)
        return data[:-padlen]


    # read-only properties
    pad_char = property(lambda self: self.__pad_char)
    key = property(lambda self: self.__key)
    key_length = property(lambda self: self.__key_length)


def encrypt(plaintext, key, salt, iv):
    """
    Encrypt the plaintext using the given key. 
    """
    encrypter = AESEncrypter(key, salt, iv)

    return encrypter.encrypt(plaintext)


def decrypt(ciphertext, key, salt, iv):
    """
    Decrypt the ciphertext with the given key. 
    """
    encrypter = AESEncrypter(key, salt, iv)
    decrypted_plaintext = encrypter.decrypt(ciphertext)
    return decrypted_plaintext

    # TODO: is there a way to know decryption failed?
    #if return_me is None:
    #    # Looks like decryption failed, probably a bad key:
    #    raise BadKeyException


def write_file(filename, plaintext, key):
    """ 
    Encrypt plaintext with the given key and write to file. 
    
    Existing file will be overwritten so be careful. 
    """
    f = open(filename, 'w')
    salt = os.urandom(8)
    iv = os.urandom(16)
    # a hex version string
    f.write("%2X" % CONFIG_VERSION)
    f.write(salt)
    f.write(iv)
    log.debug("version: %s salt: %s iv: %s" % (CONFIG_VERSION, salt, iv))
    f.write(encrypt(plaintext, key, salt, iv))
    f.close()


def read_file(filename, password):
    """
    Decrypt contents of file with the given key, and return as a string.

    Assume that we're reading files that we encrypted. (i.e. we're not trying
    to read files encrypted manually with gpg)

    Also note that the password here is the user password, not the actual
    AES key. To get that we must read the first 8 bytes of the file to get
    the correct salt to use to convert the password to the key.

    Returns a tuple of (salt, json)
    """
    if not os.path.exists(filename):
        raise NoSuchFileException()

    f = open(filename, 'r')
    # 2 byte version in hex
    ver = f.read(2)
    # 8 byte salt
    salt = f.read(8)
    # 16 byte initialization vector
    iv = f.read(16)
    log.debug("Read version: %s salt: %s  iv: %s" % (ver, salt, iv))

    cont = f.read()
    return_me = decrypt(cont, password, salt, iv)
    f.close()
    return return_me

