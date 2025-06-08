import flet as ft
import pandas as pd
from datetime import datetime
from utils.button_utils import create_button
from pages.reports_page.current_reports.export_to_excel import export_to_excel

def show_drinks_report(self):
    """عرض تقرير المشروبات"""
    try:
        query = f"""
            SELECT m.name, dr.drink_name, dr.quantity, dr.date, dr.total_cost
            FROM drink_records dr
            JOIN members m ON dr.member_id = m.member_id
        """
        drinks = self.db.fetch_all(query)
        
        # التحقق من وجود بيانات
        if not drinks:
            self.show_snackbar("لا توجد بيانات مشروبات لهذا الشهر")
            return
        
        # إنشاء DataFrame
        df = pd.DataFrame(drinks, columns=["اسم المشترك", "اسم المشروب", "الكمية", "التاريخ", "التكلفة"])
        total_cost = df["التكلفة"].sum()
        
        # دالة لتوسيط النصوص
        def centered_text(text, style=None):
            return ft.Container(
                content=ft.Text(text, style=style),
                alignment=ft.alignment.center,
                padding=10,
                expand=True
            )
        
        # إنشاء جدول Flet
        data_table = ft.DataTable(
            bgcolor=ft.colors.WHITE,
            heading_row_color=ft.colors.BLUE,
            border=ft.border.all(1, ft.colors.BLACK),
            horizontal_lines=ft.BorderSide(1, ft.colors.BLACK),
            vertical_lines=ft.BorderSide(1, ft.colors.BLACK),
            column_spacing=0,
            columns=[
                ft.DataColumn(centered_text("اسم المشترك", style=self.text_style)),
                ft.DataColumn(centered_text("اسم المشروب", style=self.text_style)),
                ft.DataColumn(centered_text("الكمية", style=self.text_style)),
                ft.DataColumn(centered_text("التاريخ", style=self.text_style)),
                ft.DataColumn(centered_text("التكلفة", style=self.text_style)),
            ],
            rows=[
                ft.DataRow(cells=[
                    ft.DataCell(centered_text(row[0], style=self.text_style)),
                    ft.DataCell(centered_text(row[1], style=self.text_style)),
                    ft.DataCell(centered_text(str(row[2]), style=self.text_style)),
                    ft.DataCell(centered_text(row[3], style=self.text_style)),
                    ft.DataCell(centered_text(str(row[4]), style=self.text_style)),
                ]) for row in drinks
            ]
        )
        
        # إنشاء أزرار
        export_button = create_button(
            text="تصدير إلى Excel",
            on_click=lambda e: export_to_excel(self, df, "تقرير_المشروبات"),
            bgcolor=ft.colors.BLUE_700,
            width=200
        )
        back_button = create_button(
            text="رجوع",
            on_click=lambda e: self.navigate_to_reports_current(),
            bgcolor=ft.colors.RED_700,
            width=200
        )
        
        # وضع الأزرار في صف
        buttons_row = ft.Row(
            [export_button, back_button],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10
        )
        
        # تنظيم المحتوى
        content = ft.Column(
            [
                ft.Text("تقرير المشروبات", style=self.title_style, color="white"),
                ft.Container(height=20),
                ft.ListView(controls=[data_table], expand=True, auto_scroll=False),
                ft.Container(height=20),
                ft.Text(
                    f"إجمالي التكلفة: {total_cost:.2f}",
                    style=self.text_style,
                    color="white",
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=20),
                buttons_row,
                ft.Container(height=20),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        
        # تحديث الصفحة
        self.page.clean()
        self.page.add(ft.Container(
            content=content,
            image_src=self.background_image.src,
            image_fit=ft.ImageFit.COVER,
            expand=True,
            padding=20
        ))
        self.page.update()
        
    except Exception as e:
        self.show_snackbar(f"خطأ أثناء جلب تقرير المشروبات: {str(e)}")
