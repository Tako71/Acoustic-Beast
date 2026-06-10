from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import matplotlib

_FONT_DIR = os.path.join(os.path.dirname(matplotlib.__file__), 'mpl-data', 'fonts', 'ttf')
pdfmetrics.registerFont(TTFont('DejaVu', os.path.join(_FONT_DIR, 'DejaVuSans.ttf')))
pdfmetrics.registerFont(TTFont('DejaVu-Bold', os.path.join(_FONT_DIR, 'DejaVuSans-Bold.ttf')))


def _get_styles():
    styles = getSampleStyleSheet()
    normal = ParagraphStyle('RuNormal', parent=styles['Normal'], fontName='DejaVu', fontSize=11, leading=16)
    heading = ParagraphStyle('RuHeading', parent=styles['Heading1'], fontName='DejaVu-Bold', fontSize=14, leading=20)
    small = ParagraphStyle('RuSmall', parent=styles['Normal'], fontName='DejaVu', fontSize=9, leading=13)
    return normal, heading, small


def generate_pdf(report):
    """Генерирует PDF-отчёт и возвращает bytes."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    normal, heading, small = _get_styles()
    story = []

    m = report.measurement

    # Заголовок
    story.append(Paragraph('Отчёт о расчёте уровня шума', heading))
    story.append(Spacer(1, 0.4*cm))

    # Данные о замере
    info_data = [
        ['Компания:', m.company],
        ['Место проведения:', m.location],
        ['Стратегия расчёта:', m.get_strategy_display()],
        ['Количество точек:', str(m.num_points)],
        ['Дата:', m.created_at.strftime('%d.%m.%Y %H:%M')],
    ]
    info_table = Table(info_data, colWidths=[5*cm, 12*cm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'DejaVu'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('FONTNAME', (0, 0), (0, -1), 'DejaVu-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.6*cm))

    # Результаты расчёта
    story.append(Paragraph('Результаты расчёта', heading))
    story.append(Spacer(1, 0.3*cm))

    status = 'ПРЕВЫШЕНИЕ НОРМЫ' if report.exceeds_norm else 'В ПРЕДЕЛАХ НОРМЫ'
    status_color = colors.red if report.exceeds_norm else colors.green

    result_data = [
        ['Показатель', 'Значение'],
        ['Эквивалентный уровень L_EX,8h, дБ', f'{report.lex_8h:.2f}'],
        ['Предельно допустимый уровень (ПДУ), дБ', f'{report.norm_value:.1f}'],
        ['Стандартное отклонение, дБ', f'{report.std_deviation:.2f}'],
        ['Максимальное значение, дБ', f'{report.max_noise:.1f}'],
        ['Минимальное значение, дБ', f'{report.min_noise:.1f}'],
        ['Статус', status],
    ]
    result_table = Table(result_data, colWidths=[10*cm, 7*cm])
    result_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d2d2d')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'DejaVu-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'DejaVu'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('TEXTCOLOR', (1, -1), (1, -1), status_color),
        ('FONTNAME', (1, -1), (1, -1), 'DejaVu-Bold'),
    ]))
    story.append(result_table)
    story.append(Spacer(1, 0.6*cm))

    # Точки замера
    story.append(Paragraph('Данные замеров по точкам', heading))
    story.append(Spacer(1, 0.3*cm))

    points = list(m.points.all())
    points_data = [['Точка', 'Уровень шума, дБ', 'Длительность, мин']]
    for p in points:
        dur = f'{p.duration_min:.1f}' if p.duration_min is not None else '—'
        points_data.append([str(p.point_number), f'{p.noise_db:.1f}', dur])

    points_table = Table(points_data, colWidths=[3*cm, 7*cm, 7*cm])
    points_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d2d2d')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'DejaVu-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'DejaVu'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(points_table)
    story.append(Spacer(1, 0.6*cm))

    # Рекомендации
    story.append(Paragraph('Рекомендации', heading))
    story.append(Spacer(1, 0.3*cm))
    for line in report.recommendations.split('\n'):
        if line.strip():
            story.append(Paragraph(line, normal))
            story.append(Spacer(1, 0.15*cm))

    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(
        'Расчёт выполнен в соответствии с ГОСТ ISO 9612-2016 '
        '«Акустика. Измерения шума для оценки его воздействия на человека. '
        'Метод измерений на рабочих местах».',
        small
    ))

    doc.build(story)
    return buffer.getvalue()
