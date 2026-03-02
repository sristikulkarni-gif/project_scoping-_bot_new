"""
PDF generation for case studies.
"""
import logging
import io
from typing import Dict, Any
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER

logger = logging.getLogger(__name__)


def generate_case_study_pdf(case_study_data: Dict[str, Any]) -> bytes:
    """
    Generate a PDF file for a case study.

    Args:
        case_study_data: Dictionary containing:
            - client_name: str
            - overview: str
            - solution: str
            - impact: str
            - project_title: str (optional)

    Returns:
        PDF file content as bytes
    """
    try:
        # Create PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        # Container for elements
        elements = []

        # Styles
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a365d'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2c5282'),
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold'
        )

        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['BodyText'],
            fontSize=11,
            leading=16,
            spaceAfter=12,
            alignment=TA_LEFT,
            fontName='Helvetica'
        )

        # Add title
        client_name = case_study_data.get('client_name', 'Client')
        project_title = case_study_data.get('project_title', '')

        title_text = f"Case Study: {client_name}"
        if project_title:
            title_text += f" - {project_title}"

        elements.append(Paragraph(title_text, title_style))
        elements.append(Spacer(1, 0.5*cm))

        # Add AI-generated banner if applicable
        if case_study_data.get('pending_approval', False):
            banner_style = ParagraphStyle(
                'Banner',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#d97706'),
                alignment=TA_CENTER,
                fontName='Helvetica-Oblique',
                spaceAfter=20,
                borderWidth=1,
                borderColor=colors.HexColor('#fbbf24'),
                borderPadding=5,
                backColor=colors.HexColor('#fef3c7')
            )
            elements.append(Paragraph("⚠️ AI-Generated Case Study — Pending Admin Approval", banner_style))
            elements.append(Spacer(1, 0.5*cm))

        # Add Client Information Table
        client_data = [
            ["Client Name:", client_name],
        ]
        if project_title:
            client_data.append(["Project:", project_title])

        client_table = Table(client_data, colWidths=[4*cm, 12*cm])
        client_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2c5282')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(client_table)
        elements.append(Spacer(1, 0.8*cm))

        # Add Overview section
        elements.append(Paragraph("Overview", heading_style))
        overview_text = case_study_data.get('overview', 'No overview available.')
        elements.append(Paragraph(overview_text, body_style))
        elements.append(Spacer(1, 0.3*cm))

        # Add Solution section
        elements.append(Paragraph("Solution", heading_style))
        solution_text = case_study_data.get('solution', 'No solution details available.')
        elements.append(Paragraph(solution_text, body_style))
        elements.append(Spacer(1, 0.3*cm))

        # Add Impact section
        elements.append(Paragraph("Impact & Results", heading_style))
        impact_text = case_study_data.get('impact', 'No impact details available.')
        elements.append(Paragraph(impact_text, body_style))

        # Build PDF
        doc.build(elements)

        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()

        logger.info(f"✅ Generated PDF for case study: {client_name}")
        return pdf_bytes

    except Exception as e:
        logger.error(f"Failed to generate case study PDF: {e}")
        raise