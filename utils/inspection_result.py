#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
巡检结果管理模块，用于保存和加载巡检结果
"""

import json
import yaml
import os
import re
from functools import lru_cache
import time

import openpyxl
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple

# Попытка импорта для PDF генерации
try:
    from reportlab.lib.pagesizes import letter, A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.units import cm, inch
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

# 数据目录定义
DATA_DIR = Path(__file__).parent.parent / "data"
RESULTS_DIR = DATA_DIR / "results"

# 确保目录存在
os.makedirs(RESULTS_DIR, exist_ok=True)

class InspectionResult:
    """巡检结果类"""

    def __init__(self, cluster_name: str, inspection_type: str):
        """
        初始化巡检结果

        Args:
            cluster_name: 集群名称
            inspection_type: 巡检类型
        """
        self.cluster_name = cluster_name
        self.inspection_type = inspection_type
        self.timestamp = datetime.now()
        self.result_id = f"{cluster_name}_{inspection_type}_{self.timestamp.strftime('%Y%m%d%H%M%S')}"
        self.items = []

    def add_item(self, item: Dict) -> None:
        """
        添加巡检项

        Args:
            item: 巡检项字典，需包含：
                - name: 巡检项名称
                - status: 'passed' 或 'exception' (简化后的状态体系)
                - description: 描述
                - severity: 严重程度 ('critical', 'warning', 'info') - 仅用于异常项的细分级别
                - details: 详细内容
                - solution: 解决方案 (可选)
        """
        if 'solution' not in item:
            item['solution'] = ''

        # 状态标准化：统一将 failed、warning、error 转换为 exception
        if item.get('status') in ['failed', 'warning', 'error']:
            item['status'] = 'exception'

        self.items.append(item)

    def get_items(self) -> List[Dict]:
        """获取所有巡检项"""
        return self.items

    def get_summary(self) -> Dict:
        """获取巡检摘要"""
        passed = 0
        exception_critical = 0
        exception_warning = 0
        exception_info = 0

        for item in self.items:
            # 安全地获取status和severity，处理不同类型的item
            if isinstance(item, dict):
                status = item.get('status', 'unknown')
                severity = item.get('severity', 'unknown')
            elif hasattr(item, 'status'):
                status = getattr(item, 'status', 'unknown')
                severity = getattr(item, 'severity', 'unknown')
            else:
                status = 'unknown'
                severity = 'unknown'

            # 简化的状态体系：只有 passed 和 exception
            if status == 'passed':
                passed += 1
            else:
                # 所有非通过的状态都视为异常，按严重程度细分
                if severity == 'critical':
                    exception_critical += 1
                elif severity == 'warning':
                    exception_warning += 1
                else:
                    exception_info += 1

        total_exceptions = exception_critical + exception_warning + exception_info

        return {
            'cluster_name': self.cluster_name,
            'inspection_type': self.inspection_type,
            'timestamp': self.timestamp,
            'result_id': self.result_id,
            'total': len(self.items),
            'passed': passed,
            'total_exceptions': total_exceptions,
            'exception_critical': exception_critical,
            'exception_warning': exception_warning,
            'exception_info': exception_info,
            # 为兼容性保留旧字段
            'critical': exception_critical,
            'warning': exception_warning,
            'info': exception_info
        }

    def save(self) -> str:
        """
        保存巡检结果

        Returns:
            结果文件路径
        """
        # 创建集群结果目录
        cluster_dir = RESULTS_DIR / self.cluster_name
        os.makedirs(cluster_dir, exist_ok=True)

        result_data = {
            'cluster_name': self.cluster_name,
            'inspection_type': self.inspection_type,
            'timestamp': self.timestamp.isoformat(),
            'result_id': self.result_id,
            'items': self.items
        }

        result_file = cluster_dir / f"{self.result_id}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        # Очистка кэша после сохранения нового отчёта
        _clear_results_cache()

        return str(result_file)


def load_result(result_id: str) -> Optional[Dict]:
    """
    加载巡检结果

    Args:
        result_id: 巡检结果 ID

    Returns:
        巡检结果字典，如果不存在则返回 None
    """
    # 搜索results目录下所有json文件，找到匹配的result_id
    for file_path in RESULTS_DIR.glob('*.json'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                result_data = json.load(f)

            # 检查result_id是否匹配
            if result_data.get('result_id') == result_id:
                return result_data
        except Exception as e:
            # 记录读取失败的文件但继续搜索
            print(f"Warning: Failed to read {file_path}: {e}")
            continue

    # 如果通过result_id没找到，尝试通过文件名模式匹配
    # 处理不同的文件名格式
    possible_patterns = [
        f"inspection_result_{result_id}.json",
        f"{result_id}.json",
        # 尝试从result_id中提取集群名和时间戳
    ]

    # 如果result_id包含时间戳，尝试构建标准文件名
    if '_' in result_id:
        parts = result_id.split('_')
        if len(parts) >= 3:
            # 假设格式是 type_date_time，尝试找到对应的文件
            for file_path in RESULTS_DIR.glob(f'inspection_result_*_{parts[-2]}_{parts[-1]}.json'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        result_data = json.load(f)
                    # 如果文件内容匹配，返回结果
                    if result_data.get('result_id') == result_id:
                        return result_data
                except Exception as e:
                    print(f"Warning: Failed to read {file_path}: {e}")
                    continue

    # 尝试直接的文件名匹配
    for pattern in possible_patterns:
        result_file = RESULTS_DIR / pattern
        if result_file.exists():
            try:
                with open(result_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Failed to read {result_file}: {e}")
                continue

    return None


def export_report(result_id: str, format_type: str = "json") -> Tuple[bool, str]:
    """
    导出巡检报告为不同格式

    Args:
        result_id: 巡检结果ID
        format_type: 导出格式，支持 "json", "excel"

    Returns:
        (成功, 文件路径) 元组，成功为 True 时返回导出文件路径
    """
    # 加载巡检结果
    result_data = load_result(result_id)
    if not result_data:
        return False, "找不到指定巡检结果"

    # 从 result_data 获取集群名
    cluster_name = result_data.get('cluster_name', 'unknown')
    export_dir = RESULTS_DIR / cluster_name / "exports"
    import os
    os.makedirs(export_dir, exist_ok=True)

    # 根据格式类型导出
    if format_type == "json":
        # 找到原始结果文件
        source_path = None
        for file_path in RESULTS_DIR.glob('*.json'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if data.get('result_id') == result_id:
                    source_path = file_path
                    break
            except Exception:
                continue

        if source_path and source_path.exists():
            export_path = export_dir / f"{result_id}.json"
            import shutil
            shutil.copy(source_path, export_path)
            return True, str(export_path)
        else:
            return False, "找不到源文件"

    elif format_type == "excel":
        export_path = export_dir / f"{result_id}.xlsx"

        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "巡检结果"

            # 添加标题信息
            ws['A1'] = "集群巡检报告"
            ws['A2'] = f"集群名称: {result_data.get('cluster_name', '')}"
            ws['A3'] = f"巡检时间: {result_data.get('timestamp', '')}"
            ws['A4'] = f"报告ID: {result_data.get('result_id', '')}"

            # 添加表头
            headers = ['名称', '状态', '严重程度', '描述', '详细信息', '解决方案']
            for col, header in enumerate(headers, start=1):
                ws.cell(row=6, column=col, value=header)

            # 获取所有检查项 - 兼容新旧数据结构
            all_items = []
            if 'inspection_results' in result_data:
                # 新数据结构：从inspection_results中获取所有项目
                for inspector_type, inspector_result in result_data['inspection_results'].items():
                    items = inspector_result.get('items', [])
                    all_items.extend(items)
            else:
                # 旧数据结构：直接从items字段获取
                all_items = result_data.get('items', [])

            # 添加数据
            for row_idx, item in enumerate(all_items, start=7):
                ws.cell(row=row_idx, column=1, value=item.get('name', ''))
                ws.cell(row=row_idx, column=2, value=item.get('status', ''))
                ws.cell(row=row_idx, column=3, value=item.get('severity', ''))
                ws.cell(row=row_idx, column=4, value=item.get('description', ''))
                ws.cell(row=row_idx, column=5, value=item.get('details', ''))
                ws.cell(row=row_idx, column=6, value=item.get('solution', ''))

            # 保存工作簿
            wb.save(export_path)
            return True, str(export_path)
        except Exception as e:
            return False, f"导出Excel失败: {str(e)}"
    elif format_type == "pdf":
        if not PDF_SUPPORT:
            return False, "PDF экспорт недоступен. Установите reportlab: pip install reportlab"

        export_path = export_dir / f"{result_id}.pdf"

        try:
            # Улучшенный поиск шрифтов для кириллицы
            font_name = 'DejaVuSans'  # По умолчанию используем DejaVuSans

            # Проверяем доступные системные шрифты (в порядке приоритета)
            possible_fonts = [
                # DejaVu Sans (часто есть в Linux)
                ('/usr/share/fonts/dejavu/DejaVuSans.ttf', 'DejaVuSans'),
                ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 'DejaVuSans'),
                ('/usr/share/fonts/TTF/DejaVuSans.ttf', 'DejaVuSans'),

                # Liberation Sans (альтернатива в Linux)
                ('/usr/share/fonts/liberation/LiberationSans-Regular.ttf', 'LiberationSans'),

                # Arial (Windows/Linux)
                ('/usr/share/fonts/arial.ttf', 'Arial'),
                ('/usr/share/fonts/Arial.ttf', 'Arial'),
                ('/usr/share/fonts/truetype/msttcorefonts/Arial.ttf', 'Arial'),
                ('C:/Windows/Fonts/arial.ttf', 'Arial'),
                ('C:/Windows/Fonts/arial.ttf', 'Arial'),

                # Times New Roman
                ('/usr/share/fonts/TTF/Times.ttf', 'TimesNewRoman'),
                ('C:/Windows/Fonts/times.ttf', 'TimesNewRoman'),

                # FreeSans (может быть в системах с ghostscript)
                ('/usr/share/fonts/type1/gsfonts/FreeSans.pfb', 'FreeSans'),
            ]

            font_found = False
            for font_path, font_alias in possible_fonts:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont(font_alias, font_path))
                        font_name = font_alias
                        font_found = True
                        print(f"Используется шрифт: {font_alias} из {font_path}")
                        break
                    except Exception as e:
                        print(f"Не удалось загрузить шрифт {font_path}: {e}")
                        continue

            # Если не нашли подходящий шрифт, используем Times-Roman (лучше поддерживает Unicode)
            if not font_found:
                font_name = 'Times-Roman'
                print(f"Используется встроенный шрифт: {font_name}")

            # Создаем PDF документ с альбомной ориентацией
            doc = SimpleDocTemplate(str(export_path), pagesize=landscape(A4),
                                    topMargin=1*cm, bottomMargin=1*cm,
                                    leftMargin=1*cm, rightMargin=1*cm)
            styles = getSampleStyleSheet()

            # Создаем стили для кириллицы
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=14,
                spaceAfter=20,
                alignment=1,  # center
                fontName=font_name
            )

            header_style = ParagraphStyle(
                'CustomHeader',
                parent=styles['Heading2'],
                fontSize=11,
                spaceAfter=10,
                alignment=0,  # left
                fontName=font_name,
                textColor=colors.white
            )

            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=9,
                spaceAfter=6,
                fontName=font_name,
                leading=11  # межстрочный интервал
            )

            # Стиль для ячеек таблицы с переносом текста
            cell_style = ParagraphStyle(
                'TableCell',
                parent=styles['Normal'],
                fontSize=8,
                fontName=font_name,
                leading=10,
                wordWrap='CJK'  # Включаем перенос текста
            )

            # Функция для очистки текста от эмодзи
            def clean_text(text):
                if not isinstance(text, str):
                    text = str(text)
                # Удаляем эмодзи и специальные символы
                emoji_pattern = re.compile(
                    "["
                    "\U0001F600-\U0001F64F"  # emoticons
                    "\U0001F300-\U0001F5FF"  # symbols & pictographs
                    "\U0001F680-\U0001F6FF"  # transport & map symbols
                    "\U0001F1E0-\U0001F1FF"  # flags (iOS)
                    "\U00002700-\U000027BF"  # dingbats
                    "\U0001f926-\U0001f937"  # gestures
                    "\U00010000-\U0010ffff"  # other unicode
                    "\u2640-\u2642"  # gender symbols
                    "\u2600-\u2B55"  # misc symbols
                    "\u200d"  # zero width joiner
                    "\u23cf"  # eject symbol
                    "\u23e9"  # fast forward
                    "\u231a"  # watch
                    "\ufe0f"  # variation selector
                    "\u3030"  # wavy dash
                    "]+",
                    flags=re.UNICODE
                )
                return emoji_pattern.sub('', text).strip()

            # Функция для создания Paragraph с переносом текста
            def create_cell_paragraph(text, max_length=150):
                """Создает Paragraph с обрезанным текстом при необходимости"""
                clean = clean_text(text)
                if len(clean) > max_length:
                    clean = clean[:max_length] + "..."
                return Paragraph(clean, cell_style)

            # Собираем содержимое PDF
            story = []

            # Заголовок
            title = clean_text("Отчет о проверке кластера Kubernetes")
            story.append(Paragraph(title, title_style))
            story.append(Spacer(1, 10))

            # Информация о кластере
            cluster_info = [
                f"<b>Название кластера:</b> {clean_text(result_data.get('cluster_name', 'Неизвестно'))}",
                f"<b>Время проверки:</b> {result_data.get('timestamp', 'Неизвестно')}",
                f"<b>ID отчета:</b> {clean_text(result_data.get('result_id', 'Неизвестно'))}",
                f"<b>Тип проверки:</b> {clean_text(result_data.get('inspection_type', 'Неизвестно'))}"
            ]

            for info in cluster_info:
                story.append(Paragraph(info, normal_style))
            story.append(Spacer(1, 15))

            # Получаем все элементы проверки
            all_items = []
            if 'inspection_results' in result_data:
                for inspector_type, inspector_result in result_data['inspection_results'].items():
                    items = inspector_result.get('items', [])
                    all_items.extend(items)
            else:
                all_items = result_data.get('items', [])

            # Статистика
            passed_count = sum(1 for item in all_items if item.get('status') == 'passed')
            exception_count = len(all_items) - passed_count

            stats_text = f"<b>Всего проверок:</b> {len(all_items)}, <b>Пройдено:</b> {passed_count}, <b>Ошибок:</b> {exception_count}"
            story.append(Paragraph(stats_text, normal_style))
            story.append(Spacer(1, 15))

            # Таблица результатов
            if all_items:
                # Определяем максимальное количество строк на странице
                max_rows_per_page = 30  # Ограничиваем для читаемости

                # Разбиваем данные на части для пагинации
                for page_num, start_idx in enumerate(range(0, len(all_items), max_rows_per_page)):
                    end_idx = min(start_idx + max_rows_per_page, len(all_items))
                    page_items = all_items[start_idx:end_idx]

                    if page_num > 0:
                        story.append(Paragraph(f"<i>Продолжение таблицы...</i>", normal_style))
                        story.append(Spacer(1, 10))

                    # Создаем данные для таблицы
                    table_data = []

                    # Заголовки таблицы
                    header_row = [
                        create_cell_paragraph('Название проверки'),
                        create_cell_paragraph('Статус'),
                        create_cell_paragraph('Уровень важности'),
                        create_cell_paragraph('Описание'),
                        create_cell_paragraph('Решение')
                    ]
                    table_data.append(header_row)

                    # Добавляем данные
                    for item in page_items:
                        name = create_cell_paragraph(item.get('name', ''))
                        status = create_cell_paragraph(item.get('status', ''))

                        # Определяем цвет для статуса
                        status_color = colors.green
                        if item.get('status') != 'passed':
                            status_color = colors.red

                        severity = create_cell_paragraph(item.get('severity', ''))
                        description = create_cell_paragraph(item.get('description', ''))
                        solution = create_cell_paragraph(item.get('solution', ''))

                        row = [name, status, severity, description, solution]
                        table_data.append(row)

                    # Автоматическое определение ширины колонок
                    # Используем пропорциональное распределение с учетом содержимого
                    page_width = landscape(A4)[0] - 2*cm  # Ширина страницы минус отступы

                    # Определяем примерные пропорции колонок на основе их содержимого
                    col_proportions = [3.0, 1.0, 1.5, 4.0, 3.0]  # Примерные пропорции
                    total_proportion = sum(col_proportions)

                    # Рассчитываем ширину каждой колонки
                    col_widths = [(page_width / total_proportion) * prop for prop in col_proportions]

                    # Создаем таблицу
                    table = Table(table_data, colWidths=col_widths, repeatRows=1)

                    # Применяем стили к таблице
                    table_style = TableStyle([
                        # Заголовок таблицы
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4F81BD')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), font_name),
                        ('FONTSIZE', (0, 0), (-1, 0), 9),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                        ('TOPPADDING', (0, 0), (-1, 0), 8),

                        # Чередование цветов строк для читаемости
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')]),

                        # Границы таблицы
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),

                        # Выравнивание содержимого
                        ('ALIGN', (0, 1), (1, -1), 'CENTER'),  # Статус и важность по центру
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 4),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                        ('TOPPADDING', (0, 0), (-1, -1), 4),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),

                        # Автоматический перенос текста
                        ('WORDWRAP', (0, 0), (-1, -1), True),
                    ])

                    # Динамическое окрашивание ячеек статуса
                    for i in range(1, len(table_data)):
                        status_text = all_items[start_idx + i - 1].get('status', '')
                        if status_text == 'passed':
                            table_style.add('BACKGROUND', (1, i), (1, i), colors.lightgreen)
                        elif status_text in ['failed', 'error', 'exception']:
                            table_style.add('BACKGROUND', (1, i), (1, i), colors.lightcoral)
                        elif status_text == 'warning':
                            table_style.add('BACKGROUND', (1, i), (1, i), colors.lightyellow)

                    table.setStyle(table_style)

                    # Добавляем таблицу в историю
                    story.append(table)

                    # Добавляем разрыв страницы если это не последняя часть
                    if end_idx < len(all_items):
                        story.append(Spacer(1, 10))
                        story.append(Paragraph(f"Страница {page_num + 1}", normal_style))
                        story.append(Spacer(1, 20))

            # Добавляем итоговую статистику
            story.append(Spacer(1, 20))
            summary_text = f"<b>Итог:</b> Отчет сгенерирован {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            story.append(Paragraph(summary_text, normal_style))

            # Генерируем PDF
            doc.build(story)
            return True, str(export_path)

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return False, f"Ошибка экспорта PDF: {str(e)}\nДетали: {error_details}"

    else:
        return False, f"不支持的导出格式: {format_type}"


# Глобальный кэш для результатов
_results_cache = {}
_cache_timestamp = None
_CACHE_TTL = 300  # 5 минут

def _clear_results_cache():
    """Очистка кэша результатов"""
    global _results_cache, _cache_timestamp
    _results_cache.clear()
    _cache_timestamp = None
    # Также очищаем LRU кэш
    list_results_cached.cache_clear()


def _calculate_result_summary(result_data: Dict) -> Dict:
    """Вычисление сводки результатов для одного файла"""
    # Всегда пересчитываем заново для точности, игнорируя старые summary поля
    # 处理新的数据结构
    if 'inspection_results' in result_data:
        # 新格式：但没有summary，需要计算
        critical = 0
        warning = 0
        info = 0
        passed = 0
        total = 0

        for inspector_type, inspector_result in result_data.get('inspection_results', {}).items():
            items = inspector_result.get('items', [])
            total += len(items)

            for item in items:
                # 安全地获取status和severity，处理不同类型的item
                if isinstance(item, dict):
                    status = item.get('status', 'unknown')
                    severity = item.get('severity', 'unknown')
                elif hasattr(item, 'status'):
                    status = getattr(item, 'status', 'unknown')
                    severity = getattr(item, 'severity', 'unknown')
                else:
                    status = 'unknown'
                    severity = 'unknown'

                if status == 'passed':
                    passed += 1
                elif status == 'exception':
                    # Подсчёт по severity как в старом формате
                    if severity == 'critical':
                        critical += 1
                    elif severity == 'warning':
                        warning += 1
                    else:
                        info += 1
                else:
                    # Неизвестный статус - считаем как info
                    info += 1
    else:
        # 旧格式：直接items字段
        critical = 0
        warning = 0
        info = 0
        passed = 0

        for item in result_data.get('items', []):
            # 安全地获取status和severity，处理不同类型的item
            if isinstance(item, dict):
                status = item.get('status', 'unknown')
                severity = item.get('severity', 'unknown')
            elif hasattr(item, 'status'):
                status = getattr(item, 'status', 'unknown')
                severity = getattr(item, 'severity', 'unknown')
            else:
                status = 'unknown'
                severity = 'unknown'

            if status == 'passed':
                passed += 1
            elif status == 'exception':
                if severity == 'critical':
                    critical += 1
                elif severity == 'warning':
                    warning += 1
                else:
                    info += 1
            else:
                # Неизвестный статус - считаем как info
                info += 1

        total = len(result_data.get('items', []))

    return {
        'cluster_name': result_data.get('cluster_name', ''),
        'inspection_type': result_data.get('inspection_type', 'unknown'),
        'timestamp': result_data.get('timestamp', ''),
        'result_id': result_data.get('result_id', ''),
        'total': total,
        'passed': passed,
        'critical': critical,
        'warning': warning,
        'info': info
    }


@lru_cache(maxsize=10)
def list_results_cached(cluster_name: Optional[str] = None) -> List[Dict]:
    """
    Оптимизированная версия list_results с кэшированием

    Args:
        cluster_name: 可选的集群名称过滤

    Returns:
        巡检结果摘要列表
    """
    global _results_cache, _cache_timestamp

    cache_key = f"results_{cluster_name or 'all'}"
    current_time = time.time()

    # Проверка актуальности кэша
    if (cache_key in _results_cache and
        _cache_timestamp is not None and
        current_time - _cache_timestamp < _CACHE_TTL):
        return _results_cache[cache_key]

    results = []

    # Оптимизированная загрузка: предварительная фильтрация по имени файла
    for file_path in RESULTS_DIR.glob('*.json'):
        try:
            # Быстрая предварительная проверка по имени файла для кластера
            if cluster_name:
                # Ищем упоминание кластера в первых 200 символах файла
                with open(file_path, 'r', encoding='utf-8') as f:
                    chunk = f.read(200)
                    if f'cluster_name": "{cluster_name}"' not in chunk:
                        continue
                    f.seek(0)
                    result_data = json.load(f)
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    result_data = json.load(f)

            # Вычисление сводки
            summary = _calculate_result_summary(result_data)
            results.append(summary)

        except (json.JSONDecodeError, IOError, UnicodeDecodeError) as e:
            # Игнорируем поврежденные файлы
            continue
        except Exception as e:
            # Для других ошибок также пропускаем файл
            continue

    # Сортировка по времени (новые сначала)
    results.sort(key=lambda x: x['timestamp'], reverse=True)

    # Кэширование результата
    _results_cache[cache_key] = results
    _cache_timestamp = current_time

    return results


def list_results(cluster_name: Optional[str] = None, limit: Optional[int] = None, offset: int = 0, order_by: Optional[str] = None) -> List[Dict]:
    """
    列出巡检结果 с поддержкой пагинации и сортировки

    Args:
        cluster_name: 可选的集群名称过滤
        limit: максимальное количество результатов (None для всех)
        offset: смещение для пагинации
        order_by: поле для сортировки ('timestamp DESC' для сортировки по времени)

    Returns:
        巡检结果摘要列表
    """
    results = list_results_cached(cluster_name)

    # Применяем сортировку
    if order_by == 'timestamp DESC':
        results.sort(key=lambda x: x['timestamp'], reverse=True)

    # Применяем пагинацию
    if limit is not None:
        start_idx = offset
        end_idx = offset + limit
        results = results[start_idx:end_idx]

    return results


def load_result_minimal(file_path: Path) -> Optional[Dict]:
    """Загрузка только необходимых полей результата для списков"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Вернуть только необходимые поля для списка
        return {
            'result_id': data.get('result_id'),
            'cluster_name': data.get('cluster_name'),
            'timestamp': data.get('timestamp'),
            'inspection_type': data.get('inspection_type'),
            'critical': data.get('critical', 0),
            'warning': data.get('warning', 0),
            'passed': data.get('passed', 0)
        }
    except:
        return None

def get_latest_result_by_cluster(cluster_name: str) -> Optional[Dict[str, Any]]:
    """
    获取指定集群的最新巡检结果

    Args:
        cluster_name (str): 集群名称

    Returns:
        Optional[Dict[str, Any]]: 最新的巡检结果，如果没有则返回 None
    """
    results = list_results(cluster_name=cluster_name, limit=1)

    return results[0] if results else None