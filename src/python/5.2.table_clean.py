# Clean up marginal effects table for .tex input

import csv
import pandas as pd
import re
import yaml
import os
import sys
import numpy as np

# set paths 
with open("../../config.local.yaml", 'r') as f:
    local_config = yaml.safe_load(f)
LOCAL_PATH = local_config['LOCAL_PATH']

sys.path.append(os.path.join(LOCAL_PATH, 'src/python'))

import writing_tools as wt

input_path = os.path.join(LOCAL_PATH, 'intermediate_data/cpc')
working_file = 'ologit.marginal_effects.mahalanobis.csv' # esttab export
output_file = 'ologit_marginal_effects.tex' 
output_path = os.path.join(LOCAL_PATH, 'tables')

def split_csv_line(line):
    parts = next(csv.reader([line]))
    cleaned = []
    for p in parts:
        p = p.strip()
        if p.startswith('="') and p.endswith('"'):
            p = p[2:-1]
        elif p == '=""':
            p = ""
        p = p.strip('"')
        cleaned.append(p)
    return cleaned

def get_row(varname):
    key = varname.lower().strip()
    for v, coef, se in data_rows:
        if v.lower().strip() == key:
            coef = (coef + [''] * n_models)[:n_models]
            se   = (se   + [''] * n_models)[:n_models]
            return coef, se
    return [''] * n_models, [''] * n_models

def add_var(label, key):
    coef, se = get_row(key)
    out.append([label] + coef)
    out.append([""] + se)
    out.append([""] * (n_models + 1))


# --- Load raw CSV ---
raw_lines = open(f'{input_path}/{working_file}', 'r', encoding='utf-8', errors='ignore').read().splitlines()
rows = [split_csv_line(l) for l in raw_lines if l.strip()]

# --- Find header row with (1), (2), ... ---
header_row = next(r for r in rows if any(cell.strip() == '(1)' for cell in r))
start_idx = header_row.index('(1)')

model_headers = []
for cell in header_row[start_idx:]:
    if re.fullmatch(r'\(\d+\)', cell.strip()):
        model_headers.append(cell.strip())
    else:
        break
n_models = len(model_headers)

# --- Parse into (name, coefs, ses) ---
data_rows = []
i = rows.index(header_row) + 2  # skip dependent variable row
while i < len(rows):
    r = rows[i]
    if not r:
        i += 1
        continue

    name = (r[0] if len(r) > 0 else '').strip()
    padded = r + [''] * (start_idx + n_models - len(r))
    coefs  = padded[start_idx : start_idx + n_models]

    se = [''] * n_models
    if i + 1 < len(rows):
        r2 = rows[i+1]
        if len(r2) > start_idx and any(str(c).strip().startswith('(') for c in r2[start_idx:]):
            r2pad = r2 + [''] * (start_idx + n_models - len(r2))
            se = r2pad[start_idx : start_idx + n_models]
            i += 1

    data_rows.append((name, coefs, se))
    i += 1


# --- Build cleaned table ---
out = []

# second header row (blank + outcome labels)
# second header row (blank + outcome labels)
label_row = rows[rows.index(header_row) + 1]
outcome_labels = []
for cell in label_row[start_idx : start_idx + n_models]:
    cleaned = re.sub(r'^\s*ME:\s*', '', cell).strip()   # remove "ME:" prefix
    cleaned = re.sub(r'\s+', ' ', cleaned)              # collapse multiple spaces
    # capitalize the word "Outcome" (first word) and keep the number as-is
    if cleaned.lower().startswith("outcome"):
        parts = cleaned.split()
        cleaned = "Outcome " + (parts[1] if len(parts) > 1 else "")
    outcome_labels.append(cleaned)

out.append([""] + outcome_labels)

# add an extra blank spacer row here
out.append([""] * (n_models + 1))

# example: add key variables (you can customize labels/keys)
add_var("Semantic Uniqueness",    "mahalanobis")
add_var("Agenda Perplexity",      "agenda_perplexity")
add_var("Agenda Order",           "agenda_order")
add_var("No. Agenda Items",       "num_agenda_items")
add_var("Consent Calendar",       "consent_calendar")
add_var("$\log_2$(\# Support)",   "n__support")
add_var("$\log_2$(\# Oppose)",    "n__oppose")

out.append(["Semantic Cluster FE","Y","Y","Y"][:n_models+1]); out.append([""]*(n_models+1))
out.append(["Council District FE","Y","Y","Y"][:n_models+1]); out.append([""]*(n_models+1))
out.append(["Suffix Group FE","Y","Y","Y"][:n_models+1]);   out.append([""]*(n_models+1))


# add stats at bottom if present
obs, _ = get_row("Obs")
out.append(["No. of Obs"] + obs)


# DataFrame → LaTeX (tabular-only)
colnames = [""] + model_headers
clean = pd.DataFrame(out, columns=colnames)

with open(f"{output_path}/{output_file}", "w") as f:
    f.write(clean.to_latex(
        index=False,
        escape=False,
        na_rep="",
        column_format="l" + "c"*n_models   # 1 label col + centered model cols
    ))

# Update results.json and results.tex
results = {}

x = float(get_row('mahalanobis')[0][0].replace('*',''))
x = f"{np.abs(x)*100:.1f}\\%"
results['SemUniME2'] = x

x = float(get_row('mahalanobis')[0][1].replace('*',''))
x = f"{np.abs(x)*100:.1f}\\%"
results['SemUniME1'] = x

x = float(get_row('mahalanobis')[0][2].replace('*',''))
x = f"{np.abs(x)*100:.1f}\\%"
results['SemUniME0'] = x

x = float(get_row('consent_calendar')[0][0].replace('*',''))
x = f"{np.abs(x)*100:.1f}\\%"
results['ConCalME2'] = x

x = float(get_row('consent_calendar')[0][1].replace('*',''))
x = f"{np.abs(x)*100:.1f}\\%"
results['ConCalME1'] = x

x = float(get_row('consent_calendar')[0][2].replace('*',''))
x = f"{np.abs(x)*100:.1f}\\%"
results['ConCalME0'] = x

x = float(get_row('n__oppose')[0][0].replace('*',''))
x = f"{np.abs(x)*100:.1f}\\%"
results['NOppME2'] = x

x = float(get_row('n__oppose')[0][1].replace('*',''))
x = f"{np.abs(x)*100:.1f}\\%"
results['NOppME1'] = x

x = float(get_row('n__oppose')[0][2].replace('*',''))
x = f"{np.abs(x)*100:.1f}\\%"
results['NOppME0'] = x

wt.update_results(results)
