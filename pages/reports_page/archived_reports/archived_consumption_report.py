import flet as ft
import pandas as pd
from datetime import datetime
from utils.button_utils import create_button
from pages.reports_page.current_reports.export_to_excel import export_to_excel

def show_consumption_report(self, archive_key_id):
    """عرض تقرير استهلاك المشتركين لفترة أرشيف محددة"""
    try:
        query = f"""
            SELECT m.name, 
                   m.rank,
                   COALESCE(csa.total_meals, 0) as total_meals,
                   COALESCE(csa.total_drinks, 0) as total_drinks,
                   COALESCE(csa.total_miscellaneous, 0) as total_miscellaneous,
                   COALESCE(csa.total_consumption, 0) as total_consumption
            FROM closure_summary_archive csa
            JOIN members_archive m ON csa.member_id = m.member_id
            WHERE csa.archive_key_id = ? AND m.archive_key_id = ?
        """
        consumption = self.db.fetch_all(query, (archive_key_id, archive_key_id))
        
        # التحقق من وجود بيانات
        if not consumption:
            self.show_snackbar("لا توجد بيانات استهلاك لهذه الفترة")
            return
        
        # إنشاء DataFrame مع عمود المسلسل
        df = pd.DataFrame(consumption, columns=["الاسم", "الرتبة", "إجمالي الوجبات", "إجمالي المشروبات", "إجمالي النثريات", "إجمالي الاستهلاك"])
        df.insert(0, "المسلسل", range(1, len(df) + 1))  # إضافة عمود المسلسل
        
        # حساب الإجماليات
        total_meals = df["إجمالي الوجبات"].sum()
        total_drinks = df["إجمالي المشروبات"].sum()
        total_misc = df["إجمالي النثريات"].sum()
        total_consumption = df["إجمالي الاستهلاك"].sum()
        
        # دالة لتوسيط النصوص
        def centered_text(text, style=None):
            return ft.Container(
                content=ft.Text(text, style=style),
                alignment=ft.alignment.center,
                padding=10,
                expand=True
            )
        
        # إنشاء جدول Flet مع ألوان متناوبة
        data_table = ft.DataTable(
            bgcolor=ft.colors.WHITE,
            heading_row_color=ft.colors.BLUE,
            border=ft.border.all(1, ft.colors.BLACK),
            horizontal_lines=ft.BorderSide(1, ft.colors.BLACK),
            vertical_lines=ft.BorderSide(1, ft.colors.BLACK),
            column_spacing=0,
            columns=[
                ft.DataColumn(centered_text("المسلسل", style=self.text_style)),
                ft.DataColumn(centered_text("الرتبة", style=self.text_style)),
                ft.DataColumn(centered_text("الاسم", style=self.text_style)),
                ft.DataColumn(centered_text("إجمالي الوجبات", style=self.text_style)),
                ft.DataColumn(centered_text("إجمالي المشروبات", style=self.text_style)),
                ft.DataColumn(centered_text("إجمالي النثريات", style=self.text_style)),
                ft.DataColumn(centered_text("إجمالي الاستهلاك", style=self.text_style)),
            ],
            rows=[
                ft.DataRow(
                    cells=[
                        ft.DataCell(centered_text(str(i + 1), style=self.text_style)),
                        ft.DataCell(centered_text(row[1], style=self.text_style)),
                        ft.DataCell(centered_text(row[0], style=self.text_style)),
                        ft.DataCell(centered_text(str(row[2]), style=self.text_style)),
                        ft.DataCell(centered_text(str(row[3]), style=self.text_style)),
                        ft.DataCell(centered_text(str(row[4]), style=self.text_style)),
                        ft.DataCell(centered_text(str(row[5]), style=self.text_style)),
                    ],
                    color=ft.colors.GREY_100 if i % 2 == 0 else ft.colors.WHITE
                ) for i, row in enumerate(consumption)
            ]
        )
        
        # إنشاء أزرار
        export_button = create_button(
            text="تصدير إلى Excel",
            on_click=lambda e: export_to_excel(self, df, f"تقرير_استهلاك_المشتركين_أرشيف_{archive_key_id}"),
            bgcolor=ft.colors.BLUE_700,
            width=200
        )
        back_button = create_button(
            text="رجوع",
            on_click=lambda e: self.navigate_to_reports_current(),  # العودة إلى صفحة الأرشيف
            bgcolor=ft.colors.RED_700,
            width=200
        )
        
        # وضع الأزرار في صف
        buttons_row = ft.Row(
            [export_button, back_button],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10
        )
        
        # تنظيم المحتوى القابل للتمرير
        scrollable_content = ft.Container(
            content=ft.Column(
                controls=[
                    data_table,
                    ft.Container(height=10),
                    ft.Text(
                        f"إجمالي الوجبات: {total_meals:.2f}, المشروبات: {total_drinks:.2f}, النثريات: {total_misc:.2f}, الاستهلاك: {total_consumption:.2f}",
                        style=self.text_style,
                        color="white",
                        text_align=ft.TextAlign.CENTER
                    ),
                    ft.Container(height=10),
                ],
                scroll=ft.ScrollMode.AUTO,
                alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            height=self.page.height * 0.6 if self.page.height else 600,  # ضبط الارتفاع بناءً على الشاشة
            width=self.page.width if self.page.width else 800  # ضبط العرض بناءً على الشاشة
        )
        
        # تنظيم المحتوى الكلي
        content = ft.Column(
            [
                ft.Text("تقرير استهلاك المشتركين", style=self.title_style, color="white"),
                ft.Container(height=10),
                scrollable_content,
                ft.Container(height=10),
                buttons_row,
                ft.Container(height=10),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        
        # تحديث الصفحة
        self.page.clean()
        self.page.add(ft.Container(
            content=content,
            image_src=self.background_image.src if hasattr(self, 'background_image') else None,
            image_fit=ft.ImageFit.COVER,
            expand=True,
            padding=20
        ))
        self.page.update()
        
    except Exception as e:
        self.show_snackbar(f"خطأ أثناء جلب تقرير الاستهلاك: {str(e)}")