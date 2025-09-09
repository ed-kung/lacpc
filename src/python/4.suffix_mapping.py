import csv
import os
import yaml


# set paths 

with open("../../config.local.yaml", 'r') as f:
    local_config = yaml.safe_load(f)
LOCAL_PATH = local_config['LOCAL_PATH']
input_path = os.path.join(LOCAL_PATH, 'intermediate_data/cpc')
working_file = 'working_file.csv'
input_file = 'sfx_mapping.csv'


data1 = []
with open(f'{input_path}/{working_file}', 'r') as g:
    reader1 = csv.reader(g, delimiter=',')
    data1 = list(reader1)

data2 = []
with open(f'{input_path}/{input_file}', 'r') as g:
    reader2 = csv.reader(g, delimiter=',')
    data2 = list(reader2)


# Extend working file with suffixes
lookup = {row[0]: row[1:] for row in data2[1:]}

data3 = []
for i, row in enumerate(data1):
    if i == 0:
        # header row: extend with new column(s) from data2 (excluding key)
        data3.append(row + data2[0][1:])
    else:
        key = row[0]  # dateitem_no
        if key in lookup:
            row_extended = row + lookup[key]
        else:
            row_extended = row
        data3.append(row_extended)


# save output
with open(f'{input_path}/{working_file}', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerows(data3)
