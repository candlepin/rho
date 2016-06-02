from rho import rho_cmds


import gettext
t = gettext.translation('rho', 'locale', fallback=True)
_ = t.ugettext

allCommands = rho_cmds.DEFAULT_CMDS

infoDict = {}

def executeCommands():
    #Goes through all the default commands and executes them in the local machine. Probably done using threads running in parallel on the machine

    for rho_cmd in allCommands:
        output = []
        for cmd_string in rho_cmd.cmd_strings:
            stdin, stdout, stderr = self.ssh.exec_command(cmd_string)
            output.append((stdout.read(), stderr.read()))
        rho_cmd.populate_data(output)

        #can probably remove the data field and store everything in a dictionary instead.





def main():
    module = AnsibleModule(
        argument_spec=dict(
            user=dict(required=True, type='str'),
            key=dict(required=True, type='str'),
            path=dict(required=False, type='str'),
            manage_dir=dict(required=False, type='bool', default=True),
            state=dict(default='present', choices=['absent', 'present']),
            key_options=dict(required=False, type='str'),
            unique=dict(default=False, type='bool'),
            exclusive=dict(default=False, type='bool'),
            validate_certs=dict(default=True, type='bool'),
        ),
        supports_check_mode=True
    )

    results = enforce_state(module, module.params)
    module.exit_json(**results)

# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.urls import *
main()




