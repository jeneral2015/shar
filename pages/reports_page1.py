import flet as ft
from database import DatabaseManager
from utils.button_utils import create_button
import pandas as pd
from datetime import datetime
import os
import logging

class ReportsPage:
    def __init__(self, page, background_image, db, navigate=None):
        self.page = page
        self.background_image = background_image
        self.db = db
        self.navigate = navigate
        self.text_style = ft.TextStyle(size=15, font_family="DancingScript")
        self.title_style = ft.TextStyle(size=28, weight=ft.FontWeight.BOLD, font_family="DancingScript")

    def set_navigate(self, navigate):
        self.navigate = navigate

    def get_content(self):
        title = ft.Text("التقارير", style=self.title_style, color="white", text_align=ft.TextAlign.CENTER)
        buttons_row = ft.Row(
            [
                create_button("الشهر الحالي", lambda e: self.navigate_to("current_reports"), bgcolor=ft.colors.GREEN),
                create_button("الأشهر السابقة", lambda e: self.navigate_to("archived_reports"), bgcolor=ft.colors.BLUE),
                create_button("رجوع", lambda e: self.navigate("main_page"), bgcolor=ft.colors.RED),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20,
        )
        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(height=20),
                    title,
                    ft.Container(height=150),
                    buttons_row,
                ],
                alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            image_src=self.background_image.src,
            image_fit=ft.ImageFit.COVER,
            expand=True,
        )

    def navigate_to(self, page_name):
        if page_name == "current_reports":
            self.page.clean()
            current_reports_page = CurrentReportsPage(self.page, self.background_image, self.db, self.navigate)
            current_reports_page.set_navigate(self.navigate)
            self.page.add(current_reports_page.get_content())
        elif page_name == "archived_reports":
            self.page.clean()
            archived_reports_page = ArchivedReportsPage(self.page, self.background_image, self.db, self.navigate)
            archived_reports_page.set_navigate(self.navigate)
            self.page.add(archived_reports_page.get_content())
        self.page.update()

class CurrentReportsPage:
    def __init__(self, page, background_image, db, navigate=None):
        self.page = page
        self.background_image = background_image
        self.db = db
        self.navigate = navigate
        self.text_style = ft.TextStyle(size=15, font_family="DancingScript")
        self.title_style = ft.TextStyle(size=28, weight=ft.FontWeight.BOLD, font_family="DancingScript")
        self.rows_per_page = 50  # عدد الصفوف في الصفحة
        self.current_page = 1
        self.total_rows = 0
        # الفلاتر
        self.date_from = ft.TextField(label="من تاريخ (YYYY-MM-DD)", width=150)
        self.date_to = ft.TextField(label="إلى تاريخ (YYYY-MM-DD)", width=150)
        self.data_type = ft.Dropdown(label="نوع البيانات", width=200, options=[
            ft.dropdown.Option("جميع البيانات", "all"),
            ft.dropdown.Option("المصاريف", "expenses"),
            ft.dropdown.Option("الأعضاء", "members"),
            ft.dropdown.Option("الوجبات", "meals"),
            ft.dropdown.Option("المشروبات", "drinks"),
            ft.dropdown.Option("النثريات", "misc"),
        ])
        self.member = ft.Dropdown(label="العضو", width=200)
        self.expense_type = ft.Dropdown(label="نوع المصروف", width=200, options=[
            ft.dropdown.Option("الكل", "all"),
            ft.dropdown.Option("عادي", "normal"),
            ft.dropdown.Option("نثريات", "misc"),
            ft.dropdown.Option("مشروبات", "drink"),
        ])
        # تهيئة الجدول بأعمدة افتراضية
        self.result_table = ft.DataTable(
            columns=[ft.DataColumn(ft.Text("جاري التحميل...", style=self.text_style))],
            rows=[],
            visible=False  # نخفي الجدول لحد ما يتحدد الأعمدة
        )
        self.pagination_row = ft.Row([], alignment=ft.MainAxisAlignment.CENTER)

    def set_navigate(self, navigate):
        self.navigate = navigate

    def get_content(self):
        self.load_members()
        title = ft.Text("تقارير الشهر الحالي", style=self.title_style, color="white", text_align=ft.TextAlign.CENTER)
        filters_row = ft.Row(
            [
                self.date_from,
                self.date_to,
                self.data_type,
                self.member,
                self.expense_type,
                create_button("عرض", self.show_report, bgcolor=ft.colors.GREEN),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10,
        )
        buttons_row = ft.Row(
            [
                create_button("تصدير إلى Excel", self.export_to_excel, bgcolor=ft.colors.BLUE),
                create_button("رجوع", lambda e: self.navigate_to_parent(), bgcolor=ft.colors.RED),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20,
        )
        # نعرض الجدول بس لو فيه أعمدة صالحة
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
                    filters_row,
                    ft.Container(height=20),
                    table_container,
                    ft.Container(height=10),
                    self.pagination_row,
                    ft.Container(height=20),
                    buttons_row,
                ],
                alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO,
            ),
            image_src=self.background_image.src,
            image_fit=ft.ImageFit.COVER,
            expand=True,
        )

    def load_members(self):
        query = "SELECT member_id, name FROM members ORDER BY name"
        try:
            members = self.db.fetch_all(query)
            self.member.options = [ft.dropdown.Option(name, str(member_id)) for member_id, name in members]
            self.member.options.insert(0, ft.dropdown.Option("الكل", "all"))
            self.member.value = "all"
        except Exception as e:
            logging.error(f"خطأ في جلب الأعضاء: {e}")
            self.show_snackbar("حدث خطأ في جلب الأعضاء!")

    def validate_date(self, date_str):
        try:
            if date_str:
                datetime.strptime(date_str, "%Y-%m-%d")
                return True
            return True  # التاريخ اختياري
        except ValueError:
            return False

    def show_report(self, e, page_number=1):
        if not self.validate_date(self.date_from.value) or not self.validate_date(self.date_to.value):
            self.show_snackbar("تنسيق التاريخ غلط! استخدم YYYY-MM-DD")
            return
        self.current_page = page_number
        data_type = self.data_type.value
        date_from = self.date_from.value
        date_to = self.date_to.value
        member_id = self.member.value
        expense_type = self.expense_type.value
        query = ""
        count_query = ""
        columns = []
        column_names = {}
        params = []
        try:
            if data_type == "all":
                query = """
                    SELECT m.name, COUNT(mr.meal_record_id) as total_meals, 
                           SUM(dr.quantity) as total_drinks, SUM(mc.misc_amount) as total_misc,
                           SUM(mr.final_cost + dr.total_cost + mc.misc_amount) as total_consumption,
                           m.contribution, (m.contribution - m.total_due) as remaining_cash
                    FROM members m
                    LEFT JOIN meal_records mr ON m.member_id = mr.member_id
                    LEFT JOIN drink_records dr ON m.member_id = dr.member_id
                    LEFT JOIN miscellaneous_contributions mc ON m.member_id = mc.member_id
                    WHERE 1=1
                """
                count_query = "SELECT COUNT(*) FROM members WHERE 1=1"
                if member_id != "all":
                    query += " AND m.member_id = ?"
                    count_query += " AND member_id = ?"
                    params.append(member_id)
                if date_from:
                    query += " AND (mr.date >= ? OR dr.date >= ? OR mc.distribution_date >= ?)"
                    params.extend([date_from] * 3)
                if date_to:
                    query += " AND (mr.date <= ? OR dr.date <= ? OR mc.distribution_date <= ?)"
                    params.extend([date_to] * 3)
                query += " GROUP BY m.member_id, m.name, m.contribution, m.total_due"
                columns = ["name", "total_meals", "total_drinks", "total_misc", "total_consumption", "contribution", "remaining_cash"]
                column_names = {
                    "name": "الاسم", "total_meals": "إجمالي الوجبات", "total_drinks": "إجمالي المشروبات",
                    "total_misc": "إجمالي النثريات", "total_consumption": "إجمالي الاستهلاك",
                    "contribution": "المساهمة", "remaining_cash": "النقدي المتبقي",
                }
            elif data_type == "expenses":
                query = """
                    SELECT item_name, quantity, price, total_price, consumption, remaining, 
                           CASE WHEN is_miscellaneous = 1 THEN 'نعم' ELSE 'لا' END as is_misc,
                           CASE WHEN is_drink = 1 THEN 'نعم' ELSE 'لا' END as is_drink,
                           date
                    FROM expenses
                    WHERE 1=1
                """
                count_query = "SELECT COUNT(*) FROM expenses WHERE 1=1"
                if expense_type != "all":
                    if expense_type == "misc":
                        query += " AND is_miscellaneous = 1"
                        count_query += " AND is_miscellaneous = 1"
                    elif expense_type == "drink":
                        query += " AND is_drink = 1"
                        count_query += " AND is_drink = 1"
                    else:
                        query += " AND is_miscellaneous = 0 AND is_drink = 0"
                        count_query += " AND is_miscellaneous = 0 AND is_drink = 0"
                if date_from:
                    query += " AND date >= ?"
                    count_query += " AND date >= ?"
                    params.append(date_from)
                if date_to:
                    query += " AND date <= ?"
                    count_query += " AND date <= ?"
                    params.append(date_to)
                columns = ["item_name", "quantity", "price", "total_price", "consumption", "remaining", "is_misc", "is_drink", "date"]
                column_names = {
                    "item_name": "اسم الصنف", "quantity": "الكمية", "price": "سعر الوحدة",
                    "total_price": "السعر الإجمالي", "consumption": "الاستهلاك", "remaining": "المتبقي",
                    "is_misc": "نثرية", "is_drink": "مشروب", "date": "التاريخ",
                }
            elif data_type == "members":
                query = """
                    SELECT name, rank, contribution, total_due, date,
                           (contribution - total_due) as balance
                    FROM members
                    WHERE 1=1
                """
                count_query = "SELECT COUNT(*) FROM members WHERE 1=1"
                if member_id != "all":
                    query += " AND member_id = ?"
                    count_query += " AND member_id = ?"
                    params.append(member_id)
                columns = ["name", "rank", "contribution", "total_due", "balance", "date"]
                column_names = {
                    "name": "الاسم", "rank": "الرتبة", "contribution": "المساهمة",
                    "total_due": "المستحق", "balance": "الرصيد", "date": "تاريخ التسجيل",
                }
            elif data_type == "meals":
                query = """
                    SELECT m.name, mr.meal_type, mr.date, mr.final_cost
                    FROM meal_records mr
                    JOIN members m ON mr.member_id = m.member_id
                    WHERE 1=1
                """
                count_query = "SELECT COUNT(*) FROM meal_records mr JOIN members m ON mr.member_id = m.member_id WHERE 1=1"
                if member_id != "all":
                    query += " AND mr.member_id = ?"
                    count_query += " AND mr.member_id = ?"
                    params.append(member_id)
                if date_from:
                    query += " AND mr.date >= ?"
                    count_query += " AND mr.date >= ?"
                    params.append(date_from)
                if date_to:
                    query += " AND mr.date <= ?"
                    count_query += " AND mr.date <= ?"
                    params.append(date_to)
                columns = ["name", "meal_type", "date", "final_cost"]
                column_names = {
                    "name": "الاسم", "meal_type": "نوع الوجبة", "date": "التاريخ", "final_cost": "التكلفة",
                }
            elif data_type == "drinks":
                query = """
                    SELECT m.name, dr.drink_name, dr.quantity, dr.total_cost, dr.date
                    FROM drink_records dr
                    JOIN members m ON dr.member_id = m.member_id
                    WHERE 1=1
                """
                count_query = "SELECT COUNT(*) FROM drink_records dr JOIN members m ON dr.member_id = m.member_id WHERE 1=1"
                if member_id != "all":
                    query += " AND dr.member_id = ?"
                    count_query += " AND dr.member_id = ?"
                    params.append(member_id)
                if date_from:
                    query += " AND dr.date >= ?"
                    count_query += " AND dr.date >= ?"
                    params.append(date_from)
                if date_to:
                    query += " AND dr.date <= ?"
                    count_query += " AND dr.date <= ?"
                    params.append(date_to)
                columns = ["name", "drink_name", "quantity", "total_cost", "date"]
                column_names = {
                    "name": "الاسم", "drink_name": "اسم المشروب", "quantity": "الكمية",
                    "total_cost": "التكلفة", "date": "التاريخ",
                }
            elif data_type == "misc":
                query = """
                    SELECT m.name, mc.misc_amount, mc.meal_count, mc.distribution_date
                    FROM miscellaneous_contributions mc
                    JOIN members m ON mc.member_id = m.member_id
                    WHERE 1=1
                """
                count_query = "SELECT COUNT(*) FROM miscellaneous_contributions mc JOIN members m ON mc.member_id = m.member_id WHERE 1=1"
                if member_id != "all":
                    query += " AND mc.member_id = ?"
                    count_query += " AND mc.member_id = ?"
                    params.append(member_id)
                if date_from:
                    query += " AND mc.distribution_date >= ?"
                    count_query += " AND mc.distribution_date >= ?"
                    params.append(date_from)
                if date_to:
                    query += " AND mc.distribution_date <= ?"
                    count_query += " AND mc.distribution_date <= ?"
                    params.append(date_to)
                columns = ["name", "misc_amount", "meal_count", "distribution_date"]
                column_names = {
                    "name": "الاسم", "misc_amount": "قيمة النثرية", "meal_count": "عدد الوجبات",
                    "distribution_date": "تاريخ التوزيع",
                }
            # إضافة Pagination
            self.total_rows = self.db.fetch_one(count_query, params)[0] if count_query else 0
            offset = (self.current_page - 1) * self.rows_per_page
            query += f" LIMIT {self.rows_per_page} OFFSET {offset}"
            rows = self.db.fetch_all(query, params)
            if not rows:
                self.show_snackbar("مفيش بيانات مطابقة للفلاتر دي!")
                self.result_table.columns = [ft.DataColumn(ft.Text("لا توجد بيانات", style=self.text_style))]
                self.result_table.rows = []
                self.result_table.visible = True
                self.pagination_row.controls = []
            else:
                self.result_table.columns = [ft.DataColumn(ft.Text(col_name, style=self.text_style)) for col_name in column_names.values()]
                self.result_table.rows = [
                    ft.DataRow([ft.DataCell(ft.Text(str(cell), style=self.text_style)) for cell in row]) for row in rows
                ]
                self.result_table.visible = True
                self.update_pagination()
            self.page.update()
        except Exception as e:
            logging.error(f"خطأ في جلب البيانات: {e}")
            self.show_snackbar("حدث خطأ في جلب البيانات!")
            self.result_table.columns = [ft.DataColumn(ft.Text("خطأ في التحميل", style=self.text_style))]
            self.result_table.rows = []
            self.result_table.visible = True
            self.page.update()

    def update_pagination(self):
        total_pages = (self.total_rows + self.rows_per_page - 1) // self.rows_per_page
        self.pagination_row.controls = [
            create_button("السابق", lambda e: self.show_report(e, self.current_page - 1) if self.current_page > 1 else None,
                          bgcolor=ft.colors.GREY, disabled=self.current_page <= 1),
            ft.Text(f"صفحة {self.current_page} من {total_pages}", style=self.text_style),
            create_button("التالي", lambda e: self.show_report(e, self.current_page + 1) if self.current_page < total_pages else None,
                          bgcolor=ft.colors.GREY, disabled=self.current_page >= total_pages),
        ]

    def export_to_excel(self, e):
        if not self.result_table.rows:
            self.show_snackbar("مفيش بيانات للتصدير!")
            return
        data_type = self.data_type.value
        df = pd.DataFrame(
            [[cell.content.value for cell in row.cells] for row in self.result_table.rows],
            columns=[col.label.value for col in self.result_table.columns]
        )
        reports_dir = "reports"
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)
        filename = f"{reports_dir}/تقرير_{data_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(filename, index=False, engine="openpyxl")
        self.show_snackbar(f"تم حفظ التقرير في: {filename}")

    def show_snackbar(self, message):
        self.page.snack_bar = ft.SnackBar(ft.Text(message, style=self.text_style))
        self.page.snack_bar.open = True
        self.page.update()

    def navigate_to_parent(self):
        self.page.clean()
        self.page.add(ReportsPage(self.page, self.background_image, self.db, self.navigate).get_content())
        self.page.update()

class ArchivedReportsPage:
    def __init__(self, page, background_image, db, navigate=None):
        self.page = page
        self.background_image = background_image
        self.db = db
        self.navigate = navigate
        self.text_style = ft.TextStyle(size=15, font_family="DancingScript")
        self.title_style = ft.TextStyle(size=28, weight=ft.FontWeight.BOLD, font_family="DancingScript")
        self.archive_dropdown = ft.Dropdown(label="اختر الفترة", width=300, on_change=self.update_members)
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

    def get_content(self):
        self.load_archive_periods()
        title = ft.Text("تقارير الأشهر السابقة", style=self.title_style, color="white", text_align=ft.TextAlign.CENTER)
        dropdown_row = ft.Row([self.archive_dropdown], alignment=ft.MainAxisAlignment.CENTER)
        buttons_row = ft.Row(
            [
                create_button("عرض التقرير", lambda e: self.show_report(e), bgcolor=ft.colors.GREEN),
                create_button("بيانات الأرشيف", lambda e: self.navigate_to("archived_data"), bgcolor=ft.colors.BLUE),
                create_button("رجوع", lambda e: self.navigate_to_parent(), bgcolor=ft.colors.RED),
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
            if not rows:
                self.archive_dropdown.options = [ft.dropdown.Option("مفيش فترات مؤرشفة", disabled=True)]
            else:
                self.archive_dropdown.options = [
                    ft.dropdown.Option(f"{archive_name or f'من {start_date} إلى {end_date}'} (أرشفة: {archived_at})", str(archive_key_id))
                    for archive_key_id, archive_name, start_date, end_date, archived_at in rows
                ]
                self.archive_dropdown.value = self.archive_dropdown.options[0].key
        except Exception as e:
            logging.error(f"خطأ في جلب فترات الأرشيف: {e}")
            self.show_snackbar("حدث خطأ في جلب فترات الأرشيف!")

    def update_members(self, e):
        pass  # سيتم استخدامها في ArchivedDataPage

    def show_report(self, e, page_number=1):
        if not self.archive_dropdown.value:
            self.show_snackbar("اختار فترة أرشيف أولاً!")
            return
        self.current_page = page_number
        archive_key_id = int(self.archive_dropdown.value)
        try:
            query = """
                SELECT m.name, s.total_meals, s.total_drinks, s.total_miscellaneous,
                       s.total_consumption, s.total_contribution, s.remaining_cash
                FROM closure_summary s
                JOIN members_archive m ON s.member_id = m.member_id
                WHERE s.closure_id IN (SELECT closure_id FROM monthly_closures WHERE archive_key_id = ?)
            """
            count_query = """
                SELECT COUNT(*) 
                FROM closure_summary s
                WHERE s.closure_id IN (SELECT closure_id FROM monthly_closures WHERE archive_key_id = ?)
            """
            params = [archive_key_id]
            self.total_rows = self.db.fetch_one(count_query, params)[0]
            offset = (self.current_page - 1) * self.rows_per_page
            query += f" LIMIT {self.rows_per_page} OFFSET {offset}"
            rows = self.db.fetch_all(query, params)
            if not rows:
                self.show_snackbar("مفيش بيانات للفترة دي!")
                self.result_table.columns = [ft.DataColumn(ft.Text("لا توجد بيانات", style=self.text_style))]
                self.result_table.rows = []
                self.result_table.visible = True
            else:
                self.result_table.columns = [
                    ft.DataColumn(ft.Text(col, style=self.text_style)) for col in [
                        "الاسم", "إجمالي الوجبات", "إجمالي المشروبات", "إجمالي النثريات",
                        "إجمالي الاستهلاك", "إجمالي المساهمة", "النقدي المتبقي"
                    ]
                ]
                self.result_table.rows = [
                    ft.DataRow([ft.DataCell(ft.Text(str(cell), style=self.text_style)) for cell in row]) for row in rows
                ]
                self.result_table.visible = True
            self.page.update()
        except Exception as e:
            logging.error(f"خطأ في جلب تقرير الأرشيف: {e}")
            self.show_snackbar("حدث خطأ في جلب التقرير!")
            self.result_table.columns = [ft.DataColumn(ft.Text("خطأ في التحميل", style=self.text_style))]
            self.result_table.rows = []
            self.result_table.visible = True
            self.page.update()

    def export_to_excel(self, e):
        if not self.result_table.rows:
            self.show_snackbar("مفيش بيانات للتصدير!")
            return
        df = pd.DataFrame(
            [[cell.content.value for cell in row.cells] for row in self.result_table.rows],
            columns=[col.label.value for col in self.result_table.columns]
        )
        reports_dir = "reports"
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)
        filename = f"{reports_dir}/تقرير_مؤرشف_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(filename, index=False, engine="openpyxl")
        self.show_snackbar(f"تم حفظ التقرير في: {filename}")

    def show_snackbar(self, message):
        self.page.snack_bar = ft.SnackBar(ft.Text(message, style=self.text_style))
        self.page.snack_bar.open = True
        self.page.update()

    def navigate_to(self, page_name):
        if page_name == "archived_data":
            self.page.clean()
            archived_data_page = ArchivedDataPage(self.page, self.background_image, self.db, self.navigate)
            archived_data_page.set_navigate(self.navigate)
            self.page.add(archived_data_page.get_content())
        self.page.update()

    def navigate_to_parent(self):
        self.page.clean()
        self.page.add(ReportsPage(self.page, self.background_image, self.db, self.navigate).get_content())
        self.page.update()

class ArchivedDataPage:
    def __init__(self, page, background_image, db, navigate=None):
        self.page = page
        self.background_image = background_image
        self.db = db
        self.navigate = navigate
        self.text_style = ft.TextStyle(size=15, font_family="DancingScript")
        self.title_style = ft.TextStyle(size=28, weight=ft.FontWeight.BOLD, font_family="DancingScript")
        self.rows_per_page = 50
        self.current_page = 1
        self.total_rows = 0
        self.archive_dropdown = ft.Dropdown(label="اختر الفترة", width=300, on_change=self.update_members)
        self.data_type = ft.Dropdown(label="نوع البيانات", width=200, options=[
            ft.dropdown.Option("جميع البيانات", "all"),
            ft.dropdown.Option("المصاريف", "expenses"),
            ft.dropdown.Option("الأعضاء", "members"),
            ft.dropdown.Option("الوجبات", "meals"),
            ft.dropdown.Option("المشروبات", "drinks"),
            ft.dropdown.Option("النثريات", "misc"),
        ])
        self.member = ft.Dropdown(label="العضو", width=200)
        self.expense_type = ft.Dropdown(label="نوع المصروف", width=200, options=[
            ft.dropdown.Option("الكل", "all"),
            ft.dropdown.Option("عادي", "normal"),
            ft.dropdown.Option("نثريات", "misc"),
            ft.dropdown.Option("مشروبات", "drink"),
        ])
        self.result_table = ft.DataTable(
            columns=[ft.DataColumn(ft.Text("جاري التحميل...", style=self.text_style))],
            rows=[],
            visible=False
        )
        self.pagination_row = ft.Row([], alignment=ft.MainAxisAlignment.CENTER)

    def set_navigate(self, navigate):
        self.navigate = navigate

    def get_content(self):
        self.load_archive_periods()
        title = ft.Text("بيانات الأرشيف", style=self.title_style, color="white", text_align=ft.TextAlign.CENTER)
        filters_row = ft.Row(
            [
                self.archive_dropdown,
                self.data_type,
                self.member,
                self.expense_type,
                create_button("عرض", lambda e: self.show_data(e), bgcolor=ft.colors.GREEN),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10,
        )
        buttons_row = ft.Row(
            [
                create_button("تصدير إلى Excel", self.export_to_excel, bgcolor=ft.colors.BLUE),
                create_button("رجوع", lambda e: self.navigate_to_parent(), bgcolor=ft.colors.RED),
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
                    filters_row,
                    ft.Container(height=20),
                    table_container,
                    ft.Container(height=10),
                    self.pagination_row,
                    ft.Container(height=20),
                    buttons_row,
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
            if not rows:
                self.archive_dropdown.options = [ft.dropdown.Option("مفيش فترات مؤرشفة", disabled=True)]
            else:
                self.archive_dropdown.options = [
                    ft.dropdown.Option(f"{archive_name or f'من {start_date} إلى {end_date}'} (أرشفة: {archived_at})", str(archive_key_id))
                    for archive_key_id, archive_name, start_date, end_date, archived_at in rows
                ]
                self.archive_dropdown.value = self.archive_dropdown.options[0].key
            self.update_members(None)
        except Exception as e:
            logging.error(f"خطأ في جلب فترات الأرشيف: {e}")
            self.show_snackbar("حدث خطأ في جلب فترات الأرشيف!")

    def update_members(self, e):
        try:
            if not self.archive_dropdown.value:
                self.member.options = [ft.dropdown.Option("مفيش أعضاء", disabled=True)]
                self.member.value = None
                return
            archive_key_id = int(self.archive_dropdown.value)
            query = "SELECT member_id, name FROM members_archive WHERE archive_key_id = ? ORDER BY name"
            members = self.db.fetch_all(query, (archive_key_id,))
            self.member.options = [ft.dropdown.Option(name, str(member_id)) for member_id, name in members]
            self.member.options.insert(0, ft.dropdown.Option("الكل", "all"))
            self.member.value = "all"
            self.page.update()
        except Exception as e:
            logging.error(f"خطأ في جلب الأعضاء المؤرشفين: {e}")
            self.show_snackbar("حدث خطأ في جلب الأعضاء!")

    def validate_date(self, date_str):
        try:
            if date_str:
                datetime.strptime(date_str, "%Y-%m-%d")
                return True
            return True
        except ValueError:
            return False

    def show_data(self, e, page_number=1):
        if not self.archive_dropdown.value:
            self.show_snackbar("اختار فترة أرشيف أولاً!")
            return
        self.current_page = page_number
        archive_key_id = int(self.archive_dropdown.value)
        data_type = self.data_type.value
        member_id = self.member.value
        expense_type = self.expense_type.value
        query = ""
        count_query = ""
        columns = []
        column_names = {}
        params = [archive_key_id]
        try:
            if data_type == "all":
                query = """
                    SELECT m.name, COUNT(mr.meal_record_id) as total_meals, 
                           SUM(dr.quantity) as total_drinks, SUM(mc.misc_amount) as total_misc,
                           SUM(mr.final_cost + dr.total_cost + mc.misc_amount) as total_consumption,
                           m.contribution, (m.contribution - m.total_due) as remaining_cash
                    FROM members_archive m
                    LEFT JOIN meal_records_archive mr ON m.member_id = mr.member_id AND mr.archive_key_id = ?
                    LEFT JOIN drink_records_archive dr ON m.member_id = dr.member_id AND dr.archive_key_id = ?
                    LEFT JOIN miscellaneous_contributions_archive mc ON m.member_id = mc.member_id AND mc.archive_key_id = ?
                    WHERE m.archive_key_id = ?
                """
                count_query = "SELECT COUNT(*) FROM members_archive WHERE archive_key_id = ?"
                if member_id != "all":
                    query += " AND m.member_id = ?"
                    count_query += " AND member_id = ?"
                    params.append(member_id)
                query += " GROUP BY m.member_id, m.name, m.contribution, m.total_due"
                columns = ["name", "total_meals", "total_drinks", "total_misc", "total_consumption", "contribution", "remaining_cash"]
                column_names = {
                    "name": "الاسم", "total_meals": "إجمالي الوجبات", "total_drinks": "إجمالي المشروبات",
                    "total_misc": "إجمالي النثريات", "total_consumption": "إجمالي الاستهلاك",
                    "contribution": "المساهمة", "remaining_cash": "النقدي المتبقي",
                }
                params.extend([archive_key_id, archive_key_id, archive_key_id])
            elif data_type == "expenses":
                query = """
                    SELECT item_name, quantity, price, total_price, consumption, remaining, 
                           CASE WHEN is_miscellaneous = 1 THEN 'نعم' ELSE 'لا' END as is_misc,
                           CASE WHEN is_drink = 1 THEN 'نعم' ELSE 'لا' END as is_drink,
                           date
                    FROM expenses_archive
                    WHERE archive_key_id = ?
                """
                count_query = "SELECT COUNT(*) FROM expenses_archive WHERE archive_key_id = ?"
                if expense_type != "all":
                    if expense_type == "misc":
                        query += " AND is_miscellaneous = 1"
                        count_query += " AND is_miscellaneous = 1"
                    elif expense_type == "drink":
                        query += " AND is_drink = 1"
                        count_query += " AND is_drink = 1"
                    else:
                        query += " AND is_miscellaneous = 0 AND is_drink = 0"
                        count_query += " AND is_miscellaneous = 0 AND is_drink = 0"
                columns = ["item_name", "quantity", "price", "total_price", "consumption", "remaining", "is_misc", "is_drink", "date"]
                column_names = {
                    "item_name": "اسم الصنف", "quantity": "الكمية", "price": "سعر الوحدة",
                    "total_price": "السعر الإجمالي", "consumption": "الاستهلاك", "remaining": "المتبقي",
                    "is_misc": "نثرية", "is_drink": "مشروب", "date": "التاريخ",
                }
            elif data_type == "members":
                query = """
                    SELECT name, rank, contribution, total_due, date,
                           (contribution - total_due) as balance
                    FROM members_archive
                    WHERE archive_key_id = ?
                """
                count_query = "SELECT COUNT(*) FROM members_archive WHERE archive_key_id = ?"
                if member_id != "all":
                    query += " AND member_id = ?"
                    count_query += " AND member_id = ?"
                    params.append(member_id)
                columns = ["name", "rank", "contribution", "total_due", "balance", "date"]
                column_names = {
                    "name": "الاسم", "rank": "الرتبة", "contribution": "المساهمة",
                    "total_due": "المستحق", "balance": "الرصيد", "date": "تاريخ التسجيل",
                }
            elif data_type == "meals":
                query = """
                    SELECT m.name, mr.meal_type, mr.date, mr.final_cost
                    FROM meal_records_archive mr
                    JOIN members_archive m ON mr.member_id = m.member_id
                    WHERE mr.archive_key_id = ?
                """
                count_query = """
                    SELECT COUNT(*) 
                    FROM meal_records_archive mr 
                    JOIN members_archive m ON mr.member_id = m.member_id 
                    WHERE mr.archive_key_id = ?
                """
                if member_id != "all":
                    query += " AND mr.member_id = ?"
                    count_query += " AND mr.member_id = ?"
                    params.append(member_id)
                columns = ["name", "meal_type", "date", "final_cost"]
                column_names = {
                    "name": "الاسم", "meal_type": "نوع الوجبة", "date": "التاريخ", "final_cost": "التكلفة",
                }
            elif data_type == "drinks":
                query = """
                    SELECT m.name, dr.drink_name, dr.quantity, dr.total_cost, dr.date
                    FROM drink_records_archive dr
                    JOIN members_archive m ON dr.member_id = m.member_id
                    WHERE dr.archive_key_id = ?
                """
                count_query = """
                    SELECT COUNT(*) 
                    FROM drink_records_archive dr 
                    JOIN members_archive m ON dr.member_id = m.member_id 
                    WHERE dr.archive_key_id = ?
                """
                if member_id != "all":
                    query += " AND dr.member_id = ?"
                    count_query += " AND dr.member_id = ?"
                    params.append(member_id)
                columns = ["name", "drink_name", "quantity", "total_cost", "date"]
                column_names = {
                    "name": "الاسم", "drink_name": "اسم المشروب", "quantity": "الكمية",
                    "total_cost": "التكلفة", "date": "التاريخ",
                }
            elif data_type == "misc":
                query = """
                    SELECT m.name, mc.misc_amount, mc.meal_count, mc.distribution_date
                    FROM miscellaneous_contributions_archive mc
                    JOIN members_archive m ON mc.member_id = m.member_id
                    WHERE mc.archive_key_id = ?
                """
                count_query = """
                    SELECT COUNT(*) 
                    FROM miscellaneous_contributions_archive mc 
                    JOIN members_archive m ON mc.member_id = m.member_id 
                    WHERE mc.archive_key_id = ?
                """
                if member_id != "all":
                    query += " AND mc.member_id = ?"
                    count_query += " AND mc.member_id = ?"
                    params.append(member_id)
                columns = ["name", "misc_amount", "meal_count", "distribution_date"]
                column_names = {
                    "name": "الاسم", "misc_amount": "قيمة النثرية", "meal_count": "عدد الوجبات",
                    "distribution_date": "تاريخ التوزيع",
                }
            self.total_rows = self.db.fetch_one(count_query, params[:1])[0] if count_query else 0
            offset = (self.current_page - 1) * self.rows_per_page
            query += f" LIMIT {self.rows_per_page} OFFSET {offset}"
            rows = self.db.fetch_all(query, params)
            if not rows:
                self.show_snackbar("مفيش بيانات مطابقة للفلاتر دي!")
                self.result_table.columns = [ft.DataColumn(ft.Text("لا توجد بيانات", style=self.text_style))]
                self.result_table.rows = []
                self.result_table.visible = True
                self.pagination_row.controls = []
            else:
                self.result_table.columns = [ft.DataColumn(ft.Text(col_name, style=self.text_style)) for col_name in column_names.values()]
                self.result_table.rows = [
                    ft.DataRow([ft.DataCell(ft.Text(str(cell), style=self.text_style)) for cell in row]) for row in rows
                ]
                self.result_table.visible = True
                self.update_pagination()
            self.page.update()
        except Exception as e:
            logging.error(f"خطأ في جلب بيانات الأرشيف: {e}")
            self.show_snackbar("حدث خطأ في جلب البيانات!")
            self.result_table.columns = [ft.DataColumn(ft.Text("خطأ في التحميل", style=self.text_style))]
            self.result_table.rows = []
            self.result_table.visible = True
            self.page.update()

    def update_pagination(self):
        total_pages = (self.total_rows + self.rows_per_page - 1) // self.rows_per_page
        self.pagination_row.controls = [
            create_button("السابق", lambda e: self.show_data(e, self.current_page - 1) if self.current_page > 1 else None,
                          bgcolor=ft.colors.GREY, disabled=self.current_page <= 1),
            ft.Text(f"صفحة {self.current_page} من {total_pages}", style=self.text_style),
            create_button("التالي", lambda e: self.show_data(e, self.current_page + 1) if self.current_page < total_pages else None,
                          bgcolor=ft.colors.GREY, disabled=self.current_page >= total_pages),
        ]

    def export_to_excel(self, e):
        if not self.result_table.rows:
            self.show_snackbar("مفيش بيانات للتصدير!")
            return
        df = pd.DataFrame(
            [[cell.content.value for cell in row.cells] for row in self.result_table.rows],
            columns=[col.label.value for col in self.result_table.columns]
        )
        reports_dir = "reports"
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)
        filename = f"{reports_dir}/بيانات_أرشيف_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(filename, index=False, engine="openpyxl")
        self.show_snackbar(f"تم حفظ البيانات في: {filename}")

    def show_snackbar(self, message):
        self.page.snack_bar = ft.SnackBar(ft.Text(message, style=self.text_style))
        self.page.snack_bar.open = True
        self.page.update()

    def navigate_to_parent(self):
        self.page.clean()
        self.page.add(ArchivedReportsPage(self.page, self.background_image, self.db, self.navigate).get_content())
        self.page.update()
