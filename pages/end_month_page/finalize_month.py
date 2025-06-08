import flet as ft
import sqlite3
import pandas as pd
from datetime import datetime
import os
import logging
from utils.button_utils import create_button

# تفعيل تسجيل الأخطاء بمستوى DEBUG
logging.basicConfig(level=logging.DEBUG)

class FinalizeMonth:
    def __init__(self, page, db, navigate=None):
        self.page = page
        self.db = db
        self.navigate = navigate
        self.file_picker = ft.FilePicker()
        self.page.overlay.append(self.file_picker)
        self.text_style = ft.TextStyle(size=15, font_family="DancingScript")
        self.title_style = ft.TextStyle(size=28, weight=ft.FontWeight.BOLD, font_family="DancingScript")
        self.archive_key_id = None  # تخزين مفتاح الأرشيف للاستخدام لاحقاً

    def start_process(self):
        """بدء عملية تقفيل الشهر"""
        self.show_confirmation()

    def show_confirmation(self):
        """عرض نافذة تأكيد قبل بدء العملية"""
        def on_confirm(e):
            self.page.dialog.open = False
            self.page.update()
            self.show_confirmation_distribution()
        dialog = ft.AlertDialog(
            title=ft.Text("تقفيل الشهر"),
            content=ft.Text("هل أنت متأكد من بدء تقفيل الشهر؟"),
            actions=[
                ft.TextButton("نعم", on_click=on_confirm),
                ft.TextButton("لا", on_click=self.close_dialog),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def show_confirmation_distribution(self):
        """عرض نافذة التأكيد قبل التوزيع"""
        def on_confirm(e):
            self.page.dialog.open = False
            self.page.update()
            self._confirm_distribution()
        confirm_dialog = ft.AlertDialog(
            title=ft.Text("توزيع النثريات"),
            content=ft.Text("سيتم توزيع النثريات، هل تريد الاستمرار؟"),
            actions=[
                ft.TextButton("نعم", on_click=on_confirm),
                ft.TextButton("لا", on_click=self.close_dialog),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog = confirm_dialog
        confirm_dialog.open = True
        self.page.update()

    def _confirm_distribution(self):
        """تنفيذ التوزيع مع التعامل مع الأخطاء"""
        try:
            success, self.archive_key_id = self._distribute_and_archive_miscellaneous()
            if success and self.archive_key_id:
                self.show_snackbar("تم توزيع النثريات والأرشفة بنجاح!")
                self._run_finalize_process()
            else:
                self.show_snackbar("فشل توزيع النثريات أو تعذر الحصول على مفتاح الأرشيف.")
        except Exception as e:
            logging.error(f"Error in distribution: {e}", exc_info=True)
            self.show_snackbar(f"خطأ أثناء التوزيع: {str(e)}")

    def _distribute_and_archive_miscellaneous(self):
        """الوظيفة الأساسية لتوزيع النثريات وأرشفتها"""
        try:
            with self.db.conn:
                cursor = self.db.conn.cursor()
                # 1. جلب النثريات (miscellaneous) من expenses
                cursor.execute(
                    "SELECT expense_id, total_price FROM expenses WHERE is_miscellaneous = 1"
                )
                misc_expenses = cursor.fetchall()
                # إذا لم توجد نثريات، نكمل العملية بدون توزيع نثريات
                if not misc_expenses:
                    self.show_snackbar("لا توجد أصناف نثريات للتوزيع!")
                    # ننشئ مفتاح أرشيف للفترة الحالية
                    distribution_date = datetime.now().strftime("%Y-%m-%d")
                    first_date = self.get_first_transaction_date() or distribution_date
                    archive_key_id = self._create_archive_key(cursor, first_date)
                    return True, archive_key_id

                total_misc_value = sum(item[1] for item in misc_expenses)

                # 2. جلب عدد الوجبات لكل مشترك دفعة واحدة
                cursor.execute(
                    "SELECT member_id, COUNT(*) as meal_count FROM meal_records GROUP BY member_id"
                )
                meal_counts = cursor.fetchall()
                if not meal_counts:
                    self.show_snackbar("لا توجد سجلات وجبات لتوزيع النثريات!")
                    return False, None

                total_meals = sum(count for _, count in meal_counts)

                # 3. حساب تكلفة النثريات لكل وجبة
                misc_cost_per_meal = total_misc_value / total_meals

                # 4. تحديث كل مشترك وتسجيل التوزيع في جدول contributions
                distribution_date = datetime.now().strftime("%Y-%m-%d")
                for member_id, meal_count in meal_counts:
                    amount = meal_count * misc_cost_per_meal
                    # تحديث الدين في جدول members
                    cursor.execute(
                        "UPDATE members SET total_due = total_due + ? WHERE member_id = ?",
                        (amount, member_id)
                    )
                    # تسجيل التوزيع
                    cursor.execute(
                        "INSERT INTO miscellaneous_contributions (member_id, misc_amount, meal_count, distribution_date) VALUES (?, ?, ?, ?)",
                        (member_id, amount, meal_count, distribution_date)
                    )

                # 5. الحصول على مفتاح الأرشفة (بدون تحديث end_date هنا)
                first_date = self.get_first_transaction_date() or distribution_date
                archive_key_id = self._create_archive_key(cursor, first_date)
                if not archive_key_id:
                    raise Exception("Failed to create archive key.")


                # 7. أرشفة وحذف النثريات الأصلية من expenses (إذا وجدت)
                misc_ids = [item[0] for item in misc_expenses]
                ph2 = ",".join("?" * len(misc_ids))
                cursor.execute(
                    f"INSERT OR REPLACE INTO expenses_archive "
                    "(expense_id, item_name, quantity, price, total_price, consumption, remaining, is_miscellaneous, is_drink, date, archive_key_id) "
                    f"SELECT expense_id, item_name, quantity, price, total_price, consumption, remaining, is_miscellaneous, is_drink, date, ? "
                    f"FROM expenses WHERE expense_id IN ({ph2})",
                    (archive_key_id, *misc_ids)
                )
                cursor.execute(
                    f"DELETE FROM expenses WHERE expense_id IN ({ph2})",
                    misc_ids
                )

                logging.info(f"Distributed and archived {len(misc_ids)} items. Total value: {total_misc_value}")
                return True, archive_key_id

        except Exception as e:
            self.db.conn.rollback()
            logging.error(f"Error distributing miscellaneous: {e}", exc_info=True)
            self.show_snackbar(f"خطأ أثناء توزيع النثريات: {e}")
            return False, None

    def _create_archive_key(self, cursor, first_date):
        """إنشاء مفتاح أرشفة جديد بدون تحديث المفاتيح الموجودة"""
        now_date = datetime.now().strftime("%Y-%m-%d")
        now_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        archive_name = f"Dist_{first_date}_to_{now_date}"
        cursor.execute(
            "INSERT INTO archive_keys (archive_name, start_date, end_date, archived_at) VALUES (?, ?, ?, ?)",
            (archive_name, first_date, now_date, now_dt)
        )
        return cursor.lastrowid

    def get_first_transaction_date(self):
        """أقل تاريخ سجل موجود في الجداول الثلاث"""
        queries = [
            "SELECT MIN(date) FROM meal_records",
            "SELECT MIN(date) FROM drink_records",
            "SELECT MIN(date) FROM expenses"
        ]
        dates = []
        for q in queries:
            cur = self.db.conn.execute(q)
            d = cur.fetchone()[0]
            if d:
                dates.append(d)
        return min(dates) if dates else None
    def _run_finalize_process(self):
        """التنفيذ الرئيسي لتقفيل الشهر"""
        try:
            # 0. أرشفة بيانات الأعضاء أولاً
            with self.db.conn:
                cursor = self.db.conn.cursor()
                if not self._archive_members_data(cursor, self.archive_key_id):
                    raise Exception("Failed to archive members data")
                
                # 1. حساب الإجماليات قبل الأرشفة
                member_data = self._get_member_data()
                meal_data = self._get_meal_totals()
                drink_data = self._get_drink_totals()
                misc_data = self._get_misc_totals()
                total_contributions = self._get_total_contributions(member_data)

                # 2. حفظ تقفيل الشهر
                closure_id = self._save_monthly_closure(cursor, self.archive_key_id)
                
                # 3. حفظ ملخص كل مشترك
                self._save_closure_summaries(cursor, closure_id, member_data, meal_data, drink_data, misc_data, total_contributions)

            # 4. عرض التقرير
            self._show_report(closure_id)

        except Exception as e:
            logging.error(f"خطأ أثناء تقفيل الشهر: {e}", exc_info=True)
            self.show_snackbar(f"حدث خطأ أثناء تقفيل الشهر: {str(e)}")


    def _archive_all_data(self):
        """أرشفة جميع البيانات وتحديث الجداول لبداية شهر جديد"""
        try:
            with self.db.conn:
                cursor = self.db.conn.cursor()
                closure_date = datetime.now().strftime("%Y-%m-%d")

                # التأكد من أن archive_key_id ليس None
                if not self.archive_key_id:
                    raise ValueError("archive_key_id is None or invalid.")

                # التأكد من وجود archive_key_id في archive_keys
                cursor.execute(
                    "SELECT start_date, end_date FROM archive_keys WHERE archive_key_id = ?",
                    (self.archive_key_id,)
                )
                result = cursor.fetchone()
                if not result:
                    raise ValueError(f"Invalid archive_key_id: {self.archive_key_id}")
                start_date, end_date = result

                # 1. أرشفة الوجبات
                cursor.execute(f"""
                    INSERT INTO meal_records_archive
                    SELECT *, ? FROM meal_records
                    WHERE date BETWEEN ? AND ?
                """, (self.archive_key_id, start_date, end_date))

                # 2. أرشفة المشروبات
                cursor.execute(f"""
                    INSERT INTO drink_records_archive
                    SELECT *, ? FROM drink_records
                    WHERE date BETWEEN ? AND ?
                """, (self.archive_key_id, start_date, end_date))

                # 3. أرشفة توزيعات النثريات
                cursor.execute(f"""
                    INSERT INTO miscellaneous_contributions_archive
                    SELECT *, ? FROM miscellaneous_contributions
                    WHERE distribution_date BETWEEN ? AND ?
                """, (self.archive_key_id, start_date, end_date))

                # 4. أرشفة المشتروات المستهلكة فقط
                cursor.execute(f"""
                    INSERT INTO expenses_archive
                    SELECT expense_id, item_name, consumption, price, 
                           (consumption * price) as total_price,
                           0 as consumption, remaining, is_miscellaneous, is_drink, ?, ?
                    FROM expenses
                    WHERE consumption > 0 AND date BETWEEN ? AND ?
                """, (closure_date, self.archive_key_id, start_date, end_date))

                # 5. تحديث جدول المشتروات لبداية شهر جديد
                cursor.execute(f"""
                    UPDATE expenses
                    SET 
                        quantity = remaining,
                        consumption = 0,
                        total_price = remaining * price,
                        date = ?
                    WHERE date BETWEEN ? AND ?
                """, (closure_date, start_date, end_date))

                # 6. تصفير ديون المشتركين
                cursor.execute("UPDATE members SET total_due = 0")

                # 7. حذف السجلات المؤرشفة

                cursor.execute("DELETE FROM miscellaneous_expenses WHERE date BETWEEN ? AND ?", (start_date, end_date))
                cursor.execute("DELETE FROM meal_records WHERE date BETWEEN ? AND ?", (start_date, end_date))
                cursor.execute("DELETE FROM drink_records WHERE date BETWEEN ? AND ?", (start_date, end_date))
                cursor.execute("DELETE FROM miscellaneous_contributions WHERE distribution_date BETWEEN ? AND ?", (start_date, end_date))


                # 8. تحديث نهاية الفترة في archive_keys
                cursor.execute(
                    "UPDATE archive_keys SET end_date = ? WHERE archive_key_id = ?",
                    (end_date, self.archive_key_id)
                )
                # أرشفة ملخص الإغلاق
                cursor.execute(f"""
                    INSERT INTO closure_summary_archive
                    SELECT s.*, ? 
                    FROM closure_summary s
                    WHERE s.closure_id IN (
                        SELECT closure_id FROM monthly_closures 
                        WHERE archive_key_id = ?
                    )
                """, (self.archive_key_id, self.archive_key_id))

                # حذف البيانات المؤرشفة من الجدول الرئيسي
                cursor.execute("""
                    DELETE FROM closure_summary 
                    WHERE closure_id IN (
                        SELECT closure_id FROM monthly_closures 
                        WHERE archive_key_id = ?
                    )
                """, (self.archive_key_id,))                
                return True

        except Exception as e:
            logging.error(f"Error archiving data: {e}", exc_info=True)
            return False

    def _get_member_data(self):
        """استرجاع بيانات المشتركين"""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT member_id, name, rank, contribution, total_due FROM members")
        return {row[0]: (row[1], row[2], row[3], row[4]) for row in cursor.fetchall()}

    def _get_meal_totals(self):
        """استرجاع إجمالي الوجبات لكل مشترك"""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT member_id, COUNT(*) as count, SUM(final_cost) as total
            FROM meal_records GROUP BY member_id
        """)
        return {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

    def _get_drink_totals(self):
        """استرجاع إجمالي المشروبات لكل مشترك"""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT member_id, SUM(quantity) as count, SUM(total_cost) as total
            FROM drink_records GROUP BY member_id
        """)
        return {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

    def _get_misc_totals(self):
        """استرجاع إجمالي النثريات لكل مشترك"""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT member_id, SUM(misc_amount) as total
            FROM miscellaneous_contributions GROUP BY member_id
        """)
        return {row[0]: row[1] for row in cursor.fetchall()}

    def _get_total_contributions(self, member_data):
        """حساب إجمالي المساهمات من جدول الأعضاء"""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT SUM(total_due) FROM members")
        result = cursor.fetchone()[0]
        return result or 0

    def _save_monthly_closure(self, cursor, archive_key_id):
        """حفظ تقفيل الشهر في قاعدة البيانات"""
        closure_date = datetime.now().strftime("%Y-%m-%d")
        cursor.execute(
            "INSERT INTO monthly_closures (closure_date, archive_key_id) VALUES (?, ?)",
            (closure_date, archive_key_id)
        )
        return cursor.lastrowid
    def _archive_members_data(self, cursor, archive_key_id):
        """أرشفة بيانات الأعضاء قبل إنشاء الملخص"""
        try:
            # أرشفة بيانات الأعضاء الحاليين
            cursor.execute("""
                INSERT INTO members_archive
                SELECT member_id, name, rank, contribution, total_due, date, ?
                FROM members
            """, (archive_key_id,))
            
            return True
        except Exception as e:
            logging.error(f"خطأ في أرشفة بيانات الأعضاء: {e}")
            return False

    def _save_closure_summaries(self, cursor, closure_id, member_data, meal_data, drink_data, misc_data, total_contributions):
        """حفظ ملخص كل مشترك في قاعدة البيانات"""
        for member_id, (name, rank, contribution, total_due) in member_data.items():
            meals = meal_data.get(member_id, (0, 0))
            drinks = drink_data.get(member_id, (0, 0))
            misc = misc_data.get(member_id, 0)
            total_consumption = meals[1] + drinks[1] + misc
            remaining = contribution - total_consumption - misc
            
            # التأكد من وجود العضو في الأرشيف أولاً
            cursor.execute("""
                SELECT 1 FROM members_archive 
                WHERE member_id = ? AND archive_key_id = ?
            """, (member_id, self.archive_key_id))
            
            if not cursor.fetchone():
                continue  # تخطي إذا لم يتم أرشفة العضو
                
            cursor.execute("""
                INSERT INTO closure_summary 
                (closure_id, member_id, total_meals, total_drinks, total_miscellaneous, 
                total_consumption, total_contribution, remaining_cash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                closure_id, member_id, meals[1], drinks[1], misc,
                total_consumption, contribution, remaining
            ))        


    def _get_remaining_items_total(self):
        """حساب إجمالي قيمة الأصناف المتبقية في المشتروات"""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT SUM(remaining * price) 
            FROM expenses
            WHERE remaining > 0
        """)
        total = cursor.fetchone()[0]
        return total if total else 0.0
    def _show_report(self, closure_id):
        """عرض التقرير على شكل جدول في صفحة Flet مع التعديلات الجديدة"""
        cursor = self.db.conn.cursor()
        
        # جلب بيانات الفترة
        cursor.execute("""
            SELECT mc.closure_date, ak.start_date, ak.end_date 
            FROM monthly_closures mc
            JOIN archive_keys ak ON mc.archive_key_id = ak.archive_key_id
            WHERE mc.closure_id = ?
        """, (closure_id,))
        closure_date, start_date, end_date = cursor.fetchone()
        
        # جلب بيانات الملخص
        cursor.execute("""
            SELECT m.name, s.total_meals, s.total_drinks, s.total_miscellaneous, 
                   s.total_consumption, s.total_contribution, s.remaining_cash
            FROM closure_summary s
            JOIN members m ON s.member_id = m.member_id
            WHERE s.closure_id = ?
        """, (closure_id,))
        summary_data = cursor.fetchall()

        # حساب الإجماليات
        total_meals = sum(row[1] for row in summary_data)
        total_drinks = sum(row[2] for row in summary_data)
        total_misc = sum(row[3] for row in summary_data)
        total_consumption = sum(row[4] for row in summary_data)
        total_contributions = sum(row[5] for row in summary_data)
        total_remaining_items = self._get_remaining_items_total()
        total_remaining_cash = total_contributions - (total_consumption + total_remaining_items)
        # حفظ الإجماليات في جدول monthly_totals_archive
        try:
            cursor.execute("""
                INSERT INTO monthly_totals_archive (
                    archive_key_id, total_meals, total_drinks, total_misc, 
                    total_consumption, total_contributions, remaining_items, remaining_cash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.archive_key_id, total_meals, total_drinks, total_misc,
                total_consumption, total_contributions, total_remaining_items, total_remaining_cash
            ))
            self.db.conn.commit()
            logging.info("تم حفظ إجماليات الشهر في جدول monthly_totals_archive بنجاح.")
        except Exception as e:
            logging.error(f"خطأ أثناء حفظ الإجماليات في قاعدة البيانات: {e}")

        # إعداد أنماط التنسيق
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

        # طريقة بديلة لتوسيط النص في الخلايا
        def centered_text(text, style=None):
            return ft.Container(
                content=ft.Text(text, style=style),
                alignment=ft.alignment.center,
                padding=10,
                expand=True
            )

        # جدول الملخص
        summary_table = ft.DataTable(
            columns=[
                ft.DataColumn(centered_text("الاسم", header_style)),
                ft.DataColumn(centered_text("الوجبات", header_style)),
                ft.DataColumn(centered_text("المشروبات", header_style)),
                ft.DataColumn(centered_text("النثريات", header_style)),
                ft.DataColumn(centered_text("الاستهلاك", header_style)),
                ft.DataColumn(centered_text("المساهمة", header_style)),
            ],
            rows=[
                ft.DataRow(
                    cells=[
                        ft.DataCell(centered_text(row[0], cell_style)),
                        ft.DataCell(centered_text(str(row[1]), cell_style)),
                        ft.DataCell(centered_text(str(row[2]), cell_style)),
                        ft.DataCell(centered_text(f"{row[3]:.2f}", cell_style)),
                        ft.DataCell(centered_text(f"{row[4]:.2f}", cell_style)),
                        ft.DataCell(centered_text(f"{row[5]:.2f}", cell_style)),
                    ]
                ) for row in summary_data
            ],
            column_spacing=5,
            heading_row_height=50,
            data_row_min_height=40,
            horizontal_margin=10,
            heading_row_color=ft.colors.BLUE,
            width=min(1000, self.page.width * 0.9),
            border=ft.border.all(1, ft.colors.GREY_400),
            border_radius=10,
        )

        # جدول الإجماليات
        totals_table = ft.DataTable(
            columns=[
                ft.DataColumn(centered_text("الوجبات", header_style)),
                ft.DataColumn(centered_text("المشروبات", header_style)),
                ft.DataColumn(centered_text("النثريات", header_style)),
                ft.DataColumn(centered_text("الاستهلاك", header_style)),
                ft.DataColumn(centered_text("المتبقيات", header_style)),
                ft.DataColumn(centered_text("المساهمة", header_style)),
                ft.DataColumn(centered_text("المتبقي", header_style)),
            ],
            rows=[
                ft.DataRow(
                    cells=[
                        ft.DataCell(centered_text(str(total_meals), cell_style)),
                        ft.DataCell(centered_text(str(total_drinks), cell_style)),
                        ft.DataCell(centered_text(f"{total_misc:.2f}", cell_style)),
                        ft.DataCell(centered_text(f"{total_consumption:.2f}", cell_style)),
                        ft.DataCell(centered_text(f"{total_remaining_items:.2f}", cell_style)),
                        ft.DataCell(centered_text(f"{total_contributions:.2f}", cell_style)),
                        ft.DataCell(centered_text(f"{total_remaining_cash:.2f}", cell_style)),
                    ]
                )
            ],
            column_spacing=10,
            heading_row_height=55,
            data_row_min_height=45,
            horizontal_margin=15,
            heading_row_color=ft.colors.BLUE,
            width=min(1000, self.page.width * 0.9),
            border=ft.border.all(1, ft.colors.GREY_400),
            border_radius=10,
        )

        # أزرار التحكم
        export_button = create_button(
            "تصدير إلى Excel", 
            lambda e: self._export_to_excel(closure_id),
            bgcolor=ft.colors.GREEN,
            width=200
        )
        
        close_button = create_button(
            "إغلاق", 
            lambda e: self._close_report(),
            bgcolor=ft.colors.RED,
            width=200
        )

        # إنشاء واجهة التقرير النهائية
        report_view = ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Column([
                            ft.Text("ملخص الاستهلاك الشهري", 
                                   style=ft.TextStyle(size=24, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE)),
                            ft.Text(f"فترة التقرير: من {start_date} إلى {end_date}", 
                                   style=ft.TextStyle(size=16)),
                            ft.Text(f"تاريخ التقفيل: {closure_date}", 
                                   style=ft.TextStyle(size=16)),
                        ], spacing=10),
                        padding=20,
                        alignment=ft.alignment.center
                    ),
                    
                    ft.Divider(height=20, color=ft.colors.GREY),
                    
                    ft.Container(
                        content=summary_table,
                        padding=10,
                        margin=ft.margin.symmetric(horizontal=20),
                        alignment=ft.alignment.center,
                        bgcolor=ft.colors.WHITE,
                        border_radius=10,
                        width=min(1100, self.page.width * 0.95),
                    ),
                    
                    ft.Divider(height=30, color=ft.colors.GREY),
                    
                    ft.Container(
                        content=ft.Column([
                            ft.Text("إجماليات الشهر", 
                                   style=ft.TextStyle(size=20, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE)),
                            totals_table
                        ]),
                        padding=10,
                        alignment=ft.alignment.center
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
        # زر تصدير إلى Excel
        def export_to_excel(e):
            self._export_to_excel(closure_id)
        export_button = create_button("تصدير إلى Excel", export_to_excel, bgcolor=ft.colors.BLUE)
        # زر إغلاق
        def on_close(e):
            # تنفيذ الأرشفة النهائية عند الضغط على إغلاق
            if self._archive_all_data():
                self.show_snackbar("تم أرشفة جميع البيانات بنجاح")
            else:
                self.show_snackbar("حدث خطأ أثناء أرشفة البيانات")
            self.close_dialog_1(e)
        close_button = create_button("إغلاق", on_close, bgcolor=ft.colors.RED)
        # إنشاء صفحة التقرير مع سكرول
        report_view = ft.Container(
            content=ft.Column([
                ft.Text("ملخص الاستهلاك", style=self.title_style),
                ft.Text(f"فترة التقرير: من {start_date} إلى {end_date}", style=self.text_style),
                ft.Text(f"تاريخ التقفيل: {closure_date}", style=self.text_style),
                ft.Container(height=20),
                ft.Container(
                    content=summary_table,
                    padding=10,
                    margin=10,
                    bgcolor=ft.colors.SURFACE_VARIANT,
                    border_radius=10
                ),
                ft.Divider(height=30),
                ft.Text("إجماليات الشهر", style=self.title_style),
                ft.Container(height=20),
                ft.Container(
                    content=totals_table,
                    padding=10,
                    margin=10,
                    bgcolor=ft.colors.SURFACE_VARIANT,
                    border_radius=10
                ),
                ft.Container(height=30),
                ft.Row(
                    [export_button, close_button],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=50
                ),
                ft.Container(height=50)
            ]),
            padding=20,
            expand=True
        )
        scrollable_report = ft.ListView(
            controls=[report_view],
            padding=10,
            expand=True
        )
        self.page.clean()
        self.page.add(scrollable_report)
        self.page.update()

    def _export_to_excel(self, closure_id):
        """تصدير التقرير إلى ملف Excel"""
        cursor = self.db.conn.cursor()
        # جلب بيانات الفترة
        cursor.execute("""
            SELECT mc.closure_date, ak.start_date, ak.end_date 
            FROM monthly_closures mc
            JOIN archive_keys ak ON mc.archive_key_id = ak.archive_key_id
            WHERE mc.closure_id = ?
        """, (closure_id,))
        closure_date, start_date, end_date = cursor.fetchone()

        # جلب بيانات الملخص
        cursor.execute("""
            SELECT m.name, s.total_meals, s.total_drinks, s.total_miscellaneous, 
                   s.total_consumption, s.total_contribution
            FROM closure_summary s
            JOIN members m ON s.member_id = m.member_id
            WHERE s.closure_id = ?
        """, (closure_id,))
        summary_data = cursor.fetchall()

        # حساب إجمالي المتبقيات
        total_remaining_items = self._get_remaining_items_total()
        total_contributions = sum(row[5] for row in summary_data)
        total_consumption = sum(row[4] for row in summary_data)
        total_remaining_cash = total_contributions - (total_consumption + total_remaining_items)

        # إنشاء DataFrames
        summary_df = pd.DataFrame(summary_data, columns=[
            "الاسم", "عدد الوجبات", "عدد المشروبات", "إجمالي النثريات",
            "إجمالي الاستهلاك", "إجمالي المساهمة"
        ])

        totals_df = pd.DataFrame({
            "إجمالي الوجبات": [sum(row[1] for row in summary_data)],
            "إجمالي المشروبات": [sum(row[2] for row in summary_data)],
            "إجمالي النثريات": [sum(row[3] for row in summary_data)],
            "إجمالي الاستهلاك": [total_consumption],
            "إجمالي المتبقيات": [total_remaining_items],
            "إجمالي المساهمة": [total_contributions],
            "النقدي المتبقي": [total_remaining_cash]
        })
        
        info_df = pd.DataFrame({
            "معلومة": ["تاريخ التقفيل", "فترة التقرير", "عدد الأفراد"],
            "القيمة": [closure_date, f"من {start_date} إلى {end_date}", len(summary_df)]
        })
        
        # إنشاء مجلد التقارير إذا لم يكن موجودًا
        reports_dir = "reports"
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)
        
        # حفظ البيانات في ملف Excel
        filename = f"{reports_dir}/تقرير_تقفيل_الشهر_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            info_df.to_excel(writer, sheet_name="معلومات", index=False)
            summary_df.to_excel(writer, sheet_name="ملخص الأفراد", index=False)
            totals_df.to_excel(writer, sheet_name="الإجماليات", index=False)
            
            # الحصول على كائن الـ workbook لاستخدامه في التنسيق
            workbook = writer.book
            
            # تطبيق التنسيق على جميع الأوراق
            for sheetname in writer.sheets:
                worksheet = writer.sheets[sheetname]
                
                # إنشاء نمط للتوسيط وإضافة الحدود
                from openpyxl.styles import Alignment, Border, Side, Font
                center_alignment = Alignment(horizontal='center', vertical='center')
                thin_border = Border(left=Side(style='thin'), 
                                    right=Side(style='thin'), 
                                    top=Side(style='thin'), 
                                    bottom=Side(style='thin'))
                font_style = Font(name='Arial', size=12)
                
                # تطبيق التنسيق على جميع الخلايا
                for row in worksheet.iter_rows():
                    for cell in row:
                        cell.alignment = center_alignment
                        cell.border = thin_border
                        cell.font = font_style
                
                # AutoFit لجميع الأعمدة
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = (max_length + 2) * 1.2
                    worksheet.column_dimensions[column_letter].width = adjusted_width
        
        self.show_snackbar(f"تم حفظ التقرير في: {filename}")
    
    def show_snackbar(self, message):
        """عرض رسالة للمستخدم"""
        self.page.snack_bar = ft.SnackBar(ft.Text(message, style=self.text_style))
        self.page.snack_bar.open = True
        self.page.update()

    def close_dialog(self, e=None):
        """إغلاق نافذة الحوار والعودة إلى صفحة نهاية الشهر"""
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()
    def close_dialog_1(self, e=None):
        # فقط أعد تحميل الصفحة السابقة (إذا كنت تستخدم نظام التنقل)
        if self.navigate:
            self.navigate("end_month_page")  # غير هذا بمسار الصفحة السابقة
        else:
            # أو أنشئ واجهة بسيطة للعودة
            self.page.clean()
            self.page.add(ft.Text("تم الإغلاق بنجاح", style=self.title_style))
            self.page.update()
