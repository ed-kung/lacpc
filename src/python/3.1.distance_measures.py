# calculate basic distance measures: euclidean, cosine, manhattan
# output as working_file2


import csv
import math
import numpy as np
from scipy.spatial import distance

import yaml, os


with open("../../config.local.yaml", 'r') as f:
    local_config = yaml.safe_load(f)

LOCAL_PATH = local_config['LOCAL_PATH']

input_path = os.path.join(LOCAL_PATH, 'intermediate_data/cpc')


working_file1 = 'working_file1.csv'
working_file2 = 'working_file2.csv'


with open(f'{input_path}/{working_file1}', 'r') as g, open(f'{input_path}/{working_file2}', 'w', newline='', encoding='utf-8') as f:
    reader1 = csv.reader(g, delimiter=',')
    next(reader1)
    writer = csv.writer(f)
    writer.writerow(['dateitem_no', 'cluster', 'euclidean', 'cosine_distance', 'manhattan'])

    for row in reader1:
        
        key = row[0]
        cluster = row[1]
        vector = row[2:12]
        vector = [float(x) for x in vector]
        centroid = row[12:22]
        centroid = [float(x) for x in centroid]
        
        # euclid distance    
        euclidean = math.sqrt(sum((a - b) ** 2 for a, b in zip(vector, centroid)))

        # cosine distance
        vector = np.array(row[1:11], dtype=float)
        centroid = np.array(row[11:21], dtype=float)
        denom = np.linalg.norm(vector) * np.linalg.norm(centroid)
        cosine_distance = 1.0 - (np.dot(vector, centroid) / denom if denom else 0.0)

        # manhattan distance
        manhattan = np.sum(np.abs(vector - centroid))

        writer.writerow([key, cluster, euclidean, cosine_distance, manhattan])




        



