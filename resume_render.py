"""Render only explicitly selected reviewed claims; no rewriting or inference."""
import html
from io import BytesIO
from pathlib import Path

from career_profile import SECTIONS, validate_profile

try:
    import reportlab
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    PDF_AVAILABLE = True
except ModuleNotFoundError:
    PDF_AVAILABLE = False

MAX_RESUME_BYTES = 8 * 1024 * 1024
THEMES = {"classic": {"accent": "#334d66", "name_size": 21, "body_size": 10},
          "slate": {"accent": "#175b63", "name_size": 24, "body_size": 10},
          "editorial": {"accent": "#593b73", "name_size": 26, "body_size": 10}}


def checked_theme(theme):
    if not isinstance(theme, str) or theme not in THEMES:
        raise ValueError("Choose Classic, Slate or Editorial layout")
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


def resume_text(profile, identifiers):
    facts = selected_facts(profile, identifiers)
    lines = [profile["name"], profile["headline"],
             " | ".join(profile[key] for key in ("email", "phone", "location") if profile[key]),
             profile["links"], "", profile["summary"]]
    for section in SECTIONS:
        items = [fact["claim"] for fact in facts if fact["section"] == section]
        if items:
            lines.extend(["", section, *("- " + claim for claim in items)])
    return "\n".join(lines)


def resume_html(profile, identifiers, theme="classic"):
    palette = checked_theme(theme)
    facts = selected_facts(profile, identifiers)
    def escaped(value):
        return html.escape(value, quote=True).replace("\n", "<br>")
    contact = " | ".join(profile[key] for key in ("email", "phone", "location") if profile[key])
    parts = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
             '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
             '<title>' + escaped(profile["name"]) + ' - Resume</title>',
             '<style>@page{size:A4;margin:18mm}*{box-sizing:border-box}body{font:11pt/1.45 Arial,sans-serif;color:#17212b;margin:0 auto;max-width:180mm;padding:24px}',
             'h1{font-size:23pt;margin:0 0 4px}h2{font-size:12pt;border-bottom:1px solid #ccd4dc;padding-bottom:4px;margin-top:20px;break-after:avoid}',
             '.headline{font-size:13pt;color:#334d66}.contact{font-size:10pt;color:#334155}p{margin:7px 0}li{margin:6px 0;overflow-wrap:anywhere}',
             '.screen-only{background:#eef3f8;padding:10px;font:10pt Arial;margin-bottom:20px}@media print{body{padding:0}.screen-only{display:none}}',
             ('' if theme == 'classic' else 'h1{font-size:'+str(palette['name_size']+2)+'pt;color:'+palette['accent']+'}h2{color:'+palette['accent']+';border-bottom:2px solid '+palette['accent']+'}.headline{color:'+palette['accent']+'}') +
             '</style></head><body><aside class="screen-only">Review this document before use. Print with your browser menu or Ctrl+P. No external resources are loaded.</aside>',
             '<main><h1>' + escaped(profile["name"]) + '</h1>']
    if profile["headline"]:
        parts.append('<p class="headline">' + escaped(profile["headline"]) + '</p>')
    if contact:
        parts.append('<p class="contact">' + escaped(contact) + '</p>')
    if profile["links"]:
        parts.append('<p class="contact">' + escaped(profile["links"]) + '</p>')
    if profile["summary"]:
        parts.append('<h2>Summary</h2><p>' + escaped(profile["summary"]) + '</p>')
    for section in SECTIONS:
        items = [fact for fact in facts if fact["section"] == section]
        if items:
            parts.append('<section><h2>' + section + '</h2><ul>')
            parts.extend('<li>' + escaped(fact["claim"]) + '</li>' for fact in items)
            parts.append('</ul></section>')
    parts.append('</main></body></html>')
    payload = "\n".join(parts).encode("utf-8")
    if len(payload) > MAX_RESUME_BYTES:
        raise ValueError("Resume HTML exceeds 8 MiB")
    return payload


def resume_pdf(profile, identifiers, theme="classic"):
    palette = checked_theme(theme)
    if not PDF_AVAILABLE:
        raise ValueError("PDF support is missing. Run Setup-RoleWeave.cmd or choose HTML-only.")
    facts = selected_facts(profile, identifiers)
    prepare_pdf_fonts(resume_text(profile, identifiers))
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
    def paragraph(value, style):
        return Paragraph(html.escape(value).replace("\n", "<br/>"), style)
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
        story.extend([paragraph("Summary", section_style), paragraph(profile["summary"], body)])
    for section in SECTIONS:
        items = [fact for fact in facts if fact["section"] == section]
        if items:
            story.append(paragraph(section, section_style))
            story.extend(paragraph("- " + fact["claim"], bullet) for fact in items)
    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("RoleWeaveVera", 8)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, str(document.page))
        canvas.restoreState()
    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                                 topMargin=17 * mm, bottomMargin=18 * mm, title=profile["name"] + " - Resume",
                                 author=profile["name"], subject="Resume", pageCompression=1, invariant=1)
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
