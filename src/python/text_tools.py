import os
import numpy as np
import pandas as pd
import yaml
import time
import re

with open('../../config.yaml', 'r') as f:
    config = yaml.safe_load(f)

"""
Check if a string is a valid planning department case number
"""
def is_casenum(s):
    pattern = r'^[A-Za-z]{2,3}-\d+-[A-Za-z0-9-]+$'
    return bool(re.match(pattern, s))

    
"""
Tools for finding parents, siblings, and descendants of a text

Assumes data is a dataframe indexed by id and has the following columns:
- parent_id
- sibling_left_id
- sibling_right_id
- first_child_id
- text_order
"""
def get_parents(id, data):
    parent_id = data.loc[id,'parent_id']
    if parent_id == '':
        return []
    parents = get_parents(parent_id, data)
    return parents + [parent_id]

def get_siblings_left(id, data):
    sibling_left_id = data.loc[id,'sibling_left_id']
    if sibling_left_id == '':
        return []
    siblings_left = get_siblings_left(sibling_left_id, data)
    return siblings_left + [sibling_left_id]

def get_siblings_right(id, data):
    sibling_right_id = data.loc[id,'sibling_right_id']
    if sibling_right_id == '':
        return []
    siblings_right = get_siblings_right(sibling_right_id, data)
    return [sibling_right_id] + siblings_right

def get_descendants(id, data):
    first_child_id = data.loc[id,'first_child_id']
    if first_child_id == '':
        return []
    children = [first_child_id] + get_siblings_right(first_child_id, data)
    descendants = []
    for child in children:
        descendants = descendants + [child]
        descendants = descendants + get_descendants(child, data)
    return descendants

def get_descendants_and_right_siblings(id, data):
    descendants = get_descendants(id, data)
    out_ids = descendants
    sibling_right_id = data.loc[id, 'sibling_right_id']
    if sibling_right_id == '':
        return out_ids
    else:
        out_ids = out_ids + [sibling_right_id] + get_descendants_and_right_siblings(sibling_right_id, data)
        return out_ids

def get_vertical_chain(id, data):
    parents = get_parents(id, data)
    descendants = get_descendants(id, data)
    return parents + [id] + descendants

def get_vertical_chain_with_siblings(id, data):
    parents = get_parents(id, data)
    descendants_and_right_siblings = get_descendants_and_right_siblings(id, data)
    return parents + [id] + descendants_and_right_siblings

def get_all_vertical_text(ids, data):
    all_ids = set()
    for id in ids:
        all_ids = all_ids.union(set(get_vertical_chain(id,data)))
    all_ids = list(all_ids)
    out = ''
    for idx, row in data.loc[all_ids].sort_values(by='text_order',ascending=True).iterrows():
        level = row['item_level']
        indent = '  '*(level+2)
        out+= indent + row['text'] + '\n'
    return out

def get_text_from_ids(ids, data):
    all_ids = list(set(ids))
    out = ''
    for idx, row in data.loc[all_ids].sort_values(by='text_order',ascending=True).iterrows():
        level = row['item_level']
        indent = '  '*(level+2)
        out+= indent + row['text'] + '\n'
    return out
        
    

        