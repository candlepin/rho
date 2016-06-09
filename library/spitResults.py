import csv
import ast


class Results(object):

    def __init__(self, module):
        self.module = module
        self.vals = module.params['vals']
        self.token = module.params['token']

    def writeToCSV(self):
        f = open("report.csv", "a")
        vals = ast.literal_eval(self.vals)
        token = ast.literal_eval(self.token)
        fields = vals.keys()
        writer = csv.DictWriter(f, fieldnames=fields)
        if token == 0:
            writer.writeheader()
            return
        writer.writerow(vals)


from ansible.module_utils.basic import *

def main():
    module = AnsibleModule(argument_spec=dict(name=dict(required=True), vals=dict(required=True),
                                              token=dict(required=True)))
    results = Results(module=module)
    results.writeToCSV()
    response = {"written": "yes"}
    module.exit_json(changed=False,meta = response)

if __name__ == '__main__':
    main()






