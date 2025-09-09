# open export, build key, drop irrelevant columns
# log base 2 support/oppose
# add council district dummies
# output as working_file.csv

import csv
import math
import yaml
import os


# set paths 

with open("../../config.local.yaml", 'r') as f:
    local_config = yaml.safe_load(f)
LOCAL_PATH = local_config['LOCAL_PATH']
input_path = os.path.join(LOCAL_PATH, 'intermediate_data/cpc')
input_file = 'export-for-joe.25.8.7.csv'
working_file = 'working_file.csv'


# collect data

def status_code(value):
    s = str(value).strip().upper()
    if s == "APPROVED":
        return 2
    if s == "APPROVED IN PART OR WITH MODIFICATIONS":
        return 1
    return 0  # everything else

data = []
with open(f'{input_path}/{input_file}', 'r') as g:
    reader1 = csv.reader(g, delimiter=',')
    data1 = list(reader1)
    for i, row in enumerate(data1):
        if i == 0: # build headings
            row1 = []
            key = str(f'{row[1]}{row[2]}')
            row1.append(key)
            row1.append(row[5]) # council district
            row1.extend(row[7:11]) # agenda characteristics
            row1.append(row[34])
            row1.append(row[35])
            row1.append(row[33])

            data.append(row1)
        
        else:

            row1 = []
            key = str(f'{row[1]}{row[2]}')
            row1.append(key)
            row1.append(row[5]) # council district
            row1.extend(row[7:11]) # agenda characteristics
            try: # take log base 2 of n_support
                row1.append(math.log(int(row[34]), 2))
            except:
                row1.append(row[34])
            try: # take log base 2 of n_oppose
                row1.append(math.log(int(row[35]), 2))
            except:
                row1.append(row[35])

            row1.append(status_code(row[33]))
            
            data.append(row1)


# create council_district co-occurring dummies

council_districts = set()
for datum in data[1:]:
    districts = str(datum[1]).split(',')
    for district in districts:
        council_districts.add(str(district).strip())

council_districts = sorted(list(council_districts))
council_districts = council_districts[:-1]
council_districts1 = []
for district in council_districts: #add text for stata variable 
    districts = f'cd{str(district)}'
    council_districts1.append(districts)

data1 = []
data1.append(data[0].extend(council_districts1))
for datum in data[1:]:
    district_dummies = [0] * len(council_districts1)
    districts = str(datum[1]).split(',')

    if str(datum[1]).strip().upper() == "CITYWIDE":
        district_dummies = [1] * len(council_districts1)  # all ones
    else:
        for district in districts:
            district = district.strip()
            district = f'cd{str(district)}'
            if district in council_districts1:
                idx = council_districts1.index(district)
                district_dummies[idx] = 1
    data1.append(datum.extend(district_dummies))
    

# write file
with open(f'{input_path}/{working_file}', 'a', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    for row in data:
        writer.writerow(row)
