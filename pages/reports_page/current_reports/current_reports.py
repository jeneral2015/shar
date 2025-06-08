import flet as ft
from utils.button_utils import create_button
from pages.reports_page.current_reports.expenses_report import show_expenses_report
from pages.reports_page.current_reports.remaining_report import show_remaining_report
from pages.reports_page.current_reports.meals_report import show_meals_report
from pages.reports_page.current_reports.drinks_report import show_drinks_report
from pages.reports_page.current_reports.consumption_report import show_consumption_report
from pages.reports_page.current_reports.member_consumption import show_member_consumption

class CurrentReportsPage:
    def __init__(self, page, background_image, db, navigate=None):
        self.page = page
        self.background_image = background_image
        self.db = db
        self.navigate = navigate
        self.text_style = ft.TextStyle(size=15, font_family="DancingScript")
        self.title_style = ft.TextStyle(size=28, weight=ft.FontWeight.BOLD, font_family="DancingScript")
        self._init_ui_components()

    def _init_ui_components(self):
        # يمكن إضافة عناصر واجهة مستخدم إضافية هنا إذا لزم الأمر
        pass

    def set_navigate(self, navigate):
        self.navigate = navigate

    def get_content(self):
        title = ft.Text(
            "تقارير الشهر الحالي", 
            style=self.title_style, 
            color="white", 
            text_align=ft.TextAlign.CENTER
        )
        
        # إنشاء الأزرار المطلوبة
        expenses_report_btn = create_button(
            text="تقرير المصروفات",
            on_click=lambda e: show_expenses_report(self),
            bgcolor=ft.colors.BLUE_700,
            width=200
        )
        
        remaining_report_btn = create_button(
            text="تقرير المتبقيات",
            on_click=lambda e: show_remaining_report(self),
            bgcolor=ft.colors.GREEN_700,
            width=200
        )
        
        meals_report_btn = create_button(
            text="تقرير الوجبات",
            on_click=lambda e: show_meals_report(self),
            bgcolor=ft.colors.INDIGO_700,
            width=200
        )
        
        drinks_report_btn = create_button(
            text="تقرير المشروبات",
            on_click=lambda e: show_drinks_report(self),
            bgcolor=ft.colors.TEAL_700,
            width=200
        )
        
        consumption_report_btn = create_button(
            text="تقرير استهلاك المشتركين",
            on_click=lambda e: show_consumption_report(self),
            bgcolor=ft.colors.ORANGE_700,
            width=200
        )
        
        member_consumption_btn = create_button(
            text="تقرير استهلاك مشترك محدد",
            on_click=lambda e: show_member_consumption(self),
            bgcolor=ft.colors.PURPLE_700,
            width=200
        )
        
        back_button = create_button(
            text="رجوع",
            on_click=lambda e: self.navigate_to_parent(),
            bgcolor=ft.colors.RED_700,
            width=200
        )

        # تنظيم الأزرار في صفوف
        row1 = ft.Row(
            [expenses_report_btn, remaining_report_btn],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20
        )
        
        row2 = ft.Row(
            [meals_report_btn, drinks_report_btn],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20
        )
        
        row3 = ft.Row(
            [consumption_report_btn, member_consumption_btn],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20
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
        """العودة للصفحة السابقة"""
        self.page.clean()
        from pages.reports_page.reports_page import ReportsPage
        self.page.add(ReportsPage(self.page, self.background_image, self.db, self.navigate).get_content())
        self.page.update()
    def navigate_to_reports_current(self):
       """العودة إلى صفحة تقارير الشهر الحالي"""
       self.page.clean()
       self.page.add(self.get_content())
       self.page.update()
    def show_snackbar(self, message):
        """عرض رسالة للمستخدم"""
        self.page.snack_bar = ft.SnackBar(ft.Text(message, style=self.text_style))
        self.page.snack_bar.open = True
        self.page.update()
