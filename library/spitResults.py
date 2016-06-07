import csv


class Results(object):

    def __init__(self,module):
        self.module = module
        self.vals = module.params['vals']

    def writeToCSV(self):
        f = open("report", "wb")
        vals = self.vals
        print vals
        fields = vals[vals.keys()[0]].keys()
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for k in vals.keys():
            writer.write(vals[k])


from ansible.module_utils.basic import *

def main():
    module = AnsibleModule(argument_spec=dict(name=dict(required=True),vals = dict(required = True)))
    results = Results(module=module)
    results.writeToCSV()
    response = {"written": "yes"}
    module.exit_json(changed=False,meta = response)

if __name__ == '__main__':
    main()






