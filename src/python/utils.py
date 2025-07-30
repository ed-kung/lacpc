import hashlib
import re

# Get the hash of a string
def get_hash(text):
    return hashlib.md5(text.encode()).hexdigest()

# Check if a string is a valid planning department case number
def is_casenum(s):
    pattern = r'^[A-Za-z]{2,3}-\d+-[A-Za-z0-9-]+$'
    return bool(re.match(pattern, s))

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