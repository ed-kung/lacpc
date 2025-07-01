import os
import sys
import yaml
import numpy as np
import pandas as pd
import Levenshtein

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

MEMBERS = [
    'AMBROZ',
    'CABILDO',
    'CAMPBELL',
    'CHOE',
    'DAKE WILSON',
    'DIAZ',
    'GOLD',
    'HORNSTOCK',
    'KHORSAND',
    'KLEIN',
    'LAWSHE',
    'LEUNG',
    'LOPEZ-LEDESMA',
    'MACK',
    'MILLMAN',
    'MITCHELL',
    'NEWHOUSE',
    'NOONAN',
    'PADILLA-CAMPOS',
    'PERLMAN',
    'RELAN',
    'SAITMAN',
    'ZAMORA',
    'NONE',
    'N/A'
]

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

def clean_member_name(x, max_distance=4):
    best_dist = 1000
    best_match = x
    for member in MEMBERS:
        lev = Levenshtein.distance(x.strip().upper(), member)
        if lev < best_dist:
            best_dist = lev
            best_match = member
    if best_dist <= max_distance:
        return best_match
    else:
        return x
    
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


def get_minutes(verbose=True, clean=True, caseinfo=True):
    colmap = {
        'RELATED CASES:': 'related_cases',
        'SUMMARY OF AGENDA ITEM:': 'agenda_item_summary',
        'SUMMARY OF CPC DELIBERATIONS:': 'deliberations_summary',
        'SUMMARY OF CPC MOTION:': 'motion_summary',
        'MOVED:': 'moved',
        'SECONDED:': 'seconded',
        'AYES:': 'ayes',
        'NAYS:': 'nays',
        'ABSTAINED:': 'abstained',
        'RECUSED:': 'recused',
        'ABSENT:': 'absent',
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

    if clean:
        # Clean up the commissioner names
        for col in ['moved', 'seconded', 'ayes', 'nays', 'abstained', 'recused', 'absent']:
            df[f"{col}_count"] = 0
            df[col] = df[col].str.replace('Commissioner', '')
            df[col] = df[col].str.replace('Choe Mitchell', 'Choe, Mitchell')
            df[col] = df[col].str.replace(r'(?<!Dake[-\s])Wilson', 'Dake Wilson', regex=True)
            for idx, row in df.iterrows():
                mylist = [clean_member_name(x.strip()) for x in row[col].split(',')]
                df.loc[idx, col] = ', '.join(mylist)

        # Count the ayes and nays
        df['n_ayes'] = 0
        df['n_nays'] = 0
        df['n_abstained'] = 0
        df['n_recused'] = 0
        df['n_absent'] = 0
        for idx, row in df.iterrows():
            lists = {}
            for col in ['moved', 'seconded', 'ayes', 'nays', 'abstained', 'recused', 'absent']:
                lists[col] = []
                for x in row[col].split(','):
                    if (x.strip() in MEMBERS) and (x.strip() not in ['NONE', 'N/A']):
                        lists[col].append(x.strip())
            df.loc[idx, 'n_ayes'] = len(set(lists['moved']).union(set(lists['seconded'])).union(set(lists['ayes'])))
            df.loc[idx, 'n_nays'] = len(set(lists['nays']))
            df.loc[idx, 'n_abstained'] = len(set(lists['abstained']))
            df.loc[idx, 'n_recused'] = len(set(lists['recused']))
            df.loc[idx, 'n_absent'] = len(set(lists['absent']))
    
    return df

def get_cases(verbose=True, clean=True):
    df = pd.read_pickle(os.path.join(LOCAL_PATH, "intermediate_data/cpc/case-data.pkl"))
    if clean:
        df['filing_date'] = pd.to_datetime(df['filingDt'], errors='coerce')
        
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
    
    
    

