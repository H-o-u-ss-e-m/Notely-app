import os
from io import BytesIO
from typing import List
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

from app.schemas.structural import PDFRawExportRequest, PageData

class PDFRawGeneratorService:
    def generate_raw_pdf_bytes(self, request: PDFRawExportRequest) -> bytes:
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        pdf.setTitle(f"{request.subject} - {request.lessonTitle}")

        page_width, page_height = A4

        # Extraire la liste des pages à exporter
        pages: List[PageData] = []
        if request.pages and len(request.pages) > 0:
            pages = request.pages
        elif request.strokes:
            pages = [PageData(
                pageNumber=1,
                strokes=request.strokes,
                width=request.canvasWidth,
                height=request.canvasHeight
            )]

        total_pages = len(pages) if pages else 1

        if not pages:
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(40, page_height - 35, f"{request.subject} - {request.lessonTitle}")
            pdf.setFont("Helvetica", 11)
            pdf.drawString(40, page_height - 65, "Document sans contenu.")
            pdf.showPage()
            pdf.save()
            pdf_data = buffer.getvalue()
            buffer.close()
            return pdf_data

        for idx, pdata in enumerate(pages, start=1):
            c_width = max(pdata.width or request.canvasWidth, 1.0)
            c_height = max(pdata.height or request.canvasHeight, 1.0)

            # En-tête de la page
            pdf.setFillColor(HexColor("#1E40AF"))
            pdf.setFont("Helvetica-Bold", 15)
            pdf.drawString(40, page_height - 32, f"{request.subject} - {request.lessonTitle}")

            pdf.setFillColor(HexColor("#6B7280"))
            pdf.setFont("Helvetica", 9)
            pdf.drawString(40, page_height - 46, "Export Brut Tel Quel (Fidélité manuscrite et proportions conservées)")

            # Ligne de séparation élégante
            pdf.setStrokeColor(HexColor("#E5E7EB"))
            pdf.setLineWidth(1.0)
            pdf.line(40, page_height - 52, page_width - 40, page_height - 52)

            # Pied de page
            pdf.setFillColor(HexColor("#9CA3AF"))
            pdf.setFont("Helvetica", 9)
            pdf.drawRightString(page_width - 40, 22, f"Page {idx} / {total_pages}")

            # Calcul du Bounding Box intelligent pour éliminer les espaces blancs inutiles
            all_points = [p for s in pdata.strokes for p in s.points if p]

            if all_points:
                raw_min_x = min(p.x for p in all_points)
                raw_max_x = max(p.x for p in all_points)
                raw_min_y = min(p.y for p in all_points)
                raw_max_y = max(p.y for p in all_points)

                content_w = max(raw_max_x - raw_min_x, 1.0)
                content_h = max(raw_max_y - raw_min_y, 1.0)

                # Zone disponible sur la page A4 (marges de 40pt)
                avail_w = page_width - 80.0
                avail_h = page_height - 95.0

                # Définir un cadre de référence équilibré (évite qu'un seul mot prenne toute la feuille)
                pad_x = 20.0
                pad_y = 20.0
                ref_w = max(content_w + 2 * pad_x, c_width * 0.40, 360.0)
                ref_h = max(content_h + 2 * pad_y, c_height * 0.40, 480.0)

                # Échelle uniforme sans déformation
                scale = min(avail_w / ref_w, avail_h / ref_h)

                # Centrage horizontal et positionnement haut naturel sous l'en-tête
                box_w = content_w * scale
                offset_x = 40.0 + (avail_w - box_w) / 2.0 - (raw_min_x * scale)
                top_banner_y = page_height - 68.0
                offset_y = top_banner_y + (raw_min_y * scale)

                for stroke in pdata.strokes:
                    if not stroke.points:
                        continue

                    path = pdf.beginPath()
                    p0 = stroke.points[0]
                    start_x = (p0.x * scale) + offset_x
                    start_y = offset_y - (p0.y * scale)
                    path.moveTo(start_x, start_y)

                    for point in stroke.points[1:]:
                        x = (point.x * scale) + offset_x
                        y = offset_y - (point.y * scale)
                        path.lineTo(x, y)

                    color_hex = stroke.color if stroke.color else "#000000"
                    line_width = max((stroke.width or 3.0) * scale, 0.8)

                    pdf.setStrokeColor(HexColor(color_hex))
                    pdf.setLineWidth(line_width)
                    pdf.drawPath(path, stroke=1, fill=0)
            else:
                pdf.setFillColor(HexColor("#9CA3AF"))
                pdf.setFont("Helvetica-Oblique", 11)
                pdf.drawCentredString(page_width / 2.0, page_height / 2.0, "(Page vierge)")

            pdf.showPage()

        pdf.save()
        pdf_data = buffer.getvalue()
        buffer.close()
        return pdf_data

pdf_raw_generator_service = PDFRawGeneratorService()
