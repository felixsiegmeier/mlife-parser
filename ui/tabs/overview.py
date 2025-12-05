import flet as ft
from ui.app_state import AppState
from typing import Callable, Optional


class OverviewTab(ft.Container):
    def __init__(self, app_state: AppState, on_navigate: Optional[Callable[[int], None]] = None):
        super().__init__(padding=20)
        self.app_state = app_state
        self.on_navigate = on_navigate
        self.content_col = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
        self.content = self.content_col

    def update_data(self):
        df = self.app_state.df
        if df is None:
            return

        # Statistiken berechnen
        total_rows = len(df)
        sources = df['source_type'].unique()
        parameters = df['parameter'].nunique()

        # Inhalt neu bauen
        self.content_col.controls = [
            ft.Text("Datensatz Zusammenfassung", size=18, weight=ft.FontWeight.BOLD),
            ft.Row([
                self.stat_card("Zeilen", str(total_rows), ft.Icons.LIST),
                self.stat_card("Quellen", str(len(sources)), ft.Icons.SOURCE),
                self.stat_card("Parameter", str(parameters), ft.Icons.ANALYTICS),
            ]),
            ft.Divider(),
            ft.Text("Schnellzugriff", size=18, weight=ft.FontWeight.BOLD),
            ft.Row([
                self.nav_card("Anonymisierung", "Daten für AI anonymisieren", ft.Icons.LOCK, 1),
                self.nav_card("Quick Export", "Schneller Export der Daten", ft.Icons.FLASH_ON, 2),
                self.nav_card("Custom Export", "Benutzerdefinierter Export", ft.Icons.BUILD, 3),
            ]),
        ]
        self.update()

    def stat_card(self, title, value, icon):
        return ft.Container(
            content=ft.Row([
                ft.Icon(icon, size=24, color=ft.Colors.BLUE_400),
                ft.Column([
                    ft.Text(value, size=20, weight=ft.FontWeight.BOLD),
                    ft.Text(title, size=12, color=ft.Colors.GREY_600)
                ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.START)
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=15, vertical=10),
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=8
        )

    def nav_card(self, title: str, description: str, icon, tab_index: int):
        return ft.Container(
            content=ft.Column([
                ft.Icon(icon, size=30, color=ft.Colors.BLUE),
                ft.Text(title, size=14, weight=ft.FontWeight.BOLD),
                ft.Text(description, size=11, color=ft.Colors.GREY, text_align=ft.TextAlign.CENTER)
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
            padding=15,
            bgcolor=ft.Colors.BLUE_50,
            border_radius=10,
            width=180,
            height=120,
            on_click=lambda e: self._navigate_to(tab_index),
            ink=True
        )

    def _navigate_to(self, tab_index: int):
        if self.on_navigate:
            self.on_navigate(tab_index)

