"""Source-preserving resume organization suggestions, separate from text extraction."""
import re
import hashlib

from career_profile import SECTIONS

HEADINGS = {
    'Experience': ('experience', 'work experience', 'professional experience', 'employment', 'employment history', 'internships'),
    'Projects': ('projects', 'personal projects', 'academic projects', 'selected projects', 'key projects'),
    'Education': ('education', 'academic background', 'academic qualifications'),
    'Skills': ('skills', 'technical skills', 'technical expertise', 'core competencies', 'skills and tools', 'technologies'),
    'Certifications': ('certifications', 'certificates', 'licenses and certifications', 'courses and certifications'),
    'Volunteering': ('volunteering', 'volunteer experience', 'leadership and volunteering'),
    'Languages': ('languages', 'language skills'), 'Publications': ('publications', 'research publications'),
    'References': ('references',), 'Additional': ('achievements', 'awards', 'interests', 'additional information'),
    'summary': ('summary', 'professional summary', 'profile', 'career objective', 'objective', 'about me'),
}
LOOKUP = {label: section for section, labels in HEADINGS.items() for label in labels}
EMAIL = re.compile(r'[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,}')
URL = re.compile(r'https://[^\s<>|]+')


def normalized(value):
    return re.sub(r'\s+', ' ', value.strip().strip('#*_ :–—-').casefold())


def make_groups(blocks, assignments):
    """Resolve proposed IDs to original text; never accept rewritten model claims."""
    source = {b['id']: b for b in blocks}
    seen, groups = set(), []
    if not isinstance(assignments, list) or len(assignments) > 500:
        raise ValueError('Resume organization exceeds its group limit')
    order = {b['id']: i for i, b in enumerate(blocks)}
    for row in assignments:
        if not isinstance(row, dict) or set(row) != {'section', 'block_ids'} or row['section'] not in SECTIONS:
            raise ValueError('Unsupported suggested resume section')
        ids = row['block_ids']
        if (not isinstance(ids, list) or not ids or any(not isinstance(i, str) or i not in source for i in ids)
                or len(set(ids)) != len(ids) or seen.intersection(ids)):
            raise ValueError('Resume grouping must use distinct original text blocks')
        if ids != sorted(ids, key=order.get):
            raise ValueError('Keep resume excerpts in their original reading order')
        value = '\n'.join(source[i]['text'] for i in ids)
        if len(value) > 10000:
            raise ValueError('Suggested resume entry exceeds 10000 characters; split it into smaller entries')
        seen.update(ids)
        group_id = 'group:' + ids[0] + ':' + ids[-1] + ':' + hashlib.sha256(':'.join(ids).encode()).hexdigest()[:16]
        groups.append({'id': ids[0] if len(ids) == 1 else group_id,
                       'text': value, 'block_ids': ids, 'section': row['section']})
    return groups


def suggest_structure(result):
    blocks = result['blocks']
    assignments, fields, omitted, pending, summary = [], [], [], [], []
    section = 'Additional'
    def flush():
        if pending:
            assignments.append({'section': section, 'block_ids': list(pending)})
            pending.clear()
    def field(name, value, ids):
        if value and len(value) <= (6000 if name == 'summary' else 2000):
            fields.append({'id': 'field:' + name + ':' + ':'.join(ids), 'field': name, 'value': value, 'block_ids': ids})
    # Preserve paragraph boundaries when the extractor supplied them.
    blank_before, previous_blank, index = set(), False, 0
    for line in result['text'].splitlines():
        if not line.strip():
            previous_blank = True
        else:
            if previous_blank and index < len(blocks):
                blank_before.add(blocks[index]['id'])
            previous_blank = False
            index += 1
    for index, block in enumerate(blocks):
        value, identifier = block['text'], block['id']
        label = normalized(value)
        heading = LOOKUP.get(label)
        inline_heading = re.match(r'^([^:]{2,40}):\s*\S', value)
        inline_section = LOOKUP.get(normalized(inline_heading[1])) if inline_heading else None
        if heading:
            flush()
            section = heading
            omitted.append({'id': identifier, 'reason': 'Section heading'})
            continue
        if re.fullmatch(r'(?:page\s+)?\d{1,2}(?:\s+(?:of|/)\s+\d{1,2})?', label):
            omitted.append({'id': identifier, 'reason': 'Possible page number; inspect original text'})
            continue
        if index < 15 and section == 'Additional':
            emails, links = EMAIL.findall(value), URL.findall(value)
            phone = re.search(r'(?<!\w)(?:\+\d{1,3}[ .()-]*)?(?:\(?\d{2,4}\)?[ .-]*){2,5}\d{2,4}(?!\w)', value)
            contacts = bool(emails or links or (phone and 7 <= sum(c.isdigit() for c in phone[0]) <= 15))
            if contacts:
                flush()
                for email in emails: field('email', email, [identifier])
                for link in links: field('linkedin' if 'linkedin.com/' in link.lower() else 'website', link.rstrip('.,;'), [identifier])
                if phone and 7 <= sum(c.isdigit() for c in phone[0]) <= 15: field('phone', phone[0], [identifier])
                omitted.append({'id': identifier, 'reason': 'Contact information; review separately'})
                continue
            if index == 0 and 2 <= len(value.split()) <= 5 and len(value) <= 70 and not value.endswith('.') and all(c.isalpha() or c in " .'-" for c in value) and not any(w in label for w in ('resume', 'curriculum', 'engineer', 'developer')):
                field('name', value, [identifier])
                omitted.append({'id': identifier, 'reason': 'Possible name; review separately'})
                continue
        if section == 'summary':
            summary.append(block)
            continue
        if inline_section:
            flush()
            section = inline_section
            if section == 'summary':
                summary.append(block)
                continue
        bullet = bool(re.match(r'^[•●▪*\-–]\s*\S', value))
        previous = blocks[index - 1]['text'] if index else ''
        new_entry = (identifier in blank_before or
                     (section in ('Experience', 'Education', 'Projects') and not bullet
                      and re.search(r'\b(?:19|20)\d{2}\b|\s\|\s', value)
                      and re.match(r'^[•●▪*\-–]', previous)))
        # Unclassified lines stay individually selectable, rather than an opaque blob.
        if pending and (section == 'Additional' or new_entry or sum(len(b['text']) for b in blocks if b['id'] in pending) + len(value) > 4000):
            flush()
        pending.append(identifier)
    flush()
    if summary:
        field('summary', '\n'.join(b['text'] for b in summary), [b['id'] for b in summary])
    return {'groups': make_groups(blocks, assignments), 'profile_suggestions': fields, 'omitted': omitted,
            'method': 'local', 'notice': 'Suggested organization only. Check reading order, sections and contact fields against your original resume.'}
