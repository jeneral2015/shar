import flet as ft
import pandas as pd
from datetime import datetime
from utils.button_utils import create_button
from pages.reports_page.current_reports.export_to_excel import export_to_excel

def show_meals_report(self):
    """عرض تقرير الوجبات"""
    try:
        query = f"""
            SELECT m.name, mr.meal_type, mr.date, mr.final_cost
            FROM meal_records mr
            JOIN members m ON mr.member_id = m.member_id
        """
        meals = self.db.fetch_all(query)
        
        # التحقق من وجود بيانات
        if not meals:
            self.show_snackbar("لا توجد بيانات وجبات")
            return
        
        # إنشاء DataFrame
        df = pd.DataFrame(meals, columns=["اسم المشترك", "نوع الوجبة", "التاريخ", "التكلفة"])
        total_cost = df["التكلفة"].sum()
        
        # حساب إجمالي عدد الوجبات لكل نوع
        breakfast_count = df[df["نوع الوجبة"] == "فطور"].shape[0]
        lunch_count = df[df["نوع الوجبة"] == "غداء"].shape[0]
        dinner_count = df[df["نوع الوجبة"] == "عشاء"].shape[0]
        
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
                ft.DataColumn(centered_text("نوع الوجبة", style=self.text_style)),
                ft.DataColumn(centered_text("التاريخ", style=self.text_style)),
                ft.DataColumn(centered_text("التكلفة", style=self.text_style)),
            ],
            rows=[
                ft.DataRow(cells=[
                    ft.DataCell(centered_text(row[0], style=self.text_style)),
                    ft.DataCell(centered_text(row[1], style=self.text_style)),
                    ft.DataCell(centered_text(row[2], style=self.text_style)),
                    ft.DataCell(centered_text(str(row[3]), style=self.text_style)),
                ]) for row in meals
            ]
        )
        
        # إنشاء أزرار
        export_button = create_button(
            text="تصدير إلى Excel",
            on_click=lambda e: export_to_excel(self, df, "تقرير_الوجبات"),
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
                ft.Text("تقرير الوجبات", style=self.title_style, color="white"),
                ft.Container(height=20),
                ft.ListView(controls=[data_table], expand=True, auto_scroll=False),
                ft.Container(height=20),
                ft.Row(
                    [
                        ft.Text(
                            f"إجمالي التكلفة: {total_cost:.2f}",
                            style=self.text_style,
                            color="white",
                            text_align=ft.TextAlign.CENTER
                        ),
                        ft.Text(
                            f"إجمالي الفطور: {breakfast_count}",
                            style=self.text_style,
                            color="white",
                            text_align=ft.TextAlign.CENTER
                        ),
                        ft.Text(
                            f"إجمالي الغداء: {lunch_count}",
                            style=self.text_style,
                            color="white",
                            text_align=ft.TextAlign.CENTER
                        ),
                        ft.Text(
                            f"إجمالي العشاء: {dinner_count}",
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
        self.show_snackbar(f"خطأ أثناء جلب تقرير الوجبات: {str(e)}")
