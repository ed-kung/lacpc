import hashlib
import re
import json
import numpy as np

# Get the hash of a string
def get_hash(text):
    return hashlib.md5(text.encode()).hexdigest()

# Check if a string is a valid planning department case number
def is_casenum(s):
    pattern = r'^[A-Za-z]{2,3}-\d+-[A-Za-z0-9-]+$'
    return bool(re.match(pattern, s))

# p-value stars
def stars(coef, serr):
    if serr == 0:
        return '***'  # Avoid division by zero; treat as highly significant
    t_stat = np.abs(coef / serr)
    if t_stat > 2.576:
        return '***'  # p < 0.01
    elif t_stat > 1.96:
        return '**'   # p < 0.05
    elif t_stat > 1.645:
        return '*'    # p < 0.10
    else:
        return ''
    
# Handle strings with json in them
def extract_json(s):
    # Try directly
    try:
        return json.loads(s)
    except:
        pass
    
    # Try by getting the last ```json ``` block
    matches = re.findall(r"```json\s*(.*?)\s*```", s, re.DOTALL)
    if matches:
        try:
            parsed = json.loads(matches[-1])
            return parsed
        except:
            pass

    # Try by getting the first { } block
    start = s.index('{')
    end = s.rindex('}') + 1
    try:
        parsed = json.loads(s[start:end])
        return parsed
    except:
        pass

    print("No JSON found.")
    return None

# Canonicalize a case number
def canonicalize_casenum(caseno):
    case_parts = caseno.split('-')
    if case_parts[0]=='VTT':
        case_parts = case_parts[0:2]
        case_parts[1] = case_parts[1].lstrip('0')
        return '-'.join(case_parts)
    else:
        case_parts = case_parts[0:3]
        case_parts[2] = case_parts[2].lstrip('0')
        return '-'.join(case_parts)

# Parse case number into its components
def parse_casenum(caseno):
    if not is_casenum(caseno):
        raise ValueError(f"Invalid case number format: {caseno}")
    
    canonical_casenum = canonicalize_casenum(caseno)

    prefix = canonical_casenum.split('-')[0]
    suffixes = caseno[len(canonical_casenum):].split('-')[1:]

    return {
        'casenum': caseno, 
        'canonical_casenum': canonical_casenum,
        'prefix': prefix,
        'suffixes': suffixes
    }