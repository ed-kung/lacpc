# Clean up ologit table for .tex input

import csv
import pandas as pd
import re
import yaml
import os


# set paths 

with open("../../config.local.yaml", 'r') as f:
    local_config = yaml.safe_load(f)
LOCAL_PATH = local_config['LOCAL_PATH']
input_path = os.path.join(LOCAL_PATH, 'intermediate_data/cpc')
working_file = 'ologit.main_effects.mahalanobis.csv' # esttab export
output_file = 'ologit_main_effects.tex' 
output_path = os.path.join(LOCAL_PATH, 'tables')


def split_csv_line(line):
    # esttab often writes fields like ="text"
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
            # ensure lengths
            coef = (coef + [''] * n_models)[:n_models]
            se   = (se   + [''] * n_models)[:n_models]
            return coef, se
    return [''] * n_models, [''] * n_models
def add_var(label, key):
    coef, se = get_row(key)
    out.append([label] + coef)
    out.append([""] + se)
    out.append([""] * (n_models + 1))


raw_lines = open(f'{input_path}/{working_file}', 'r', encoding='utf-8', errors='ignore').read().splitlines()
rows = [split_csv_line(l) for l in raw_lines if l.strip()]


# find the header row 
header_row = next(r for r in rows if any(cell.strip() == '(1)' for cell in r))

start_idx = header_row.index('(1)')


# take all consecutive cells that look like (number)
model_headers = []
for cell in header_row[start_idx:]:
    if re.fullmatch(r'\(\d+\)', cell.strip()):
        model_headers.append(cell.strip())
    else:
        break

n_models = len(model_headers)


# parse into (name, coefs[n], ses[n]) 
data_rows = []
i = rows.index(header_row) + 2  # skip the dependent-var row
while i < len(rows):
    r = rows[i]
    if not r:
        i += 1
        continue

    name = (r[0] if len(r) > 0 else '').strip()

    # pad row to avoid index errors
    padded = r + [''] * (start_idx + n_models - len(r))
    coefs  = padded[start_idx : start_idx + n_models]

    # look-ahead for SE line (parentheses)
    se = [''] * n_models
    if i + 1 < len(rows):
        r2 = rows[i+1]
        if len(r2) > start_idx and any(str(c).strip().startswith('(') for c in r2[start_idx:]):
            r2pad = r2 + [''] * (start_idx + n_models - len(r2))
            se = r2pad[start_idx : start_idx + n_models]
            i += 1

    data_rows.append((name, coefs, se))
    i += 1


# build cleaned table
out = []
# header row (label + model headers)
out.append([""] + [r"\makecell{Project \\ Implication}"] * n_models)
out.append([""] * (n_models + 1))
out.append([""] * (n_models + 1))

# main variables (rename labels to taste)
add_var("Distance",               "mahalanobis")
add_var("Agenda Perplexity",      "agenda_perplexity")
add_var("Agenda Order",           "agenda_order")
add_var("No. Agenda Items",       "num_agenda_items")
add_var("Consent Calendar",       "consent_calendar")
add_var("No. Support",            "n__support")
add_var("No. Oppose",             "n__oppose")


# block rows, esttab renumbers to (1)(2)(3)(4).
# adjust n/y flags to match spec

out.append(["Cluster Effects","n","y","y","y"][:n_models+1]); out.append([""]*(n_models+1))
out.append(["District Effects","n","n","y","y"][:n_models+1]); out.append([""]*(n_models+1))
out.append(["Suffix Effects","n","n","n","y"][:n_models+1]);   out.append([""]*(n_models+1))


# intercepts + stats (names as they appear in CSV)
for label, key in [("Intercept 1","cut1"), ("Intercept 2","cut2")]:
    coef, se = get_row(key)
    out.append([label] + coef)
    out.append([""] + se)
    out.append([""] * (n_models + 1))

obs, _ = get_row("Obs")
r2,  _ = get_row("Pseudo R-squared")
out.append(["No. of Obs"] + obs)
out.append(["Pseudo R2"] + r2)


# DataFrame → LaTeX (tabular-only)
colnames = [""] + model_headers
clean = pd.DataFrame(out, columns=colnames)

with open(f"{output_path}/{output_file}", "w") as f:
    f.write(clean.style.to_latex(
        index=False,
        escape=False,
        na_rep="",
        column_format="l" + "c"*n_models   # 1 label col + centered model cols
    ))