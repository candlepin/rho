#!/usr/bin/python

import sys
from rho import crypto

content = crypto.read_file('rho.conf', sys.argv[1])
print(content)
