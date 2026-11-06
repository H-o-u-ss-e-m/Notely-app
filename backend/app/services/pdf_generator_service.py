import os
import base64
from io import BytesIO
from typing import List
from PIL import Image as PILImage
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, HRFlowable, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from app.schemas.structural import StructuralElement, PDFExportRequest

class PDFGeneratorService:
    def generate_pdf_bytes(self, request: PDFExportRequest) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=35,
            leftMargin=35,
            topMargin=35,
            bottomMargin=35
        )

        styles = getSampleStyleSheet()

        primary_color = colors.HexColor("#1E40AF")   # Deep Blue H1
        secondary_color = colors.HexColor("#0D9488") # Teal H2
        accent_color = colors.HexColor("#7C3AED")    # Purple H3
        dark_neutral = colors.HexColor("#1F2937")    # Charcoal body text

        title_style = ParagraphStyle(
            'DocSubjectTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=20,
            leading=24,
            textColor=primary_color,
            alignment=0,
            spaceAfter=4
        )

        subtitle_style = ParagraphStyle(
            'DocLessonTitle',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=18,
            textColor=secondary_color,
            alignment=0,
            spaceAfter=10
        )

        heading_styles = {
            'h1': ParagraphStyle('H1Style', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=16, leading=20, textColor=primary_color, spaceBefore=12, spaceAfter=6),
            'h2': ParagraphStyle('H2Style', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=13, leading=17, textColor=secondary_color, spaceBefore=8, spaceAfter=4),
            'h3': ParagraphStyle('H3Style', parent=styles['Heading3'], fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=accent_color, spaceBefore=6, spaceAfter=3),
            'h4': ParagraphStyle('H4Style', parent=styles['Heading4'], fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=dark_neutral, spaceBefore=5, spaceAfter=3),
            'h5': ParagraphStyle('H5Style', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=13, textColor=dark_neutral, spaceBefore=4, spaceAfter=2),
            'h6': ParagraphStyle('H6Style', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=10, leading=13, textColor=dark_neutral, spaceBefore=4, spaceAfter=2),
        }

        body_style = ParagraphStyle(
            'BodyContent',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=11,
            leading=15,
            textColor=dark_neutral,
            spaceAfter=6
        )

        story = []

        # En-tête de document
        story.append(Paragraph(request.subject.upper(), title_style))
        story.append(Paragraph(request.lessonTitle, subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1.2, color=primary_color, spaceAfter=12))

        current_page_num = 1

        for elem in request.elements:
            if getattr(elem, 'pageNumber', 1) > current_page_num:
                current_page_num = getattr(elem, 'pageNumber', 1)
                story.append(PageBreak())

            if elem.type in heading_styles:
                story.append(Paragraph(elem.text, heading_styles[elem.type]))
            elif elem.type == 'diagram':
                if elem.image_base64:
                    try:
                        clean_b64 = elem.image_base64.split(",")[-1].strip()
                        img_bytes = base64.b64decode(clean_b64)
                        img_stream = BytesIO(img_bytes)

                        # Calcul intelligent des dimensions de l'image pour préserver les proportions
                        with PILImage.open(BytesIO(img_bytes)) as pil_img:
                            orig_w, orig_h = pil_img.size
                            max_w = 460.0
                            max_h = 240.0
                            ratio = min(max_w / max(orig_w, 1.0), max_h / max(orig_h, 1.0), 1.0)
                            display_w = orig_w * ratio
                            display_h = orig_h * ratio

                        img_flowable = RLImage(img_stream, width=display_w, height=display_h)
                        img_flowable.hAlign = 'CENTER'
                        story.append(Spacer(1, 4))
                        story.append(img_flowable)
                        story.append(Spacer(1, 4))
                    except Exception:
                        story.append(Paragraph("[Schéma géométrique]", body_style))
            else:
                story.append(Paragraph(elem.text, body_style))

        doc.build(story)
        pdf_data = buffer.getvalue()
        buffer.close()
        return pdf_data

pdf_generator_service = PDFGeneratorService()
