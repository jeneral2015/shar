import flet as ft
from utils.button_utils import create_button
from .current_reports.current_reports import CurrentReportsPage
from .archived_reports.archived_reports import ArchivedReportsPage

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
        title = ft.Text(
            "التقارير",
            style=self.title_style,
            color="white",
            text_align=ft.TextAlign.CENTER
        )
        
        buttons = [
            create_button(
                text="الشهر الحالي",
                on_click=lambda e: self.navigate_to("current_reports"),
                bgcolor=ft.colors.GREEN
            ),
            create_button(
                text="الأشهر السابقة",
                on_click=lambda e: self.navigate_to("archived_reports"),
                bgcolor=ft.colors.BLUE
            ),
            create_button(
                text="رجوع",
                on_click=lambda e: self.navigate("main_page"),
                bgcolor=ft.colors.RED
            )
        ]

        buttons_row = ft.Row(
            controls=buttons,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20
        )

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(height=20),
                    title,
                    ft.Container(height=150),
                    buttons_row,
                ],
                alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            image_src=self.background_image.src,
            image_fit=ft.ImageFit.COVER,
            expand=True
        )

    def navigate_to(self, page_name):
        try:
            self.page.clean()
            if page_name == "current_reports":
                report_page = CurrentReportsPage(self.page, self.background_image, self.db, self.navigate)
            elif page_name == "archived_reports":
                report_page = ArchivedReportsPage(self.page, self.background_image, self.db, self.navigate)
            
            self.page.add(report_page.get_content())
            self.page.update()
        except Exception as e:
            print(f"Navigation error: {str(e)}")
            self.page.snack_bar = ft.SnackBar(ft.Text("حدث خطأ في تحميل الصفحة!", style=self.text_style))
            self.page.snack_bar.open = True
            self.page.update()
