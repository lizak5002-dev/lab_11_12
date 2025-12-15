import threading
import time
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from reportlab.pdfgen import canvas
import openpyxl
from io import BytesIO
from datetime import datetime

class ReportGeneratorThread(threading.Thread):
    def __init__(self, groups_data, report_type, callback=None):
        threading.Thread.__init__(self)
        self.groups_data = groups_data
        self.report_type = report_type  # 'pdf' или 'excel'
        self.callback = callback
        self.report_url = None
        
    def run(self):
        """Запуск генерации отчета в отдельном потоке"""
        try:
            if self.report_type == 'pdf':
                file_content = self.generate_pdf()
                filename = f"reports/groups_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            else:
                file_content = self.generate_excel()
                filename = f"reports/groups_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            # Сохраняем файл в хранилище
            self.report_url = default_storage.save(filename, ContentFile(file_content))
            
            # Вызываем колбек если есть
            if self.callback:
                self.callback(self.report_url)
                
        except Exception as e:
            print(f"Ошибка генерации отчета: {e}")
            if self.callback:
                self.callback(None, str(e))
    
    def generate_pdf(self):
        """Генерация PDF в памяти"""
        buffer = BytesIO()
        p = canvas.Canvas(buffer)
        
        # Заголовок
        p.setFont("Helvetica", 16)
        p.drawString(100, 800, "Отчет по группам")
        p.setFont("Helvetica", 10)
        p.drawString(400, 800, f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        
        # Подзаголовок
        p.setFont("Helvetica", 12)
        p.drawString(100, 780, f"Всего групп: {len(self.groups_data)}")
        
        # Данные
        y = 750
        p.setFont("Helvetica", 12)
        
        # Заголовки таблицы
        p.drawString(50, y, "№")
        p.drawString(100, y, "Группа")
        p.drawString(250, y, "Возрастная категория")
        p.drawString(400, y, "Год открытия")
        p.drawString(480, y, "Кол-во детей")
        y -= 20
        p.line(50, y, 550, y)
        y -= 10
        
        # Данные
        for i, group in enumerate(self.groups_data, 1):
            if y < 50:  # Новая страница
                p.showPage()
                y = 800
                p.setFont("Helvetica", 12)
            
            p.drawString(50, y, str(i))
            p.drawString(100, y, group.get('group_name', ''))
            p.drawString(250, y, group.get('age_category', ''))
            p.drawString(400, y, str(group.get('start_year', '')))
            p.drawString(480, y, str(group.get('child_count', 0)))
            y -= 20
        
        p.save()
        pdf = buffer.getvalue()
        buffer.close()
        return pdf
    
    def generate_excel(self):
        """Генерация Excel в памяти"""
        buffer = BytesIO()
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Группы"
        
        # Заголовки
        headers = ['№', 'Группа', 'Возрастная категория', 'Год открытия', 
                   'Воспитатель', 'Количество детей', 'Средний возраст']
        
        for col, header in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=header)
        
        # Данные
        for row, group in enumerate(self.groups_data, 2):
            ws.cell(row=row, column=1, value=row-1)
            ws.cell(row=row, column=2, value=group.get('group_name', ''))
            ws.cell(row=row, column=3, value=group.get('age_category', ''))
            ws.cell(row=row, column=4, value=group.get('start_year', ''))
            
            teacher = group.get('teacher')
            if teacher:
                ws.cell(row=row, column=5, value=f"{teacher.last_name} {teacher.first_name}")
            
            ws.cell(row=row, column=6, value=group.get('child_count', 0))
            ws.cell(row=row, column=7, value=group.get('avg_age', ''))
        
        # Автоширина
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        wb.save(buffer)
        excel_data = buffer.getvalue()
        buffer.close()
        return excel_data