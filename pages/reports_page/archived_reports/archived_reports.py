import flet as ft
from utils.button_utils import create_button
import pandas as pd
from datetime import datetime
import os
import logging

class ArchivedReportsPage:
    def __init__(self, page, background_image, db, navigate=None):
        self.page = page
        self.background_image = background_image
        self.db = db
        self.navigate = navigate
        self.text_style = ft.TextStyle(size=15, font_family="DancingScript")
        self.title_style = ft.TextStyle(size=28, weight=ft.FontWeight.BOLD, font_family="DancingScript")
        self._init_ui_components()

    def _init_ui_components(self):
        self.archive_dropdown = ft.Dropdown(
            label="اختر الفترة",
            width=300,
            bgcolor=ft.colors.WHITE,
            on_change=self.update_members,
            options=[],
            value=None,
            hint_text="اختر من القائمة",
        )
        self.result_table = ft.DataTable(
            columns=[ft.DataColumn(ft.Text("جاري التحميل...", style=self.text_style))],
            rows=[],
            visible=False
        )
        self.rows_per_page = 50
        self.current_page = 1
        self.total_rows = 0

    def set_navigate(self, navigate):
        self.navigate = navigate

    def create_button(text, on_click, bgcolor, padding=10, width=None):
        return ft.ElevatedButton(
            text=text,
            on_click=on_click,
            bgcolor=bgcolor,
            style=ft.ButtonStyle(
                padding=padding,
                overlay_color=ft.colors.with_opacity(0.1, bgcolor)
            ),
            width=width
        )

    def get_content(self):
        self.load_archive_periods()
        title = ft.Text(
            "تقارير الأشهر السابقة", 
            style=self.title_style, 
            color="white", 
            text_align=ft.TextAlign.CENTER
        )
        
        show_report_button = create_button(
            text="عرض التقرير",
            on_click=lambda e: self.show_report(e),
            bgcolor=ft.colors.GREEN
        )
        
        archive_data_button = create_button(
            text="بيانات الأرشيف",
            on_click=lambda e: self.navigate_to("archived_data"),
            bgcolor=ft.colors.BLUE,
            width=150
        )
        
        back_button = create_button(
            text="رجوع",
            on_click=lambda e: self.navigate_to_parent(),
            bgcolor=ft.colors.RED
        )

        dropdown_row = ft.Row(
            [self.archive_dropdown], 
            alignment=ft.MainAxisAlignment.CENTER
        )
        
        buttons_row = ft.Row(
            [
                show_report_button,
                archive_data_button,
                back_button
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20,
        )

        table_container = ft.Container(
            content=self.result_table,
            padding=10,
            bgcolor=ft.colors.SURFACE_VARIANT,
            border_radius=10,
            visible=self.result_table.visible
        )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(height=20),
                    title,
                    ft.Container(height=20),
                    dropdown_row,
                    ft.Container(height=20),
                    buttons_row,
                    ft.Container(height=20),
                    table_container,
                ],
                alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO,
            ),
            image_src=self.background_image.src,
            image_fit=ft.ImageFit.COVER,
            expand=True,
        )

    def load_archive_periods(self):
        try:
            query = """
                SELECT archive_key_id, archive_name, start_date, end_date, archived_at
                FROM archive_keys
                ORDER BY archived_at DESC
            """
            rows = self.db.fetch_all(query)
            self.archive_dropdown.options = [
                ft.dropdown.Option(
                    key="",
                    text="--- اختر فترة ---"
                )
            ]
            if not rows:
                self.archive_dropdown.options = [
                    ft.dropdown.Option("لا توجد فترات مؤرشفة", disabled=True)
                ]
            else:
                self.archive_dropdown.options = [
                    ft.dropdown.Option(
                        key=str(archive_key_id),
                        text=f"ID: {archive_key_id} | {end_date}"
                    )
                    for archive_key_id, archive_name, start_date, end_date, archived_at in rows
                ]
                self.archive_dropdown.value = None
            self.page.update()
        except Exception as e:
            logging.error(f"خطأ في جلب فترات الأرشيف: {e}")
            self.show_snackbar("حدث خطأ في جلب فترات الأرشيف!")

    def update_members(self, e):
        pass

    def show_report(self, e, page_number=1):
        if not self.archive_dropdown.value:
            self.show_snackbar("اختار فترة أرشيف أولاً!")
            return
        
        archive_key_id = int(self.archive_dropdown.value)
        
        try:
            period_data = self.db.fetch_all(
                "SELECT archive_name, start_date, end_date, archived_at FROM archive_keys WHERE archive_key_id = ?",
                [archive_key_id]
            )
            
            if not period_data:
                self.show_snackbar("لا توجد بيانات للفترة المحددة!")
                return
                
            archive_name, start_date, end_date, archived_at = period_data[0]

            closure_ids = self.db.fetch_all(
                "SELECT closure_id, closure_date FROM monthly_closures WHERE archive_key_id = ?",
                [archive_key_id]
            )
            
            if not closure_ids:
                self.show_snackbar("لا توجد تقارير مقفلة لهذه الفترة!")
                return

            query = """
                SELECT 
                    m.name, 
                    SUM(s.total_meals) as total_meals,
                    SUM(s.total_drinks) as total_drinks,
                    SUM(s.total_miscellaneous) as total_misc,
                    SUM(s.total_consumption) as total_consumption,
                    SUM(s.total_contribution) as total_contribution,
                    SUM(s.remaining_cash) as remaining_cash
                FROM closure_summary_archive s
                JOIN members_archive m ON s.member_id = m.member_id
                WHERE s.closure_id IN ({})
                GROUP BY m.name
                ORDER BY m.name
            """.format(','.join(['?']*len(closure_ids)))
            
            params = [cid[0] for cid in closure_ids]
            rows = self.db.fetch_all(query, params)
            
            if not rows:
                self.show_snackbar("لا توجد بيانات تفصيلية للتقارير المقفلة!")
                return

            totals_data = self.db.fetch_all("""
                SELECT total_meals, total_drinks, total_misc, total_consumption, 
                       total_contributions, remaining_items, remaining_cash
                FROM monthly_totals_archive
                WHERE archive_key_id = ?
                ORDER BY recorded_at DESC
                LIMIT 1
            """, [archive_key_id])

            if not totals_data:
                self.show_snackbar("لم يتم العثور على إجماليات محفوظة لهذه الفترة!")
                return

            total_meals, total_drinks, total_misc, total_consumption, total_contributions, total_remaining_items, total_remaining = totals_data[0]

            header_style = ft.TextStyle(
                size=16,
                weight=ft.FontWeight.BOLD,
                font_family="DancingScript",
                color=ft.colors.WHITE
            )
            
            cell_style = ft.TextStyle(
                size=14,
                font_family="DancingScript",
                color=ft.colors.BLACK
            )

            def centered_text(text, style=None):
                return ft.Container(
                    content=ft.Text(text, style=style),
                    alignment=ft.alignment.center,
                    padding=10,
                    expand=True
                )

            summary_table = ft.DataTable(
                columns=[
                    ft.DataColumn(centered_text("الاسم", header_style)),
                    ft.DataColumn(centered_text("إجمالي الوجبات", header_style)),
                    ft.DataColumn(centered_text("إجمالي المشروبات", header_style)),
                    ft.DataColumn(centered_text("إجمالي النثريات", header_style)),
                    ft.DataColumn(centered_text("إجمالي الاستهلاك", header_style)),
                    ft.DataColumn(centered_text("إجمالي المساهمة", header_style)),
                ],
                rows=[
                    ft.DataRow(
                        cells=[
                            ft.DataCell(centered_text(row[0], cell_style)),
                            ft.DataCell(centered_text(f"{row[1]:.2f}", cell_style)),
                            ft.DataCell(centered_text(f"{row[2]:.2f}", cell_style)),
                            ft.DataCell(centered_text(f"{row[3]:.2f}", cell_style)),
                            ft.DataCell(centered_text(f"{row[4]:.2f}", cell_style)),
                            ft.DataCell(centered_text(f"{row[5]:.2f}", cell_style)),
                        ]
                    ) for row in rows
                ],
                column_spacing=5,
                heading_row_height=50,
                data_row_min_height=40,
                horizontal_margin=10,
                heading_row_color=ft.colors.BLUE,
                width=min(1000, self.page.width * 0.99),
                border=ft.border.all(1, ft.colors.GREY_400),
                border_radius=10,
            )

            totals_table = ft.DataTable(
                columns=[
                    ft.DataColumn(centered_text("المجموع", header_style)),
                    ft.DataColumn(centered_text("إجمالي الوجبات", header_style)),
                    ft.DataColumn(centered_text("إجمالي المشروبات", header_style)),
                    ft.DataColumn(centered_text("إجمالي النثريات", header_style)),
                    ft.DataColumn(centered_text("إجمالي الاستهلاك", header_style)),
                    ft.DataColumn(centered_text("إجمالي المساهمة", header_style)),
                    ft.DataColumn(centered_text("النقدي المتبقي", header_style)),
                ],
                rows=[
                    ft.DataRow(
                        cells=[
                            ft.DataCell(centered_text("الإجمالي", cell_style)),
                            ft.DataCell(centered_text(f"{total_meals:.2f}", cell_style)),
                            ft.DataCell(centered_text(f"{total_drinks:.2f}", cell_style)),
                            ft.DataCell(centered_text(f"{total_misc:.2f}", cell_style)),
                            ft.DataCell(centered_text(f"{total_consumption:.2f}", cell_style)),
                            ft.DataCell(centered_text(f"{total_contributions:.2f}", cell_style)),
                            ft.DataCell(centered_text(f"{total_remaining:.2f}", cell_style)),
                        ]
                    )
                ],
                column_spacing=10,
                heading_row_height=55,
                data_row_min_height=45,
                horizontal_margin=15,
                heading_row_color=ft.colors.BLUE,
                width=min(1000, self.page.width * 0.99),
                border=ft.border.all(1, ft.colors.GREY_400),
                border_radius=10,
            )

            export_button = create_button(
                "تصدير إلى Excel", 
                lambda e: self.export_to_excel(archive_key_id),
                bgcolor=ft.colors.GREEN_700,
                width=200
            )
            
            close_button = create_button(
                "رجوع", 
                lambda e: self.navigate_to_reports_archived(),
                bgcolor=ft.colors.RED_700,
                width=200
            )

            report_view = ft.Container(
                content=ft.Column(
                    [
                        ft.Container(
                            content=ft.Column([
                                ft.Text("تقرير الاستهلاك الشهري", 
                                       style=ft.TextStyle(size=24, weight=ft.FontWeight.BOLD, 
                                                         color=ft.colors.BLUE_800)),
                                ft.Text(f"اسم الأرشيف: {archive_name}", 
                                       style=ft.TextStyle(size=16)),
                                ft.Text(f"الفترة: من {start_date} إلى {end_date}", 
                                       style=ft.TextStyle(size=16)),
                                ft.Text(f"تاريخ الأرشفة: {archived_at}", 
                                       style=ft.TextStyle(size=16)),
                            ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            padding=20,
                            alignment=ft.alignment.center
                        ),
                        
                        ft.Divider(height=20, color=ft.colors.GREY),
                        
                        ft.Container(
                            content=ft.Column([
                                ft.Text("تفاصيل الاستهلاك حسب العضو", 
                                       style=ft.TextStyle(size=18, weight=ft.FontWeight.BOLD)),
                                ft.Container(
                                    content=summary_table,
                                    padding=5,
                                    margin=ft.margin.symmetric(horizontal=10),
                                    alignment=ft.alignment.center,
                                    bgcolor=ft.colors.WHITE,
                                    border_radius=5,
                                    width=min(1100, self.page.width * 0.99),
                                )
                            ], spacing=30),
                        ),
                        
                        ft.Divider(height=30, color=ft.colors.GREY),
                        
                        ft.Container(
                            content=ft.Column([
                                ft.Text("إجماليات الفترة", 
                                       style=ft.TextStyle(size=18, weight=ft.FontWeight.BOLD)),
                                ft.Container(
                                    content=totals_table,
                                    padding=5,
                                    margin=ft.margin.symmetric(horizontal=10),
                                    alignment=ft.alignment.center,
                                    bgcolor=ft.colors.WHITE,
                                    border_radius=5,
                                )
                            ], spacing=30),
                        ),
                        
                        ft.Container(height=30),
                        
                        ft.Row(
                            [export_button, close_button],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=50
                        ),
                        
                        ft.Container(height=20)
                    ],
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10
                ),
                padding=ft.padding.symmetric(vertical=20, horizontal=10),
                expand=True,
                bgcolor=ft.colors.GREY_100
            )

            self.page.clean()
            self.page.add(report_view)
            self.page.update()

        except Exception as e:
            logging.error(f"خطأ في جلب تقرير الأرشيف: {str(e)}", exc_info=True)
            self.show_snackbar(f"حدث خطأ في جلب التقرير: {str(e)}")

    def export_to_excel(self, archive_key_id):
        try:
            archive_info = self.db.fetch_all("""
                SELECT archive_name, start_date, end_date, archived_at 
                FROM archive_keys 
                WHERE archive_key_id = ?
            """, [archive_key_id])

            if not archive_info:
                self.show_snackbar("لا توجد معلومات عن الفترة المحددة!")
                return

            archive_name, start_date, end_date, archived_at = archive_info[0]

            closure_ids = self.db.fetch_all(
                "SELECT closure_id FROM monthly_closures WHERE archive_key_id = ?",
                [archive_key_id]
            )
            if not closure_ids:
                self.show_snackbar("لا توجد تقارير مقفلة لهذه الفترة!")
                return

            closure_ids_str = ','.join(['?'] * len(closure_ids))
            closure_ids_values = [cid[0] for cid in closure_ids]

            rows = self.db.fetch_all(f"""
                SELECT 
                    m.name, 
                    SUM(s.total_meals), SUM(s.total_drinks), SUM(s.total_miscellaneous),
                    SUM(s.total_consumption), SUM(s.total_contribution), SUM(s.remaining_cash)
                FROM closure_summary_archive s
                JOIN members_archive m ON s.member_id = m.member_id
                WHERE s.closure_id IN ({closure_ids_str})
                GROUP BY m.name
                ORDER BY m.name
            """, closure_ids_values)

            if not rows:
                self.show_snackbar("لا توجد بيانات للتصدير!")
                return

            summary_df = pd.DataFrame(rows, columns=[
                "الاسم", "عدد الوجبات", "عدد المشروبات", "النثريات", "الاستهلاك", "المساهمة", "المتبقي"
            ])

            totals_data = self.db.fetch_all("""
                SELECT total_meals, total_drinks, total_misc, total_consumption, 
                       total_contributions, remaining_items, remaining_cash
                FROM monthly_totals_archive
                WHERE archive_key_id = ?
                ORDER BY recorded_at DESC
                LIMIT 1
            """, [archive_key_id])

            if not totals_data:
                self.show_snackbar("لا توجد بيانات إجمالية للتصدير!")
                return

            total_meals, total_drinks, total_misc, total_consumption, total_contributions, total_remaining_items, total_remaining = totals_data[0]

            totals_df = pd.DataFrame([{
                "إجمالي الوجبات": total_meals,
                "إجمالي المشروبات": total_drinks,
                "إجمالي النثريات": total_misc,
                "إجمالي الاستهلاك": total_consumption,
                "إجمالي المساهمة": total_contributions,
                "قيمة الأصناف المتبقية": total_remaining_items,
                "النقدي المتبقي": total_remaining,
            }])

            info_df = pd.DataFrame([
                ["اسم الأرشيف", archive_name],
                ["الفترة", f"من {start_date} إلى {end_date}"],
                ["تاريخ الأرشفة", archived_at],
                ["عدد الأعضاء", len(summary_df)],
            ], columns=["المعلومة", "القيمة"])

            reports_dir = "reports"
            if not os.path.exists(reports_dir):
                os.makedirs(reports_dir)

            filename = f"{reports_dir}/تقرير_مؤرشف_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

            with pd.ExcelWriter(filename, engine="openpyxl") as writer:
                info_df.to_excel(writer, sheet_name="معلومات", index=False)
                summary_df.to_excel(writer, sheet_name="تفاصيل الأعضاء", index=False)
                totals_df.to_excel(writer, sheet_name="الإجماليات", index=False)

            self.show_snackbar(f"تم حفظ التقرير في: {filename}")

        except Exception as e:
            logging.error(f"خطأ أثناء تصدير التقرير: {e}", exc_info=True)
            self.show_snackbar("حدث خطأ أثناء تصدير التقرير إلى Excel.")

    def show_snackbar(self, message):
        self.page.snack_bar = ft.SnackBar(ft.Text(message, style=self.text_style))
        self.page.snack_bar.open = True
        self.page.update()

    def navigate_to(self, page_name):
        if not self.archive_dropdown.value:
            self.show_snackbar("اختار فترة أرشيف أولاً!")
            return

        archive_key_id = int(self.archive_dropdown.value)
        self.page.clean()
        from pages.reports_page.archived_reports.archived_data import ArchivedDataPage
        self.page.add(ArchivedDataPage(self.page, self.background_image, self.db, self.navigate, archive_key_id).get_content())
        self.page.update()
        
    def navigate_to_parent(self):
        self.page.clean()
        from pages.reports_page.reports_page import ReportsPage
        self.page.add(ReportsPage(self.page, self.background_image, self.db, self.navigate).get_content())
        self.page.update()

    def navigate_to_reports_archived(self):
        self.page.clean()
        from pages.reports_page.archived_reports.archived_reports import ArchivedReportsPage
        self.page.add(ArchivedReportsPage(self.page, self.background_image, self.db, self.navigate).get_content())
        self.page.update()
