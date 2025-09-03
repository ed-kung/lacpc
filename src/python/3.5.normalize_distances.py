# calculate z-score for each distance measures, by cluster


import csv
import statistics

input_path = '/Users/hal9004/Library/Mobile Documents/com~apple~CloudDocs/research/projects/cityplanning/data/analysis5'
working_file = 'working_file.csv'

clusters = set()
with open(f'{input_path}/{working_file}', 'r') as g:
    reader1 = csv.reader(g, delimiter=',')
    next(reader1)
    for row in reader1:
        clusters.add(row[24])


data = []


# build headings
with open(f'{input_path}/{working_file}', 'r') as g:
    reader1 = csv.reader(g, delimiter=',')
    data1 = list(reader1)
    for i, row in enumerate(data1):
        if i == 0:
            # header row: extend with new column(s) from data2 (excluding key)
            data.append(row + ['euclid_zscore', 'cosine_zscore', 'manhattan_zscore'])
            break


# calculate cluster specific statistics
for cluster in clusters:
    cluster_data = []
    with open(f'{input_path}/{working_file}', 'r') as g:
        reader1 = csv.reader(g, delimiter=',')
        next(reader1)
        for row in reader1:
            if row[24] == cluster:
                cluster_data.append(row)
    

    # euclidean
    e_mean_val = statistics.mean(float(row[25]) for row in cluster_data)
    e_sd_val = statistics.pstdev(float(row[25]) for row in cluster_data)

    # cosine
    c_mean_val = statistics.mean(float(row[26]) for row in cluster_data)
    c_sd_val = statistics.pstdev(float(row[26]) for row in cluster_data)

    # manhattan
    m_mean_val = statistics.mean(float(row[27]) for row in cluster_data)
    m_sd_val = statistics.pstdev(float(row[27]) for row in cluster_data)

    # append z-scores
    for row in cluster_data:
        row1 = []
        row1.extend(row)
        row1.append(((float(row[25]) - e_mean_val) / e_sd_val)) # euclid z-score
        row1.append(((float(row[26]) - c_mean_val) / c_sd_val)) # cosine z-score
        row1.append(((float(row[27]) - m_mean_val) / m_sd_val)) # manhattan z-score
        data.append(row1)


# save output
with open(f'{input_path}/{working_file}', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerows(data)






        
