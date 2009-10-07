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

# From the python-crypto package
from Crypto.Cipher import Blowfish

def pad(plaintext):
    """
    Pad the given plaintext such that it's length is a multiple of 8 bytes.

    Padding bytes will be equal to the number of padding bytes that are 
    required. (i.e. if the string requires 2 padding bytes, those two bytes
    will have the value of 0x02)

    For more information on why this is done: 
        http://www.di-mgt.com.au/cryptopad.html
    """

    # Only works on strings, need to throw exception if for instance we get a unicode
    if type(plaintext) != type(''):
        raise Exception("Can only pad strings.")

    return_me = plaintext
    if len(return_me) % 8 != 0:
        padding_needed = 8 - (len(return_me) % 8)
        return_me = return_me + str(padding_needed) * padding_needed

    return return_me

def unpad(plaintext):
    """
    Remove any padding present on this decrypted string.

    There is a known problem here, where if the original string did not 
    require padding, but ended with a string like "7777777" or "333", we 
    cannot tell if that string is padded or was like that to begin with.
    In this method we have to assume it's padded and chop them off, but this
    is basically a non-issue as we'll only ever be encrypting/decrypting XML
    or JSON here, which will never end with integer sequences.
    """

    # Only works on strings, need to throw exception if for instance we get a unicode
    if type(plaintext) != type(''):
        raise Exception("Can only pad strings.")

    if len(plaintext) % 8 != 0:
        raise Exception("String length not a multiple of 8")

    return_me = plaintext

    if plaintext[-1] in ['1', '2', '3', '4', '5', '6', '7']:
        # Indicates there could be padding involved:
        chop_count = int(plaintext[-1])
        chopped_bytes = plaintext[-chop_count]
        # If this is padding, all bytes chopped should equal the count:
        all_bytes_match = True
        for c in chopped_bytes:
            if c != plaintext[-1]:
                all_bytes_match = False
                break

        if all_bytes_match:
            chop_to = len(plaintext) - chop_count
            return_me = plaintext[0:chop_to]

        return return_me

def encrypt(plaintext, key):
    """
    Encrypt the plaintext using the given key. 

    Uses the Blowfish algorithm. Plaintext will be padded if required.
    """
    obj = Blowfish.new(key, Blowfish.MODE_CBC)

    plaintext = pad(plaintext)
    ciphertext = obj.encrypt(plaintext)
    return ciphertext

def decrypt(ciphertext, key):
    """
    Decrypt the ciphertext with the given key. 
    
    Uses the Blowfish algorithm. Padding bytes (if present) will be removed.
    """
    obj = Blowfish.new(key, Blowfish.MODE_CBC)
    decrypted_plaintext = obj.decrypt(ciphertext)
    return_me = unpad(decrypted_plaintext)
    return return_me
