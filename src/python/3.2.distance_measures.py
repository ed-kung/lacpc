# calculate mahalnobis stability
# first need to calculate covariances to normalize with
# second need to weight distance by relevant covariances
# output as working_file3

import csv
import numpy as np
from collections import defaultdict
from pathlib import Path



input_path = '/Users/hal9004/Library/Mobile Documents/com~apple~CloudDocs/research/projects/cityplanning/data/analysis5'
working_file1 = 'working_file1.csv'
working_file3 = 'working_file3.csv'


# Pass1: Gather vectors by cluster to estimate covariance
vectors_by_cluster = defaultdict(list)

with open(f'{input_path}/{working_file1}', 'r', newline='', encoding='utf-8') as g:
    reader = csv.reader(g)
    next(reader)  # skip header
    for row in reader:
        cluster = int(row[1])
        vec = [float(x) for x in row[2:12]]  # 10 dims
        vectors_by_cluster[cluster].append(vec)

# Build a pooled/global inverse covariance (fallback)
all_vecs = np.vstack([np.asarray(v, dtype=float) for v in vectors_by_cluster.values()])
global_cov = np.cov(all_vecs, rowvar=False)
global_cov += 1e-6 * np.eye(global_cov.shape[0])      # small ridge
global_VI = np.linalg.pinv(global_cov)                # stable pseudo-inverse

# Inverse covariance per cluster (regularized if needed)
inv_cov_by_cluster = {}
for clus, vecs in vectors_by_cluster.items():
    X = np.asarray(vecs, dtype=float)
    if X.shape[0] >= 2:  # at least 2 samples needed
        cov = np.cov(X, rowvar=False)
        cov += 1e-6 * np.eye(cov.shape[0])           # regularize
        VI = np.linalg.pinv(cov)
    else:
        VI = global_VI                                # fallback if tiny cluster
    inv_cov_by_cluster[clus] = VI

# Pass 2: compute Mahalanobis and write output

with open(f'{input_path}/{working_file1}', 'r', newline='', encoding='utf-8') as g, open(f'{input_path}/{working_file3}', 'w', newline='', encoding='utf-8') as f:

    reader = csv.reader(g)
    next(reader)  # skip header

    writer = csv.writer(f)
    writer.writerow(['dateitem_no', 'mahalanobis'])

    for row in reader:
        key = row[0]
        cluster = int(row[1])

        vector = np.array(row[2:12], dtype=float)     # 10 dims
        centroid = np.array(row[12:22], dtype=float)  # 10 dims

        delta = vector - centroid
        VI = inv_cov_by_cluster.get(cluster, global_VI)

        # Mahalanobis distance: sqrt( delta^T * VI * delta )
        maha = float(np.sqrt(delta @ VI @ delta))

        writer.writerow([key, maha])
