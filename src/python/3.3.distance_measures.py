# Diagnostic of mahalanobis stability
# All clusters should have condition numbers in the 20–30 range
# All clusters should have minimum eigenvalues in the ~1e-3 range or be invertible


import numpy as np
from collections import defaultdict
import csv

import yaml, os


with open("../../config.local.yaml", 'r') as f:
    local_config = yaml.safe_load(f)

LOCAL_PATH = local_config['LOCAL_PATH']

input_path = os.path.join(LOCAL_PATH, 'intermediate_data/cpc')


working_file1 = 'working_file1.csv'

vectors_by_cluster = defaultdict(list)

with open(f'{input_path}/{working_file1}', 'r') as g:
    reader = csv.reader(g)
    next(reader)  # skip header
    for row in reader:
        cluster = int(row[1])
        vec = [float(x) for x in row[2:12]]
        vectors_by_cluster[cluster].append(vec)

for clus, vecs in vectors_by_cluster.items():
    X = np.array(vecs, dtype=float)
    cov = np.cov(X, rowvar=False)
    cond_number = np.linalg.cond(cov)
    eigvals = np.linalg.eigvals(cov)
    print(f"Cluster {clus}: n={len(X)}, cond={cond_number:.2e}, min_eig={eigvals.min():.2e}")