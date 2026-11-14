"""Local, selectable-text PDF for the exact reviewed letter text."""
import html
from io import BytesIO

from resume_render import prepare_pdf_fonts


def letter_pdf(name, text):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    prepare_pdf_fonts(text)
    body = ParagraphStyle("LetterBody", fontName="RoleWeaveVera", fontSize=10.5,
                          leading=16, spaceAfter=6, textColor=colors.HexColor("#17212b"))
    heading = ParagraphStyle("LetterName", parent=body, fontName="RoleWeaveVeraBold",
                             fontSize=22, leading=28, textColor=colors.HexColor("#175b63"))
    story=[]
    for index, line in enumerate(text.splitlines()):
        story.append(Paragraph(html.escape(line), heading if index==0 else body) if line else Spacer(1,6))
    output=BytesIO()
    document=SimpleDocTemplate(output, pagesize=A4, leftMargin=22*mm, rightMargin=22*mm,
                               topMargin=20*mm, bottomMargin=20*mm, title=name+" - Cover letter",
                               author=name, subject="Cover letter", pageCompression=1, invariant=1)
    document.build(story)
    payload=output.getvalue()
    if len(payload)>2*1024*1024:
        raise ValueError("Cover-letter PDF exceeds 2 MiB")
    return payload
