import flet as ft
from utils.button_utils import create_button
from pages.reports_page.archived_reports.archived_expenses_report import show_expenses_report
from pages.reports_page.archived_reports.archived_remaining_report import show_remaining_report
from pages.reports_page.archived_reports.archived_meals_report import show_meals_report
from pages.reports_page.archived_reports.archived_drinks_report import show_drinks_report
from pages.reports_page.archived_reports.archived_consumption_report import show_consumption_report
from pages.reports_page.archived_reports.archived_member_consumption import show_member_consumption

class ArchivedDataPage:
    def __init__(self, page, background_image, db, navigate=None, archive_key_id=None):
        self.page = page
        self.background_image = background_image
        self.db = db
        self.navigate = navigate
        self.archive_key_id = archive_key_id
        self.text_style = ft.TextStyle(size=15, font_family="DancingScript")
        self.title_style = ft.TextStyle(size=28, weight=ft.FontWeight.BOLD, font_family="DancingScript")
        self._init_ui_components()

    def _init_ui_components(self):
        pass

    def set_navigate(self, navigate):
        self.navigate = navigate

    def get_content(self):
        if not self.archive_key_id:
            self.show_snackbar("يرجى اختيار فترة أرشيف أولاً!")
            return ft.Container()

        # جلب معلومات الأرشيف لعرض العنوان
        archive_info = self.db.fetch_all(
            "SELECT archive_name, start_date, end_date FROM archive_keys WHERE archive_key_id = ?",
            [self.archive_key_id]
        )
        if not archive_info:
            self.show_snackbar("لا توجد بيانات لفترة الأرشيف المحددة!")
            return ft.Container()
        
        archive_name, start_date, end_date = archive_info[0]
        title_text = f"تقارير الأرشيف: {archive_name} ({start_date} إلى {end_date})"

        title = ft.Text(
            title_text, 
            style=self.title_style, 
            color="white", 
            text_align=ft.TextAlign.CENTER
        )
        
        expenses_report_btn = create_button(
            text="تقرير المصروفات",
            on_click=lambda e: show_expenses_report(self, self.archive_key_id),
            bgcolor=ft.colors.BLUE_700,
            width=200
        )
        
        remaining_report_btn = create_button(
            text="تقرير المتبقيات",
            on_click=lambda e: show_remaining_report(self, self.archive_key_id),
            bgcolor=ft.colors.GREEN_700,
            width=200
        )
        
        meals_report_btn = create_button(
            text="تقرير الوجبات",
            on_click=lambda e: show_meals_report(self, self.archive_key_id),
            bgcolor=ft.colors.INDIGO_700,
            width=200
        )
        
        drinks_report_btn = create_button(
            text="تقرير المشروبات",
            on_click=lambda e: show_drinks_report(self, self.archive_key_id),
            bgcolor=ft.colors.TEAL_700,
            width=200
        )
        
        consumption_report_btn = create_button(
            text="تقرير استهلاك المشتركين",
            on_click=lambda e: show_consumption_report(self, self.archive_key_id),
            bgcolor=ft.colors.ORANGE_700,
            width=200
        )
        
        member_consumption_btn = create_button(
            text="تقرير استهلاك مشترك",
            on_click=lambda e: show_member_consumption(self, self.archive_key_id),
            bgcolor=ft.colors.PURPLE_700,
            width=200
        )
        
        back_button = create_button(
            text="رجوع",
            on_click=lambda e: self.navigate_to_parent(),
            bgcolor=ft.colors.RED_700,
            width=200
        )

        row1 = ft.Row(
            [expenses_report_btn, remaining_report_btn],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10
        )
        
        row2 = ft.Row(
            [meals_report_btn, drinks_report_btn],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10
        )
        
        row3 = ft.Row(
            [consumption_report_btn, member_consumption_btn],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10
        )
        
        row4 = ft.Row(
            [back_button],
            alignment=ft.MainAxisAlignment.CENTER
        )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(height=20),
                    title,
                    ft.Container(height=30),
                    row1,
                    ft.Container(height=20),
                    row2,
                    ft.Container(height=20),
                    row3,
                    ft.Container(height=20),
                    row4,
                ],
                alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            image_src=self.background_image.src,
            image_fit=ft.ImageFit.COVER,
            expand=True
        )

    def navigate_to_parent(self):
        self.page.clean()
        from pages.reports_page.archived_reports.archived_reports import ArchivedReportsPage
        self.page.add(ArchivedReportsPage(self.page, self.background_image, self.db, self.navigate).get_content())
        self.page.update()

    def navigate_to_reports_current(self):
        self.page.clean()
        self.page.add(self.get_content())
        self.page.update()

    def show_snackbar(self, message):
        self.page.snack_bar = ft.SnackBar(ft.Text(message, style=self.text_style))
        self.page.snack_bar.open = True
        self.page.update()
