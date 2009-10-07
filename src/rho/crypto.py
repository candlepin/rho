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

def encrypt(plaintext, key):
    """
    Encrypt the plaintext using the given key. 

    Currently using the Blowfish algorithm. The plaintext will be padded if 
    required.
    """
    pass
