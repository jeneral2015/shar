import flet as ft
import pandas as pd
from datetime import datetime
from utils.button_utils import create_button
from pages.reports_page.current_reports.export_to_excel import export_to_excel

def show_member_consumption(self, archive_key_id):
    """عرض تقرير استهلاك مشترك محدد لفترة أرشيف محددة"""
    try:
        subscribers = self.db.fetch_all("SELECT member_id, name FROM members_archive WHERE archive_key_id = ?", [archive_key_id])
        dropdown = ft.Dropdown(
            label="اختر المشترك",
            bgcolor=ft.colors.WHITE,
            options=[ft.dropdown.Option(key=str(row[0]), text=row[1]) for row in subscribers],
            width=300,
            text_style=self.text_style,
            color="BLACK"
        )
        
        def on_submit(e):
            subscriber_id = dropdown.value
            if not subscriber_id:
                self.show_snackbar("يرجى اختيار مشترك")
                return
            
            # تحويل subscriber_id إلى عدد صحيح
            subscriber_id = int(subscriber_id)
            
            query = f"""
                SELECT m.name, 
                       COALESCE(mr.meal_type, 'غير محدد') as item, 
                       COALESCE(mr.final_cost, 0) as cost, 
                       mr.date
                FROM meal_records_archive mr
                JOIN members_archive m ON mr.member_id = m.member_id
                WHERE mr.member_id = ? AND mr.archive_key_id = ?
                UNION ALL
                SELECT m.name, 
                       dr.drink_name as item, 
                       dr.total_cost as cost, 
                       dr.date
                FROM drink_records_archive dr
                JOIN members_archive m ON dr.member_id = m.member_id
                WHERE dr.member_id = ? AND dr.archive_key_id = ?
                UNION ALL
                SELECT m.name, 
                       'نثريات' as item, 
                       mc.misc_amount as cost, 
                       mc.distribution_date as date
                FROM miscellaneous_contributions_archive mc
                JOIN members_archive m ON mc.member_id = m.member_id
                WHERE mc.member_id = ? AND mc.archive_key_id = ?
            """
            consumption = self.db.fetch_all(query, (subscriber_id, archive_key_id, subscriber_id, archive_key_id, subscriber_id, archive_key_id))
            
            # التحقق من وجود بيانات
            if not consumption:
                self.show_snackbar("لا توجد بيانات لهذا المشترك في هذه الفترة")
                return
            
            df = pd.DataFrame(consumption, columns=["اسم المشترك", "البند", "التكلفة", "التاريخ"])
            total_cost = df["التكلفة"].sum()
            
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
                    ft.DataColumn(centered_text("اسم المشترك", style=self.text_style)),
                    ft.DataColumn(centered_text("البند", style=self.text_style)),
                    ft.DataColumn(centered_text("التكلفة", style=self.text_style)),
                    ft.DataColumn(centered_text("التاريخ", style=self.text_style)),
                ],
                rows=[
                    ft.DataRow(
                        cells=[
                            ft.DataCell(centered_text(row[0], style=self.text_style)),
                            ft.DataCell(centered_text(row[1], style=self.text_style)),
                            ft.DataCell(centered_text(str(row[2]), style=self.text_style)),
                            ft.DataCell(centered_text(row[3], style=self.text_style)),
                        ],
                        color=ft.colors.GREY_100 if i % 2 == 0 else ft.colors.WHITE
                    ) for i, row in enumerate(consumption)
                ]
            )
            
            # إنشاء أزرار
            export_button = create_button(
                text="تصدير إلى Excel",
                on_click=lambda e: export_to_excel(self, df, f"تقرير_استهلاك_مشترك_{subscriber_id}_أرشيف_{archive_key_id}"),
                bgcolor=ft.colors.BLUE_700,
                width=200
            )
            back_button = create_button(
                text="رجوع",
                on_click=lambda e: show_member_consumption(self, self.archive_key_id),  # العودة إلى صفحة الأرشيف
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
                            f"إجمالي التكلفة: {total_cost:.2f}",
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
                height=self.page.height * 0.5 if self.page.height else 600,  # استعادة الارتفاع الأصلي
                width=self.page.width if self.page.width else 800  # ضبط العرض بناءً على الشاشة
            )
            
            # تنظيم المحتوى الكلي
            content = ft.Column(
                [
                    ft.Text("تقرير استهلاك مشترك", style=self.title_style, color="white"),
                    ft.Container(height=5),
                    dropdown,
                    ft.Container(height=5),
                    scrollable_content,
                    ft.Container(height=5),
                    buttons_row,
                    ft.Container(height=5),
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
        
        # إنشاء زر العرض
        submit_button = create_button(
            text="عرض التقرير",
            on_click=on_submit,
            bgcolor=ft.colors.GREEN_700,
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
            [submit_button, back_button],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10
        )
        
        # تنظيم المحتوى الأولي
        content = ft.Column(
            [
                ft.Text("تقرير استهلاك مشترك", style=self.title_style, color="white"),
                ft.Container(height=10),
                dropdown,
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
        self.show_snackbar(f"خطأ أثناء جلب تقرير المشترك: {str(e)}")
