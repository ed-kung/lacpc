import os
import sys
import yaml
import numpy as np
import pandas as pd

with open('../../config.local.yaml', 'r') as f:
    local_config = yaml.safe_load(f)

LOCAL_PATH = local_config['LOCAL_PATH']

PREFIX_MAP = {
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

SUFFIX_MAP = {
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

def get_supplemental_docs(verbose=True, clean=True):
    colmap = {
        'TYPE OF DOCUMENT:': 'doc_type',
        'TYPE OF AUTHOR:': 'author_type',
        'SUMMARY OF DOCUMENT:': 'summary',
        'REFERENCED AGENDA ITEMS:': 'referenced_items',
        'SUPPORT OR OPPOSE:': 'support_or_oppose'
    }

    meetings_df = pd.read_csv(os.path.join(LOCAL_PATH, "intermediate_data/cpc/meetings-manifest.csv"))
    DATES = sorted(list(meetings_df['date']))
    
    df = []
    for date in DATES:
        year = date[0:4]
        PATH = os.path.join(LOCAL_PATH, f"intermediate_data/cpc/{year}/{date}")
        try:
            summ_df = pd.read_pickle(os.path.join(PATH, "supplemental-docs-summaries.pkl"))
            docs_df = pd.read_pickle(os.path.join(PATH, "supplemental-docs.pkl"))
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
        df['author_type'] = df['author_type'].str.replace('JOURNALIST', 'OTHER')
    
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

    meetings_df = pd.read_csv(os.path.join(LOCAL_PATH, "intermediate_data/cpc/meetings-manifest.csv"))
    DATES = sorted(list(meetings_df['date']))
    
    df = []
    for date in DATES:
        year = date[0:4]
        PATH = os.path.join(LOCAL_PATH, f"intermediate_data/cpc/{year}/{date}")
        try:
            minutes_df = pd.read_pickle(os.path.join(PATH, "minutes-summaries.pkl"))
        except:
            if verbose:
                print(f"No data found for {date}")
            continue
    
        for j, jrow in minutes_df.iterrows():
            item_no = jrow['item_no']
            title = jrow['title']
            agenda_content = jrow['agenda_content']
            minutes_content = jrow['minutes_content']
            minutes_start_line = jrow['minutes_start_line']
            minutes_end_line = jrow['minutes_end_line']
            prompt = jrow['prompt']
            response = jrow['response']
            score = jrow['score']

            out_row = {'year': year, 'date': date, 'item_no': item_no, 'title': title, 
                       'agenda_content': agenda_content, 'minutes_content': minutes_content,
                       'minutes_start_line': minutes_start_line, 'minutes_end_line': minutes_end_line,
                       'prompt': prompt, 'response': response, 'score': score}

            # Find the starting indexes for each part of the response
            start_indexes = {}
            for heading, colname in colmap.items():
                start_indexes[heading] = response.find(heading)

            if start_indexes['IMPLICATION FOR PROJECT:']==-1:
                if verbose:
                    print(f"No proper response found for {date}, item_no {item_no}")
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
    return df

def get_cases(verbose=True, clean=True):
    df = pd.read_pickle("../../intermediate_data/cpc/case-data.pkl")
    return df

def get_agenda_items(verbose=True, clean=True):
    meetings_df = pd.read_csv(os.path.join(LOCAL_PATH, "intermediate_data/cpc/meetings-manifest.csv"))
    DATES = sorted(list(meetings_df['date']))
    
    df = []
    for date in DATES:
        year = date[0:4]
        PATH = os.path.join(LOCAL_PATH, f"intermediate_data/cpc/{year}/{date}")
        try:
            agenda_items_df = pd.read_pickle(os.path.join(PATH, "agenda-items.pkl"))
        except:
            if verbose:
                print(f"No data found for {date}")
            continue
        df.append(agenda_items_df)

    df = pd.concat(df)
    return df
    
    
    

