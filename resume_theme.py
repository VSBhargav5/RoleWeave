"""Portable, bounded document styling data; no CSS, URLs, scripts or font files."""
import json
import re
from career_profile import unique_json

DEFAULT={'format':'roleweave-resume-theme-v1','accent':'#334d66','body_size':10,'name_size':24,'font':'sans','margin_mm':18,'page':'A4'}


def validate_theme(theme):
    if not isinstance(theme,dict) or set(theme)!=set(DEFAULT) or theme.get('format')!=DEFAULT['format']:
        raise ValueError('Use a supported resume theme with no extra fields')
    if not isinstance(theme['accent'],str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',theme['accent']):raise ValueError('Use a six-digit hex accent color')
    channels=[int(theme['accent'][n:n+2],16)/255 for n in (1,3,5)]
    linear=[v/12.92 if v<=0.04045 else ((v+0.055)/1.055)**2.4 for v in channels]
    luminance=sum(a*b for a,b in zip(linear,(0.2126,0.7152,0.0722)))
    if 1.05/(luminance+0.05)<4.5:raise ValueError('Choose a darker accent: at least4.5:1 contrast against white paper')
    for name,low,high in (('body_size',9,12),('name_size',18,30),('margin_mm',14,24)):
        if type(theme[name]) is not int or not low<=theme[name]<=high:raise ValueError(name+' is outside supported integer bounds')
    if theme['font'] not in ('sans','serif') or theme['page'] not in ('A4','Letter'):raise ValueError('Choose a bundled font and A4 or Letter paper')
    return dict(theme)


def parse_theme(payload):
    if not isinstance(payload,bytes) or len(payload)>2048:raise ValueError('Theme JSON exceeds2KiB')
    try:theme=json.loads(payload,object_pairs_hook=unique_json)
    except (UnicodeError,ValueError,TypeError,RecursionError):raise ValueError('Invalid theme JSON') from None
    return validate_theme(theme)


def theme_bytes(theme):
    return json.dumps(validate_theme(theme),sort_keys=True,indent=2).encode()
