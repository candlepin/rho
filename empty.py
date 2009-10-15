#!/usr/bin/python

import sys
from rho import crypto

f = open('rho-plain.conf', 'r')
content = f.read()
f.close()
crypto.write_file('rho.conf', content, sys.argv[1])
