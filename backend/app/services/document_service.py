import io
import time
import uuid
from typing import List, Optional
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.schemas.documents import DocumentCreate, DocumentResponse, DocumentListResponse

class DocumentService:
    def __init__(self):
        self._storage: dict[str, DocumentResponse] = {}

    def create_document(self, doc_in: DocumentCreate) -> DocumentResponse:
        doc_id = str(uuid.uuid4())[:8]
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        doc = DocumentResponse(
            id=doc_id,
            title=doc_in.title or "Notebook Document",
            createdAt=now_str,
            updatedAt=now_str,
            strokes=doc_in.strokes,
            lines=doc_in.lines or [],
            fullText=doc_in.fullText or ""
        )
        self._storage[doc_id] = doc
        return doc

    def get_document(self, doc_id: str) -> Optional[DocumentResponse]:
        return self._storage.get(doc_id)

    def list_documents(self) -> DocumentListResponse:
        docs = list(self._storage.values())
        return DocumentListResponse(documents=docs, total=len(docs))

    def delete_document(self, doc_id: str) -> bool:
        if doc_id in self._storage:
            del self._storage[doc_id]
            return True
        return False

    def export_pdf(self, doc_id: str) -> bytes:
        doc = self.get_document(doc_id)
        if not doc:
            raise ValueError("Document introuvable.")

        buffer = io.BytesIO()
        pdf = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontSize=18,
            leading=22,
            textColor='#2563eb'
        )
        story.append(Paragraph(doc.title, title_style))
        story.append(Spacer(1, 12))

        body_style = ParagraphStyle(
            'DocBody',
            parent=styles['Normal'],
            fontSize=12,
            leading=16,
            textColor='#0f172a'
        )

        for line in doc.lines:
            if line.text:
                story.append(Paragraph(line.text, body_style))
                story.append(Spacer(1, 6))

        pdf.build(story)
        return buffer.getvalue()

document_service = DocumentService()
