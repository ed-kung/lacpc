import numpy as np
import pandas as pd

def get_la_planning_dept_cases(sheet=1):
    df = pd.read_excel("../../raw_data/LA Business Council Data Request - 20220823.xlsx", sheet_name=sheet)

    # Coerce date vars to date
    for col in [
        'Filed Date', 
        'Case Deemed Complete Date', 
        'DCP Hearing Date', 
        'CPC/APC Hearing Date', 
        'Completion Date'
    ]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # Drop any cases missing project description or requested entitlement
    for col in ['Project Description', 'Requested Entitlement']:
        if col in df.columns:
            df[col] = df[col].fillna('')
            df[col] = df[col].astype('str')
            df[col] = df[col].str.strip()
            idx = df[col].str.len()>0
            df = df.loc[idx]
    df = df.reset_index(drop=True)

    # Create a unified text column inclusive of project description and requested entitlement
    df['text'] = ''
    for idx, row in df.iterrows():
        project_description = row['Project Description']
        requested_entitlement = row['Requested Entitlement']
        df.loc[idx, 'text'] = fr"""Project Description:
{project_description}

Requested Entitlement:
{requested_entitlement}
"""
    return df

