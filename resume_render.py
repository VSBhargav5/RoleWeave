"""Render only explicitly selected reviewed claims; no rewriting or inference."""
import html
import re
from document_locale import checked_locale, label
from resume_theme import validate_theme
from io import BytesIO
from pathlib import Path

from career_profile import SECTIONS, validate_profile
from career_entries import fact_text, fact_heading, entry_lines
from document_locale import month

try:
    import reportlab
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, HRFlowable
    PDF_AVAILABLE = True
except ModuleNotFoundError:
    PDF_AVAILABLE = False

MAX_RESUME_BYTES = 8 * 1024 * 1024
THEMES = {"jake": {"accent": "#000000", "name_size": 24, "body_size": 10.5},
          "jake2": {"accent": "#000000", "name_size": 24, "body_size": 10.5},
          "classic": {"accent": "#334d66", "name_size": 21, "body_size": 10},
          "slate": {"accent": "#175b63", "name_size": 24, "body_size": 10},
          "editorial": {"accent": "#593b73", "name_size": 26, "body_size": 10}}


def checked_theme(theme):
    if isinstance(theme,dict):return validate_theme(theme)
    if not isinstance(theme, str) or theme not in THEMES:
        raise ValueError("Choose Jake-inspired, Classic, Slate or Editorial layout")
    return THEMES[theme]



def selected_facts(profile, identifiers):
    validate_profile(profile)
    if not isinstance(identifiers, list) or not identifiers or any(not isinstance(value, str) for value in identifiers):
        raise ValueError("Select at least one reviewed fact")
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Select each fact only once")
    facts = {fact["id"]: fact for fact in profile["facts"]}
    if any(identifier not in facts or not facts[identifier]["reviewed"] for identifier in identifiers):
        raise ValueError("Only existing reviewed facts can be used in a resume")
    return [facts[identifier] for identifier in identifiers]


def fact_groups(facts,locale="en"):
    groups=[]
    for section in SECTIONS:
        section_groups={}
        for fact in facts:
            if fact['section']==section:section_groups.setdefault(fact_heading(fact,locale),[]).append(fact)
        groups.extend(section_groups.items())
    return groups


def resume_text(profile, identifiers, locale="en", theme=None):
    checked_locale(locale)
    facts = selected_facts(profile, identifiers)
    if theme=='jake2':
        lines=[profile['name'],profile['headline'],' | '.join(profile[k] for k in ('email','phone','location') if profile[k]),profile['links'],'',flow_text(profile['summary'],identifiers)]
        for section,items in fact_groups(facts,locale):
            lines.extend(['',section])
            for fact in items:
                entry=entry_layout(fact,locale,True,identifiers)
                lines.extend([entry['title'],entry['period'],entry['organization'],entry['location'],*('- '+v for v in entry['bullets']),*entry['notes']] if entry else flow_blocks(fact_text(fact,locale=locale),identifiers))
        return '\n'.join(lines)
    lines = [profile["name"], profile["headline"],
             " | ".join(profile[key] for key in ("email", "phone", "location") if profile[key]),
             profile["links"], "", profile["summary"]]
    for section,items in fact_groups(facts,locale):
        lines.extend(["", section, *("- " + fact_text(fact,locale=locale) for fact in items)])
    return "\n".join(lines)


# Jake-inspired layout: https://github.com/jakegut/resume (original rendering code).
def flow_text(value, identifiers=()):
    # These are internal citation markers, not candidate wording. Other bracketed
    # content is preserved, including technical expressions and project names.
    value=re.sub(r'\[([^\[\]\n]{1,300})\]',lambda m:'' if all(v.strip() in identifiers for v in m[1].split(',')) else m[0],value)
    return ' '.join(value.split())


def flow_blocks(value, identifiers=()):
    blocks=[];current=[]
    for line in value.splitlines():
        line=line.strip()
        if not line:continue
        new=bool(re.match(r'^(?:[-•●]\s+|[A-Za-z][A-Za-z /&+()-]{1,65}:)',line) or (' | ' in line and len(line)<200))
        if new and current:blocks.append(flow_text(' '.join(current),identifiers));current=[]
        current.append(re.sub(r'^[-•●]\s+','',line))
    if current:blocks.append(flow_text(' '.join(current),identifiers))
    return blocks


def entry_layout(fact, locale, refined=False, identifiers=()):
    """Separate structured headings from printable wording without dropping fields."""
    fields=fact.get('details',{}).get('fields')
    if not fields:return None
    lines=entry_lines(fact,locale=locale)  # Validate before using typed fields.
    period=' - '.join(month(v,locale) if v!='Present' else label('Present',locale)
                      for v in (fields.get('started',''),'Present' if fields.get('current') else fields.get('ended','')) if v)
    skipped=1+bool(period)+bool(fields.get('location'))+bool(fields.get('about'))
    wording=[fields.get('about',''),fact['claim']]
    bullets=[]
    for value in wording:
        if refined:
            # Strip a model-repeated heading only when every field and both
            # dates agree with this structured entry. Never infer changed dates.
            heading=[fields['title'],fields.get('organization',''),fields.get('location','')]
            parts=value.split('|',3)
            if len(parts)==4 and all(v and parts[i].strip().casefold()==v.casefold() for i,v in enumerate(heading)):
                start=fields.get('started','');end='present' if fields.get('current') else fields.get('ended','')
                if start and end:
                    pattern=r'^\s*'+re.escape(start)+r'\s*(?:to|[-–—])\s*'+re.escape(end)+r'\s*(?:[—–]|-\s|:\s)\s*'
                    remaining,count=re.subn(pattern,'',parts[3],count=1,flags=re.I)
                    if count:value=remaining
        # PDF imports retain visual line wraps. Only explicit bullet markers split claims.
        segments=re.split(r'(?:^|\n)\s*[-•●]\s*|[•●]\s*',value)
        if refined:segments=[part for segment in segments for part in re.split(r';\s+(?=(?i:optimized|delivered|built|designed|validated|extended)\b)',segment)]
        bullets.extend((flow_text(part,identifiers) if refined else ' '.join(part.split())) for part in segments if part.strip())
    return {'title':fields['title'],'organization':fields.get('organization',''),
            'period':period,'location':fields.get('location',''),'bullets':bullets,'notes':lines[skipped:]}


def resume_html(profile, identifiers, theme="classic", locale="en"):
    checked_locale(locale)
    palette = checked_theme(theme)
    custom=isinstance(theme,dict)
    custom_css=''
    if theme in ('jake','jake2'):
        custom_css='@page{size:Letter;margin:12.7mm}body{font:10.5pt/1.15 Georgia,"Times New Roman",serif;color:#000;max-width:190.5mm}h1{text-align:center;font-size:24pt;color:#000}.headline,.contact{text-align:center;color:#000;font-size:10pt}h2{font-variant:small-caps;font-size:12pt;color:#000;border-bottom:1px solid #000;padding-bottom:2px;margin:12px 0 5px}.entry-heading,.entry-subheading{display:flex;justify-content:space-between;gap:12px;margin:3px 0}.entry-heading span:last-child,.entry-subheading span:last-child{text-align:right}.entry-subheading{font-style:italic}ul{margin:4px 0 7px;padding-left:18px}li{margin:2px 0}.entry-note{font-size:10pt;margin:3px 0 7px}'
    if theme=='jake2':custom_css+='body{font-family:Times New Roman,serif}.entry-note{line-height:1.2}'
    if custom:
        family='Georgia,Times New Roman,serif' if palette['font']=='serif' else 'Arial,sans-serif'
        width=(215.9 if palette['page']=='Letter' else 210)-2*palette['margin_mm']
        custom_css='@page{size:'+palette['page']+';margin:'+str(palette['margin_mm'])+'mm}body{font:'+str(palette['body_size'])+'pt/1.4 '+family+';max-width:'+str(width)+'mm}h1{font-size:'+str(palette['name_size'])+'pt}'
    facts = selected_facts(profile, identifiers)
    def escaped(value):
        return html.escape(value, quote=True).replace("\n", "<br>")
    contact = " | ".join(profile[key] for key in ("email", "phone", "location") if profile[key])
    parts = ['<!doctype html><html lang="'+locale+'"><head><meta charset="utf-8">',
             '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
             '<title>' + escaped(profile["name"]) + ' - '+escaped(label('Resume',locale))+'</title>',
             '<style>@page{size:A4;margin:18mm}*{box-sizing:border-box}body{font:11pt/1.45 Arial,sans-serif;color:#17212b;margin:0 auto;max-width:180mm;padding:24px}',
             'h1{font-size:23pt;margin:0 0 4px}h2{font-size:12pt;border-bottom:1px solid #ccd4dc;padding-bottom:4px;margin-top:20px;break-after:avoid}',
             '.headline{font-size:13pt;color:#334d66}.contact{font-size:10pt;color:#334155}p{margin:7px 0}li{margin:6px 0;overflow-wrap:anywhere}',
             '.screen-only{background:#eef3f8;padding:10px;font:10pt Arial;margin-bottom:20px}@media print{body{padding:0}.screen-only{display:none}}',
             ('' if theme == 'classic' else 'h1{font-size:'+str(palette['name_size']+2)+'pt;color:'+palette['accent']+'}h2{color:'+palette['accent']+';border-bottom:2px solid '+palette['accent']+'}.headline{color:'+palette['accent']+'}') +custom_css+
             '</style></head><body><aside class="screen-only">Review this document before use. Print with your browser menu or Ctrl+P. No external resources are loaded.</aside>',
             '<main><h1>' + escaped(profile["name"]) + '</h1>']
    if profile["headline"]:
        parts.append('<p class="headline">' + escaped(profile["headline"]) + '</p>')
    if contact:
        parts.append('<p class="contact">' + escaped(contact) + '</p>')
    if profile["links"]:
        parts.append('<p class="contact">' + escaped(profile["links"]) + '</p>')
    if profile["summary"]:
        parts.append('<h2>'+escaped(label('Summary',locale))+'</h2><p>' + escaped(flow_text(profile['summary'],identifiers) if theme=='jake2' else profile["summary"]) + '</p>')
    for section,items in fact_groups(facts,locale):
        if theme in ('jake','jake2'):
            parts.append('<section><h2>'+escaped(section)+'</h2>')
            for fact in items:
                entry=entry_layout(fact,locale,theme=='jake2',identifiers)
                if entry:
                    parts.append('<div class="entry-heading"><strong>'+escaped(entry['title'])+'</strong><span>'+escaped(entry['period'])+'</span></div>')
                    parts.append('<div class="entry-subheading"><span>'+escaped(entry['organization'])+'</span><span>'+escaped(entry['location'])+'</span></div>')
                    if entry['bullets']:parts.append('<ul>'+''.join('<li>'+escaped(v)+'</li>' for v in entry['bullets'])+'</ul>')
                    parts.extend('<p class="entry-note">'+escaped(v)+'</p>' for v in entry['notes'])
                elif theme=='jake2':parts.extend('<p class="entry-note">'+escaped(v)+'</p>' for v in flow_blocks(fact_text(fact,locale=locale),identifiers))
                else:parts.append('<ul><li>'+escaped(fact_text(fact,locale=locale))+'</li></ul>')
            parts.append('</section>')
            continue
        parts.append('<section><h2>' + escaped(section) + '</h2><ul>')
        parts.extend('<li>' + escaped(fact_text(fact,locale=locale)) + '</li>' for fact in items)
        parts.append('</ul></section>')
    parts.append('</main></body></html>')
    payload = "\n".join(parts).encode("utf-8")
    if len(payload) > MAX_RESUME_BYTES:
        raise ValueError("Resume HTML exceeds 8 MiB")
    return payload


def resume_pdf(profile, identifiers, theme="classic", locale="en"):
    checked_locale(locale)
    palette = checked_theme(theme)
    if not PDF_AVAILABLE:
        raise ValueError("PDF support is missing. Run Setup-RoleWeave.cmd or choose HTML-only.")
    facts = selected_facts(profile, identifiers)
    prepare_pdf_fonts(resume_text(profile, identifiers,locale)+label("Summary",locale)+label("Resume",locale))
    body = ParagraphStyle("Body", fontName="RoleWeaveVera", fontSize=10, leading=14, spaceAfter=6, alignment=TA_LEFT)
    name_style = ParagraphStyle("Name", parent=body, fontName="RoleWeaveVeraBold", fontSize=21, leading=26, spaceAfter=4)
    headline = ParagraphStyle("Headline", parent=body, fontSize=12, leading=16, textColor=colors.HexColor("#334d66"))
    contact_style = ParagraphStyle("Contact", parent=body, fontSize=9, leading=13, textColor=colors.HexColor("#334155"))
    section_style = ParagraphStyle("Section", parent=body, fontName="RoleWeaveVeraBold", fontSize=11, leading=15,
                                   spaceBefore=10, spaceAfter=6, keepWithNext=True)
    bullet = ParagraphStyle("Claim", parent=body, leftIndent=9, firstLineIndent=-9)
    if theme != "classic":
        name_style.fontSize = palette["name_size"]
        name_style.leading = palette["name_size"] + 5
        name_style.textColor = colors.HexColor(palette["accent"])
        headline.textColor = colors.HexColor(palette["accent"])
        section_style.textColor = colors.HexColor(palette["accent"])
    custom=isinstance(theme,dict)
    page_size=letter if custom and palette['page']=='Letter' else A4
    margin=palette['margin_mm'] if custom else 18
    if theme in ('jake','jake2'):
        page_size=letter; margin=12.7
        try:resume_text(profile,identifiers,locale).encode('cp1252');normal,bold='Times-Roman','Times-Bold'
        except UnicodeEncodeError:normal,bold='RoleWeaveVera','RoleWeaveVeraBold'
        for style in (body,bullet,headline,contact_style):style.fontName=normal;style.textColor=colors.black
        for style in (name_style,section_style):style.fontName=bold;style.textColor=colors.black
        for style in (body,bullet):style.fontSize=10.5;style.leading=12;style.spaceAfter=3
        for style in (headline,contact_style):style.fontSize=10;style.leading=11.5;style.spaceAfter=3;style.alignment=TA_CENTER
        name_style.alignment=TA_CENTER;name_style.leading=27;name_style.spaceAfter=4
        section_style.fontSize=12;section_style.leading=14;section_style.spaceBefore=8;section_style.spaceAfter=2
    if custom:
        if palette['font']=='serif':
            try:resume_text(profile,identifiers,locale).encode('cp1252')
            except UnicodeEncodeError:raise ValueError('Serif PDF font supports Windows-1252 text only; choose Sans for this content') from None
        normal='Times-Roman' if palette['font']=='serif' else 'RoleWeaveVera'
        bold='Times-Bold' if palette['font']=='serif' else 'RoleWeaveVeraBold'
        for style in (body,bullet):style.fontName=normal;style.fontSize=palette['body_size'];style.leading=palette['body_size']*1.4
        for style in (headline,contact_style):style.fontName=normal
        for style in (name_style,section_style):style.fontName=bold
    def paragraph(value, style):
        return Paragraph(html.escape(value).replace("\n", "<br/>"), style)
    def section_rule():
        rule=HRFlowable(width='100%',thickness=.5,color=colors.black,spaceAfter=4)
        rule.keepWithNext=True
        return rule
    story = [paragraph(profile["name"], name_style)]
    if profile["headline"]:
        story.append(paragraph(profile["headline"], headline))
    contact = " | ".join(profile[key] for key in ("email", "phone", "location") if profile[key])
    if contact:
        story.append(paragraph(contact, contact_style))
    if profile["links"]:
        story.append(paragraph(profile["links"], contact_style))
    story.append(Spacer(1, 4))
    if profile["summary"]:
        story.append(paragraph(label("Summary",locale), section_style))
        if theme in ('jake','jake2'):story.append(section_rule())
        story.append(paragraph(flow_text(profile['summary'],identifiers) if theme=='jake2' else profile["summary"], body))
    for section,items in fact_groups(facts,locale):
        story.append(paragraph(section, section_style))
        if theme in ('jake','jake2'):
            story.append(section_rule())
            title_style=ParagraphStyle('Entry title',parent=body,fontName=bold,keepWithNext=True)
            right_style=ParagraphStyle('Entry date',parent=body,alignment=TA_RIGHT)
            # SimpleDocTemplate's frame reserves six points of padding per side.
            width=page_size[0]-2*margin*mm-(12 if theme=='jake2' else 0)
            for fact in items:
                entry=entry_layout(fact,locale,theme=='jake2',identifiers)
                if not entry:
                    if theme=='jake2':story.extend(paragraph(v,body) for v in flow_blocks(fact_text(fact,locale=locale),identifiers))
                    else:story.append(paragraph('- '+fact_text(fact,locale=locale),bullet))
                    continue
                rows=[[paragraph(entry['title'],title_style),paragraph(entry['period'],right_style)]]
                if entry['organization'] or entry['location']:rows.append([paragraph(entry['organization'],body),paragraph(entry['location'],right_style)])
                heading=Table(rows,colWidths=[width*.72,width*.28],hAlign='LEFT')
                heading.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0 if theme=='jake2' else 3),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),1)]))
                heading.keepWithNext=True;story.append(heading)
                story.extend(paragraph(('- ' if theme=='jake2' else '• ')+v,bullet) for v in entry['bullets'])
                story.extend(paragraph(v,body) for v in entry['notes'])
                story.append(Spacer(1,4))
            continue
        story.extend(paragraph("- " + fact_text(fact,locale=locale), bullet) for fact in items)
    def footer(canvas, document):
        if theme in ('jake','jake2'):return
        canvas.saveState()
        canvas.setFont("RoleWeaveVera", 8)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawRightString(page_size[0] - margin * mm, 10 * mm, str(document.page))
        canvas.restoreState()
    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=page_size, leftMargin=margin * mm, rightMargin=margin * mm,
                                 topMargin=(margin if custom or theme in ('jake','jake2') else 17) * mm, bottomMargin=margin * mm, title=profile["name"] + " - " + label("Resume",locale),
                                 author=profile["name"], subject=label("Resume",locale), pageCompression=1, invariant=1)
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    payload = output.getvalue()
    if len(payload) > MAX_RESUME_BYTES:
        raise ValueError("Resume PDF exceeds 8 MiB")
    return payload


def prepare_pdf_fonts(content):
    if not PDF_AVAILABLE:
        raise ValueError("PDF support is missing. Install the runtime requirements.")
    fonts = Path(reportlab.__file__).parent / "fonts"
    for name, file in (("RoleWeaveVera", "Vera.ttf"), ("RoleWeaveVeraBold", "VeraBd.ttf")):
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(fonts / file)))
    characters = set(content) - set("\n\r\t")
    missing = [char for char in characters if ord(char) not in pdfmetrics.getFont("RoleWeaveVera").face.charToGlyph]
    if missing:
        points = ", ".join(f"U+{ord(char):04X}" for char in sorted(missing)[:8])
        raise ValueError(f"Bundled PDF font cannot render {points}. Save an HTML-only version and print it from your browser.")
    pdfmetrics.registerFontFamily("RoleWeaveVera", normal="RoleWeaveVera", bold="RoleWeaveVeraBold")
