import numpy as np
import pandas as pd

def parse_casenum(casenum, raw=True):
    tokens = casenum.split('-')
    parsed = {'prefix':'', 'year':'', 'canonical_casenum':'', 'suffixes':[]}
    
    prefix = tokens[0]
    
    parsed['prefix'] = prefix
    
    if len(tokens)>1:
        token1 = tokens[1]
        if pd.to_numeric(token1, errors='coerce')<=2022:
            parsed['year'] = tokens[1]

        if len(tokens)<=2:
            parsed['canonical_casenum'] = '-'.join(tokens)
        else:
            parsed['canonical_casenum'] = '-'.join(tokens[0:3])
            parsed['suffixes'] = tokens[3:]

        return parsed
    else:
        parsed['canonical_casenum'] = tokens[0]
    
    return parsed

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

    # Fix a council district
    if sheet==1:
        idx = df['Case Number']=='DIR-2018-1190-SPP'
        df.loc[idx, 'Council District'] = 1
    elif sheet==0:
        idx = df['Case Number']=='CPC-2017-839-GPA-VZC-ZAD'
        df.loc[idx, 'Council District'] = 13
        idx = df['Case Number']=='DIR-2016-4984-DRB-SPP-MSP'
        df.loc[idx, 'Council District'] = 4
        idx = df['Case Number']=='DIR-2018-1190-SPP'
        df.loc[idx, 'Council District'] = 1
        idx = df['Case Number']=='ZA-2015-305-CUB-SPP'
        df.loc[idx, 'Council District'] = 13
    
    df['Council District'] = pd.to_numeric(df['Council District'], errors='coerce')
    assert df['Council District'].isna().sum()==0

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

