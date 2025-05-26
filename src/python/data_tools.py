import numpy as np
import pandas as pd

prefix_map = {
	'AA': 'AA',      # advisory agency
	'ADM': 'ADM',   # administrative review
	'APCC': 'APC',   # area planning commission
	'APCE': 'APC',
	'APCH': 'APC',
	'APCNV': 'APC',
	'APCS': 'APC',
	'APCSV': 'APC',
	'APCW': 'APC',
	'CPC': 'CPC',    # city planning commission
	'DIR': 'DIR',    # director of planning
	'ENV': 'ENV',    # environmental
	'TT': 'VTT',     # tentative tract
	'VTT': 'VTT',    # vesting tentative tract
	'ZA': 'ZA',      # zoning administration
	'ZAI': 'ZA'      
}

suffix_map = {
	'ADU': 'ADU',     # accessory dwelling units
	'ADUH': 'ADU',    
	'CCMP': 'CCMP',   # certificate of compatability
	'CDO': 'CDO',     # community design overlay district
	'CDP': 'CDP',     # coastal development permit
	'CPIO': 'CPIO',   # community plan implementation overlay
	'CPIOA': 'CPIO',
	'CPIOC': 'CPIO',
	'CPIOE': 'CPIO',
	'CU': 'CU',       # conditional use permits
	'CUB': 'CU',
	'CUE': 'CU',
	'CUW': 'CU',
	'CUX': 'CU',
	'CUZ': 'CU',
	'CWC': 'CWC',     # conforming work contributing elements
	'CWNC': 'CWC',    # conforming work non-contributing elements
	'DB': 'DB',       # density bonus
	'DRB': 'DRB',     # design review board
	'GPA': 'GPA',     # general plan amendment
	'GPAJ': 'GPAJ',   
	'HCA': 'HCA',     # housing crisis act
	'HD': 'HD',       # height district
	'MCUP': 'MCUP',   # master conditional use permit
	'MEL': 'MEL',     # mello act compliance review
	'MSP': 'MSP',     # mulholland specific plan
	'OVR': 'OVR',     # overlay review
	'PHP': 'PHP',     # priority housing project
	'PMLA': 'PMLA',   # parcel map
	'QC': 'QC',       # Q condition clearance
	'RDP': 'RDP',     # redevelopment plan project
	'SL': 'SL',       # small lot subdivision
	'SPP': 'SPP',     # specific plan project permit compliance
	'SPR': 'SPR',     # site plan review
	'TOC': 'TOC',     # transit oriented communities
	'UDU': 'UDU',     # unapproved dwelling unit
	'VZC': 'VZC',     # vesting zone change
	'VZCJ': 'VZCJ',   
	'WDI': 'WDI',     # waiver of dedication and improvements
	'ZAA': 'ZAA',     # line adjustments gt 20% (slight modifications)
	'ZAD': 'ZAD',     # ZA determination
	'ZC': 'ZC',       # zone change
	'ZCJ': 'ZC',
	'ZV': 'ZV',       # zone variance
}

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

    # Drop any cases with a missing filed date
    for col in ['Filed Date']:
        if col in df.columns:
            idx = df[col].notnull()
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

    # attach dummy columns for prefixes and suffixes
    df['case_pfx'] = ''
    for k in prefix_map.keys():
        df[prefix_map[k]] = 0
    for k in suffix_map.keys():
        df[suffix_map[k]] = 0
    for idx, row in df.iterrows():
        casenum = row['Case Number']
        parsed = parse_casenum(casenum)
        pfx = parsed['prefix']
        if pfx in prefix_map.keys():
            df.loc[idx, 'case_pfx'] = prefix_map[pfx]
            df.loc[idx, prefix_map[pfx]] = 1
        for sfx in parsed['suffixes']:
            if sfx in suffix_map.keys():
                df.loc[idx, suffix_map[sfx]] = 1
    
    return df

def get_supplemental_docs(verbose=True, clean=True):
    colmap = {
        'TYPE OF DOCUMENT:': 'doc_type',
        'TYPE OF AUTHOR:': 'author_type',
        'SUMMARY OF DOCUMENT:': 'summary',
        'REFERENCED AGENDA ITEMS:': 'referenced_items',
        'SUPPORT OR OPPOSE:': 'support_or_oppose'
    }

    meta_df = pd.read_csv("../../intermediate_data/cpc/meetings_metadata.csv")
    df = []
    for i, irow in meta_df.iterrows():
        date = irow['date']
        year = irow['year']
        try:
            summ_df = pd.read_pickle(f"../../intermediate_data/cpc/{year}/{date}/supplemental-docs-summaries.pkl")
            docs_df = pd.read_pickle(f"../../intermediate_data/cpc/{year}/{date}/supplemental-docs.pkl")
            summ_df = summ_df.merge(docs_df[['doc_id','content']], how='left', on='doc_id')
        except:
            if verbose:
                print(f"No data found for {date}")
            continue
        for j, jrow in summ_df.iterrows():
            doc_id = jrow['doc_id']
            start_page = jrow['start_page']
            end_page = jrow['end_page']
            prompt = jrow['prompt']
            response = jrow['response']
            content = jrow['content']
            score = jrow['score']

            out_row = {'year': year, 'date': date, 'doc_id': doc_id, 
                       'start_page': start_page, 'end_page': end_page,
                       'content': content, 'prompt': prompt,
                       'response': response, 'score': score}

            # Find the starting indexes for each part of the response
            start_indexes = {}
            for heading, colname in colmap.items():
                start_indexes[heading] = response.find(heading)

            if start_indexes['SUPPORT OR OPPOSE:']==-1:
                if verbose:
                    print(f"No proper response found for {date}, doc_id {doc_id}, pages {start_page}-{end_page}")
                    print(f"Content: {content}")
                    print("")
                continue

            for k in range(len(colmap)):
                heading = list(colmap.keys())[k]
                colname = colmap[heading]
                start_index = start_indexes[heading] + len(heading)
                if heading=='SUPPORT OR OPPOSE:':
                    end_index = len(response)
                else:
                    heading2 = list(colmap.keys())[k+1]
                    end_index = start_indexes[heading2]
                text = response[start_index:end_index].strip()
                out_row[colname] = text

            df.append(out_row)
            
    df = pd.DataFrame.from_dict(df)

    if clean:
        for idx, row in df.iterrows():
            doc_type = row['doc_type'].lower()
            if doc_type.startwith('the submitted document is a letter'):
                doc_type = 'letter'
            elif doc_type.startswith('other'):
                doc_type = 'other'
            elif doc_type.startswith('procedural matter'):
                doc_type = 'procedural_matter'
    
    return df


def get_minutes(verbose=True, clean=True):
    colmap = {
        'RELATED CASES:': 'related_cases',
        'SUMMARY OF AGENDA ITEM:': 'agenda_item_summary',
        'SUMMARY OF CPC DELIBERATIONS:': 'deliberations_summary',
        'SUMMARY OF CPC MOTION:': 'motion_summary',
        'VOTES FOR:': 'votes_for',
        'VOTES AGAINST:': 'votes_against',
        'VOTES ABSENT:': 'votes_absent',
        'VOTE RESULT:': 'vote_result',
        'RESULT OF APPEAL:': 'appeal_result',
        'IMPLICATION FOR PROJECT:': 'project_result'
    }

    meta_df = pd.read_csv("../../intermediate_data/cpc/meetings_metadata.csv")
    df = []
    for i, irow in meta_df.iterrows():
        date = irow['date']
        year = irow['year']
        try:
            minutes_df = pd.read_pickle(f"../../intermediate_data/cpc/{year}/{date}/minutes-summaries.pkl")
        except:
            if verbose:
                print(f"No data found for {date}")
            continue
    
        for j, jrow in minutes_df.iterrows():
            item_no = jrow['item_no']
            title = jrow['title']
            prompt = jrow['prompt']
            response = jrow['response']
            score = jrow['score']

            out_row = {'year': year, 'date': date, 'item_no': item_no,
                       'title': title, 'prompt': prompt, 'response': response,
                       'score': score}

            # Find the starting indexes for each part of the response
            start_indexes = {}
            for heading, colname in colmap.items():
                start_indexes[heading] = response.find(heading)

            if start_indexes['IMPLICATION FOR PROJECT:']==-1:
                if verbose:
                    print(f"No proper response found for {date}, item_no {item_no}")
                    print(f"Response: {response}")
                    print("")
                continue

            for k in range(len(colmap)):
                heading = list(colmap.keys())[k]
                colname = colmap[heading]
                start_index = start_indexes[heading] + len(heading)
                if heading=='IMPLICATION FOR PROJECT:':
                    end_index = len(response)
                else:
                    heading2 = list(colmap.keys())[k+1]
                    end_index = start_indexes[heading2]
                text = response[start_index:end_index].strip()
                out_row[colname] = text

            df.append(out_row)
            
    df = pd.DataFrame.from_dict(df)

    if clean:
        for idx, row in df.iterrows():
            appeal_result = row['appeal_result']
            if appeal_result=="NO APPEAL, DELIBERATIONS CONTINUED TO FUTURE DATE":
                df.loc[idx, 'appeal_result'] = "NO APPEAL"

            vote_result = row['vote_result']
            if vote_result=="DELIBERATIONS CONTINUED TO FUTURE DATE":
                df.loc[idx, 'vote_result'] = "N/A"
            if vote_result=="MOTION FAILED (initial motion), MOTION PASSED (second motion)":
                df.loc[idx, 'vote_result'] = "MOTION PASSED"
                df.loc[idx, 'votes_for'] = "Millman, Zamora, Cabildo, Lawshe, Leung"
                df.loc[idx, 'votes_against'] = ""
    return df




