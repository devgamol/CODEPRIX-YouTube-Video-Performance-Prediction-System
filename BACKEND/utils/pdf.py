from io import BytesIO

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


def _build_pdf(data, output):
    doc = SimpleDocTemplate(output)
    styles = getSampleStyleSheet()

    elements = []

    elements.append(Paragraph("Video Analysis Report", styles["Title"]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(f"Score: {data['overall_score']}", styles["Normal"]))
    elements.append(Paragraph(f"Summary: {data['summary']}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Suggestions:", styles["Heading2"]))

    for s in data["suggestions"]:
        text = f"{s['timestamp_start']}s - {s['timestamp_end']}s: {s['issue']} | {s['fix']}"
        elements.append(Paragraph(text, styles["Normal"]))
        elements.append(Spacer(1, 6))

    doc.build(elements)


def generate_pdf(data, file_path):
    _build_pdf(data, file_path)


def generate_pdf_bytes(data):
    buffer = BytesIO()
    _build_pdf(data, buffer)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
