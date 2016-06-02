import csv
import ast
import os
import json
from ansible.module_utils.basic import AnsibleModule


class Results(object):
    # The class Results contains the functionality
    # to parse data passed in from the playbook
    # and to output it in the csv format in the
    # file path specified.

    def __init__(self, module):
        self.module = module
        self.name = module.params['name']
        self.file_path = module.params['file_path']
        self.vals = module.params['vals']

    def write_to_csv(self):
        f_path = self.file_path
        f = open(f_path, "a")
        file_size = os.path.getsize(f_path)
        vals = ast.literal_eval(self.vals)
        fields = vals[0].keys()
        fields.sort()
        writer = csv.writer(f, delimiter=',', quotechar='|')
        if file_size == 0:
            writer.writerow(fields)
        for d in vals:
            sorted_keys = d.keys()
            sorted_keys.sort()
            sorted_values = []
            for k in sorted_keys:
                sorted_values.append(d[k])
            writer.writerow(sorted_values)


def main():
    module = AnsibleModule(argument_spec=dict(name=dict(required=True),
                                              file_path=dict(required=True),
                                              vals=dict(required=True)))
    results = Results(module=module)
    results.write_to_csv()
    vals = json.dumps(results.vals)
    module.exit_json(changed=False, meta=vals)

if __name__ == '__main__':
    main()
