import json
import os
import re
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import openpyxl

HISTORY_FILE = 'history.json'

# Регистрация шрифта с кириллицей
FONT_PATH = 'DejaVuSans.ttf'
if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont('DejaVuSans', FONT_PATH))
    FONT_NAME = 'DejaVuSans'
else:
    print("ВНИМАНИЕ: Шрифт DejaVuSans.ttf не найден, используем Helvetica (кириллица не отобразится)")
    FONT_NAME = 'Helvetica'

def clean_text(text):
    """Удаляет эмодзи, оставляет русские/английские буквы, цифры и знаки."""
    if not isinstance(text, str):
        return str(text)
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F700-\U0001F77F"
        u"\U0001F780-\U0001F7FF"
        u"\U0001F800-\U0001F8FF"
        u"\U0001F900-\U0001F9FF"
        u"\U0001FA00-\U0001FA6F"
        u"\U0001FA70-\U0001FAFF"
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    text = emoji_pattern.sub(r'', text)
    # Оставляем только печатные символы (включая кириллицу)
    text = ''.join(ch for ch in text if ch.isprintable() or ch in '\n\r\t')
    return text.strip()

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except (json.JSONDecodeError, IOError):
        return []

def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def add_record(image_name, guest_count, occupancy, annotated_image_path=None):
    history = load_history()
    record = {
        'id': len(history) + 1,
        'timestamp': datetime.now().isoformat(),
        'image_name': clean_text(image_name),
        'guest_count': int(guest_count) if isinstance(guest_count, (int, float)) else 0,
        'occupancy': clean_text(occupancy),
        'annotated_image': annotated_image_path
    }
    history.append(record)
    save_history(history)
    return record

def generate_pdf_report(records, output_path='report.pdf'):
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    # Применяем наш шрифт ко всем стилям
    for style_name in styles.byName:
        styles[style_name].fontName = FONT_NAME
    title_style = ParagraphStyle('Title', parent=styles['Title'], fontName=FONT_NAME)
    normal_style = ParagraphStyle('Normal', parent=styles['Normal'], fontName=FONT_NAME)

    story = []
    title = Paragraph("Отчёт по количеству гостей в кафе", title_style)
    story.append(title)
    story.append(Spacer(1, 0.2*inch))

    # Заголовки таблицы (русские)
    data = [["ID", "Время", "Файл", "Гостей", "Загруженность"]]
    for rec in records[-50:]:
        time_str = clean_text(rec.get('timestamp', ''))[:19]
        fname = clean_text(rec.get('image_name', ''))
        occupancy = clean_text(rec.get('occupancy', ''))
        data.append([
            str(rec.get('id', '')),
            time_str,
            fname,
            str(rec.get('guest_count', 0)),
            occupancy
        ])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), FONT_NAME),
        ('FONTNAME', (0,1), (-1,-1), FONT_NAME),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.beige),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.2*inch))

    # Добавляем изображения
    for rec in records[-5:]:
        img_path = rec.get('annotated_image')
        if img_path and os.path.exists(img_path.lstrip('/')):
            try:
                img = Image(img_path.lstrip('/'), width=4*inch, height=3*inch)
                caption = clean_text(f"Файл: {rec.get('image_name', '')} (гостей: {rec.get('guest_count', 0)})")
                story.append(Paragraph(caption, normal_style))
                story.append(img)
                story.append(Spacer(1, 0.1*inch))
            except Exception as e:
                print(f"Не удалось добавить изображение {img_path}: {e}")

    doc.build(story)

def generate_excel_report(records, output_path='report.xlsx'):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "История"
    headers = ["ID", "Время", "Имя файла", "Количество гостей", "Загруженность", "Путь к аннотации"]
    ws.append(headers)
    for rec in records:
        ws.append([
            rec.get('id', ''),
            rec.get('timestamp', ''),
            clean_text(rec.get('image_name', '')),
            rec.get('guest_count', 0),
            clean_text(rec.get('occupancy', '')),
            rec.get('annotated_image', '')
        ])
    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            try:
                cell_len = len(str(cell.value))
                if cell_len > max_len:
                    max_len = cell_len
            except:
                pass
        ws.column_dimensions[col_letter].width = min(max_len + 2, 50)
    wb.save(output_path)
