from __future__ import annotations

import io
import json
import logging
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)

logger = logging.getLogger(__name__)

class ExportService:
    """Service to handle document exporting (PDF, CSV, JSON)."""

    @staticmethod
    def export_csv(data: List[Dict[str, Any]]) -> str:
        """Export raw list of dicts to CSV string."""
        if not data:
            return ""
        df = pd.DataFrame(data)
        return df.to_csv(index=False)

    @staticmethod
    def export_json(data: List[Dict[str, Any]]) -> str:
        """Export data to formatted JSON string."""
        return json.dumps(data, indent=2, default=str)

    @staticmethod
    def generate_dashboard_pdf(
        dashboard_name: str,
        widgets: List[Dict[str, Any]],
        creator_name: str = "Nexus User"
    ) -> bytes:
        """Generate a styled PDF report for a dashboard and its widgets."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=54,
            leftMargin=54,
            topMargin=54,
            bottomMargin=54
        )

        styles = getSampleStyleSheet()
        
        # Custom premium styles
        title_style = ParagraphStyle(
            name="CoverTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=26,
            leading=32,
            textColor=colors.HexColor("#1e293b"),
            alignment=0, # Left-aligned
            spaceAfter=10
        )
        
        meta_style = ParagraphStyle(
            name="CoverMeta",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=25
        )

        section_heading = ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#4f46e5"), # Premium Indigo
            spaceBefore=15,
            spaceAfter=8,
            keepWithNext=True
        )

        body_style = ParagraphStyle(
            name="ReportBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#334155")
        )

        code_style = ParagraphStyle(
            name="ReportCode",
            parent=styles["Code"],
            fontName="Courier",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#0f172a"),
            backColor=colors.HexColor("#f1f5f9"),
            borderColor=colors.HexColor("#e2e8f0"),
            borderWidth=1,
            borderPadding=6,
            spaceAfter=12
        )

        story = []

        # --- Header Section ---
        story.append(Paragraph(dashboard_name, title_style))
        story.append(Paragraph(
            f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')} | Created by {creator_name}",
            meta_style
        ))
        story.append(Spacer(1, 10))

        # --- Content Section ---
        if not widgets:
            story.append(Paragraph("This dashboard contains no widgets.", body_style))
        else:
            for i, widget in enumerate(widgets, start=1):
                widget_title = widget.get("title", f"Widget #{i}")
                widget_type = widget.get("type", "table").upper()
                query_sql = widget.get("query", "")
                widget_data = widget.get("data", [])

                widget_story = []
                # Header & Type indicator
                widget_story.append(Paragraph(f"{i}. {widget_title} ({widget_type})", section_heading))
                
                # Show SQL Query if present
                if query_sql:
                    widget_story.append(Paragraph("SQL Query:", body_style))
                    widget_story.append(Paragraph(query_sql.replace("\n", "<br/>"), code_style))

                # Display Widget Data
                if not widget_data:
                    widget_story.append(Paragraph("No data retrieved for this widget.", body_style))
                else:
                    df = pd.DataFrame(widget_data)
                    # Limit to top 15 rows for PDF clean layout
                    max_rows = 15
                    display_df = df.head(max_rows)

                    # Prepare table data: headers + rows
                    table_headers = [str(col) for col in display_df.columns]
                    table_rows = []
                    for _, row in display_df.iterrows():
                        table_rows.append([str(val) for val in row.values])

                    pdf_table_data = [table_headers] + table_rows
                    
                    # Compute dynamic widths based on column contents
                    col_widths = []
                    for col_idx in range(len(table_headers)):
                        max_len = len(table_headers[col_idx])
                        for row in table_rows:
                            max_len = max(max_len, len(row[col_idx]))
                        col_widths.append(min(max(max_len * 6.5, 50), 150)) # limit width per col

                    t = Table(pdf_table_data, colWidths=col_widths, hAlign="LEFT")
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#4f46e5")),
                        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0,0), (-1,0), 9),
                        ('BOTTOMPADDING', (0,0), (-1,0), 6),
                        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#f8fafc")),
                        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#f8fafc"), colors.HexColor("#ffffff")]),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
                        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
                        ('FONTSIZE', (0,1), (-1,-1), 8),
                        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ]))
                    widget_story.append(t)

                    if len(df) > max_rows:
                        widget_story.append(Spacer(1, 4))
                        widget_story.append(Paragraph(
                            f"<i>* Showing top {max_rows} of {len(df)} total rows. Export as CSV for full dataset.</i>",
                            body_style
                        ))

                widget_story.append(Spacer(1, 20))
                # Keep individual widget elements together so they don't break across pages awkwardly
                story.append(KeepTogether(widget_story))

        # Build PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
