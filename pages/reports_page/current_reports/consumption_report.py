import flet as ft
import pandas as pd
from datetime import datetime
from utils.button_utils import create_button
from pages.reports_page.current_reports.export_to_excel import export_to_excel

def show_consumption_report(self):
    """عرض تقرير استهلاك المشتركين"""
    try:
        query = f"""
            SELECT m.name, 
                   COALESCE(SUM(mr.final_cost), 0) as meal_cost,
                   COALESCE(SUM(dr.total_cost), 0) as drink_cost,
                   COALESCE(SUM(mc.misc_amount), 0) as misc_cost
            FROM members m
            LEFT JOIN meal_records mr ON m.member_id = mr.member_id
            LEFT JOIN drink_records dr ON m.member_id = dr.member_id
            LEFT JOIN miscellaneous_contributions mc ON m.member_id = mc.member_id
            GROUP BY m.member_id, m.name
        """
        consumption = self.db.fetch_all(query)
        
        # التحقق من وجود بيانات
        if not consumption:
            self.show_snackbar("لا توجد بيانات استهلاك لهذا الشهر")
            return
        
        # إنشاء DataFrame
        df = pd.DataFrame(consumption, columns=["اسم المشترك", "تكلفة الوجبات", "تكلفة المشروبات", "تكلفة النثريات"])
        total_meal_cost = df["تكلفة الوجبات"].sum()
        total_drink_cost = df["تكلفة المشروبات"].sum()
        total_misc_cost = df["تكلفة النثريات"].sum()
        
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
                ft.DataColumn(centered_text("تكلفة الوجبات", style=self.text_style)),
                ft.DataColumn(centered_text("تكلفة المشروبات", style=self.text_style)),
                ft.DataColumn(centered_text("تكلفة النثريات", style=self.text_style)),
            ],
            rows=[
                ft.DataRow(cells=[
                    ft.DataCell(centered_text(row[0], style=self.text_style)),
                    ft.DataCell(centered_text(str(row[1]), style=self.text_style)),
                    ft.DataCell(centered_text(str(row[2]), style=self.text_style)),
                    ft.DataCell(centered_text(str(row[3]), style=self.text_style)),
                ]) for row in consumption
            ]
        )
        
        # إنشاء أزرار
        export_button = create_button(
            text="تصدير إلى Excel",
            on_click=lambda e: export_to_excel(self, df, "تقرير_استهلاك_المشتركين"),
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
                ft.Text("تقرير استهلاك المشتركين", style=self.title_style, color="white"),
                ft.Container(height=20),
                ft.ListView(controls=[data_table], expand=True, auto_scroll=False),
                ft.Container(height=20),
                ft.Text(
                    f"إجمالي تكلفة الوجبات: {total_meal_cost:.2f}, المشروبات: {total_drink_cost:.2f}, النثريات: {total_misc_cost:.2f}",
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
        self.show_snackbar(f"خطأ أثناء جلب تقرير الاستهلاك: {str(e)}")
