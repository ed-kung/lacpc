# combine cluster embeddings and cluster centroid data
# output as working_file1

import csv, time, math

input_path = '/Users/hal9004/Library/Mobile Documents/com~apple~CloudDocs/research/projects/cityplanning/data/analysis5'
input_file1 = 'agenda_item_with_embeddings.25.8.7.csv'
input_file2 = 'cluster_centroids.25.8.7.csv'
working_file = 'working_file1.csv'

# open working file

data1 = []
with open(f'{input_path}/{input_file1}', 'r') as g:
    reader1 = csv.reader(g, delimiter=',')
    for row in reader1:
        row1 = []
        key = str(f'{row[0]}{row[1]}')
        row1.append(key)
        row1.extend(row[4:]) # cluster characteristics
        data1.append(row1)


data2 = []
with open(f'{input_path}/{input_file2}', 'r') as g:
    reader2 = csv.reader(g, delimiter=',')
    data2 = list(reader2)


# match data1 and data2
lookup = {row[0]: row[1:] for row in data2[1:]}

# Extend data1 rows with matching cluster values
result = []
for i, row in enumerate(data1):
    if i == 0:
        # header row: extend with data2 headers (skipping 'cluster')
        new_header = [f"{col}_cluster" for col in data2[0][1:]]
        result.append(row + new_header)
    else:
        cluster = row[1]
        if cluster in lookup:
            row_extended = row + lookup[cluster]
        else:
            row_extended = row  # keep row as-is if no cluster match
        result.append(row_extended)

# write file
with open(f'{input_path}/{working_file}', 'a', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    for row in result:
        writer.writerow(row)