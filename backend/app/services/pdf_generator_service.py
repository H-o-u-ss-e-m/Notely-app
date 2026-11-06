import os
import re
import base64
from io import BytesIO
from typing import List
from PIL import Image as PILImage
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, HRFlowable, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_ARABIC_SUPPORT = True
except ImportError:
    HAS_ARABIC_SUPPORT = False

from app.schemas.structural import StructuralElement, PDFExportRequest

# Détection de caractères arabes Unicode
_ARABIC_CHAR_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")

def is_arabic_text(text: str) -> bool:
    return bool(_ARABIC_CHAR_RE.search(text))

def shape_arabic_for_pdf(text: str) -> str:
    """Applique le reshaping des ligatures et l'algorithme bidi pour ReportLab (Plan v2 §5.11)."""
    if not text:
        return text
    if HAS_ARABIC_SUPPORT and is_arabic_text(text):
        try:
            reshaped = arabic_reshaper.reshape(text)
            return get_display(reshaped)
        except Exception:
            return text
    return text

class PDFGeneratorService:
    def __init__(self):
        self._font_registered = False
        self._font_name = "Helvetica"
        self._bold_font_name = "Helvetica-Bold"
        self._register_arabic_font_if_available()

    def _register_arabic_font_if_available(self):
        # Vérifier polices supportant l'arabe (ex: Arial sur Windows, Noto Naskh Arabic sur Linux)
        candidate_paths = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
            "/usr/share/fonts/opentype/noto/NotoNaskhArabic-Regular.ttf",
        ]
        regular_path = None
        bold_path = None
        for p in candidate_paths:
            if os.path.exists(p):
                if "bd" in p.lower() or "bold" in p.lower():
                    bold_path = p
                elif regular_path is None:
                    regular_path = p

        if regular_path:
            try:
                pdfmetrics.registerFont(TTFont("NotelyArabicFont", regular_path))
                self._font_name = "NotelyArabicFont"
                if bold_path and os.path.exists(bold_path):
                    pdfmetrics.registerFont(TTFont("NotelyArabicBold", bold_path))
                    self._bold_font_name = "NotelyArabicBold"
                else:
                    self._bold_font_name = "NotelyArabicFont"
                self._font_registered = True
            except Exception:
                pass

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

        base_font = self._font_name
        bold_font = self._bold_font_name

        title_style = ParagraphStyle(
            'DocSubjectTitle',
            parent=styles['Heading1'],
            fontName=bold_font,
            fontSize=20,
            leading=24,
            textColor=primary_color,
            alignment=0,
            spaceAfter=4
        )

        subtitle_style = ParagraphStyle(
            'DocLessonTitle',
            parent=styles['Heading2'],
            fontName=bold_font,
            fontSize=14,
            leading=18,
            textColor=secondary_color,
            alignment=0,
            spaceAfter=10
        )

        heading_styles = {
            'h1': ParagraphStyle('H1Style', parent=styles['Heading1'], fontName=bold_font, fontSize=16, leading=20, textColor=primary_color, spaceBefore=12, spaceAfter=6),
            'h2': ParagraphStyle('H2Style', parent=styles['Heading2'], fontName=bold_font, fontSize=13, leading=17, textColor=secondary_color, spaceBefore=8, spaceAfter=4),
            'h3': ParagraphStyle('H3Style', parent=styles['Heading3'], fontName=bold_font, fontSize=12, leading=15, textColor=accent_color, spaceBefore=6, spaceAfter=3),
            'h4': ParagraphStyle('H4Style', parent=styles['Heading4'], fontName=bold_font, fontSize=11, leading=14, textColor=dark_neutral, spaceBefore=5, spaceAfter=3),
            'h5': ParagraphStyle('H5Style', parent=styles['Normal'], fontName=bold_font, fontSize=10, leading=13, textColor=dark_neutral, spaceBefore=4, spaceAfter=2),
            'h6': ParagraphStyle('H6Style', parent=styles['Normal'], fontName=base_font, fontSize=10, leading=13, textColor=dark_neutral, spaceBefore=4, spaceAfter=2),
        }

        body_style = ParagraphStyle(
            'BodyContent',
            parent=styles['Normal'],
            fontName=base_font,
            fontSize=11,
            leading=15,
            textColor=dark_neutral,
            spaceAfter=6
        )

        story = []

        # En-tête de document avec support bidi/arabe
        shaped_subject = shape_arabic_for_pdf(request.subject.upper())
        shaped_lesson = shape_arabic_for_pdf(request.lessonTitle)

        story.append(Paragraph(shaped_subject, title_style))
        story.append(Paragraph(shaped_lesson, subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1.2, color=primary_color, spaceAfter=12))

        current_page_num = 1

        for elem in request.elements:
            if getattr(elem, 'pageNumber', 1) > current_page_num:
                current_page_num = getattr(elem, 'pageNumber', 1)
                story.append(PageBreak())

            shaped_text = shape_arabic_for_pdf(elem.text)

            if elem.type in heading_styles:
                story.append(Paragraph(shaped_text, heading_styles[elem.type]))
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
                story.append(Paragraph(shaped_text, body_style))

        doc.build(story)
        pdf_data = buffer.getvalue()
        buffer.close()
        return pdf_data

pdf_generator_service = PDFGeneratorService()
