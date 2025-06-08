import flet as ft
import pandas as pd
from datetime import datetime
from utils.button_utils import create_button
from pages.reports_page.current_reports.export_to_excel import export_to_excel

def show_expenses_report(self):
    """عرض تقرير المصروفات"""
    try:
        # استعلام SQL لجلب المصروفات من جدول expenses
        query = f"""
            SELECT item_name, quantity, price, (price * quantity) as total_price, consumption
            FROM expenses
        """
        expenses = self.db.fetch_all(query)
        
        # التحقق من وجود بيانات
        if not expenses:
            self.show_snackbar("لا توجد مصروفات")
            return
        
        # إنشاء DataFrame باستخدام pandas
        df = pd.DataFrame(expenses, columns=["اسم الصنف", "الكمية", "سعر الوحدة", "السعر الكامل", "الاستهلاك"])
        
        # حساب إجمالي المصروفات وإجمالي الاستهلاك
        total_expenses = df["السعر الكامل"].sum()
        total_consumption = (df["الاستهلاك"] * df["سعر الوحدة"]).sum()  # إجمالي سعر الاستهلاك
        
        # دالة لتوسيط النصوص
        def centered_text(text, style=None):
            return ft.Container(
                content=ft.Text(text, style=style),
                alignment=ft.alignment.center,
                padding=10,
                expand=True
            )
        
        # إنشاء جدول Flet لعرض البيانات
        data_table = ft.DataTable(
            bgcolor=ft.colors.WHITE,  # خلفية الجدول بيضاء
            heading_row_color=ft.colors.BLUE,  # رأس الجدول أزرق
            border=ft.border.all(1, ft.colors.BLACK),  # حدود خارجية
            horizontal_lines=ft.BorderSide(1, ft.colors.BLACK),  # خطوط أفقية
            vertical_lines=ft.BorderSide(1, ft.colors.BLACK),  # خطوط عمودية
            column_spacing=0,  # تقليل المسافة بين الأعمدة
            columns=[
                ft.DataColumn(centered_text("اسم الصنف", style=self.text_style)),
                ft.DataColumn(centered_text("الكمية", style=self.text_style)),
                ft.DataColumn(centered_text("سعر الوحدة", style=self.text_style)),
                ft.DataColumn(centered_text("السعر الكامل", style=self.text_style)),
                ft.DataColumn(centered_text("الاستهلاك", style=self.text_style)),
            ],
            rows=[
                ft.DataRow(cells=[
                    ft.DataCell(centered_text(row[0], style=self.text_style)),
                    ft.DataCell(centered_text(str(row[1]), style=self.text_style)),
                    ft.DataCell(centered_text(str(row[2]), style=self.text_style)),
                    ft.DataCell(centered_text(str(row[3]), style=self.text_style)),
                    ft.DataCell(centered_text(str(row[4]), style=self.text_style)),
                ]) for row in expenses
            ]
        )
        
        # إنشاء أزرار التصدير والرجوع
        export_button = create_button(
            text="تصدير إلى Excel",
            on_click=lambda e: export_to_excel(self, df, "تقرير_المصروفات"),
            bgcolor=ft.colors.BLUE_700,
            width=200
        )
        back_button = create_button(
            text="رجوع",
            on_click=lambda e: self.navigate_to_reports_current(),
            bgcolor=ft.colors.RED_700,
            width=200
        )
        
        # وضع الأزرار في صف مع مسافة بينهما
        buttons_row = ft.Row(
            [export_button, back_button],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10
        )
        
        # تنظيم المحتوى
        content = ft.Column(
            [
                ft.Text("تقرير المصروفات", style=self.title_style, color="white"),
                ft.Container(height=20),
                ft.ListView(controls=[data_table], expand=True, auto_scroll=False),
                ft.Container(height=20),
                ft.Row(
                    [
                        ft.Text(
                            f"إجمالي المصروفات: {total_expenses:.2f}",
                            style=self.text_style,
                            color="white",
                            text_align=ft.TextAlign.CENTER
                        ),
                        ft.Text(
                            f"إجمالي الاستهلاك: {total_consumption:.2f}",
                            style=self.text_style,
                            color="white",
                            text_align=ft.TextAlign.CENTER
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=20
                ),
                ft.Container(height=20),
                buttons_row,
                ft.Container(height=20),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        
        # تحديث الصفحة مع إضافة مسافة من الحواف
        self.page.clean()
        self.page.add(ft.Container(
            content=content,
            image_src=self.background_image.src,
            image_fit=ft.ImageFit.COVER,
            expand=True,
            padding=20  # إضافة مسافة من حدود النافذة
        ))
        self.page.update()
        
    except Exception as e:
        self.show_snackbar(f"خطأ أثناء جلب تقرير المصروفات: {str(e)}")
