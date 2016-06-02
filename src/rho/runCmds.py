#!/usr/bin/python

import sys
import subprocess as sp
import json
import gettext
t = gettext.translation('rho', 'locale', fallback=True)
_ = t.ugettext

sys.path.insert(0, '/home/kbattula/devel/rho2/src/rho')
import rho_cmds




allCommands = rho_cmds.DEFAULT_CMDS

infoDict = {} #stores the values of every command string run on the shell

def executeCommands():
    #Goes through all the default commands and executes them in the local machine.

    for rho_cmd in allCommands:
        output = []
        for cmd_string in rho_cmd.cmd_strings:
            process = sp.Popen(cmd_string,shell=True,stdout=sp.PIPE,stderr=sp.PIPE)
            out,err = process.communicate()
            errCode = process.returncode
            output.append((out, err))
        print rho_cmd
        print output
        rho_cmd.populate_data(output)
        infoDict.update(rho_cmd.data)


executeCommands()
print json.dumps(infoDict,ensure_ascii=False)






#
# def main():
#     module = AnsibleModule(
#         argument_spec=dict(
#             user=dict(required=True, type='str'),
#             key=dict(required=True, type='str'),
#             path=dict(required=False, type='str'),
#             manage_dir=dict(required=False, type='bool', default=True),
#             state=dict(default='present', choices=['absent', 'present']),
#             key_options=dict(required=False, type='str'),
#             unique=dict(default=False, type='bool'),
#             exclusive=dict(default=False, type='bool'),
#             validate_certs=dict(default=True, type='bool'),
#         ),
#         supports_check_mode=True
#     )
#
#     results = enforce_state(module, module.params)
#     module.exit_json(**results)
#
# # import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.urls import *
# main()




