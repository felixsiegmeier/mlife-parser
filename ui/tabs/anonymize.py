import flet as ft
from ui.app_state import AppState
import re
import os
import sys
from typing import List


class AnonymizeTab(ft.Container):
    def __init__(self, app_state: AppState):
        super().__init__(padding=20)
        self.app_state = app_state
        self.content_col = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
        self.content = self.content_col
        self.temporal_blacklist = set()
        # ListView-Referenzen für UI-Updates
        self._temporal_listview = ft.ListView(spacing=5, height=200)
        self._permanent_listview = ft.ListView(spacing=5, height=200)
        # TextField-Referenzen
        self._temporal_input = ft.TextField(
            label="Begriffe hinzufügen",
            hint_text="Komma, Leerzeichen, etc. als Trenner",
            expand=True,
            on_submit=self._handle_add_temporal
        )
        self._permanent_input = ft.TextField(
            label="Begriffe hinzufügen",
            hint_text="Komma, Leerzeichen, etc. als Trenner",
            expand=True,
            on_submit=self._handle_add_permanent
        )
        # Status-Banner für Erfolg/Fehler (immer sichtbar)
        self._status_banner = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.WARNING, color=ft.Colors.WHITE, size=16),
                ft.Text("Daten wurden noch nicht anonymisiert", color=ft.Colors.WHITE, size=13)
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=8),
            bgcolor=ft.Colors.ORANGE,
            padding=ft.padding.symmetric(horizontal=15, vertical=8),
            border_radius=6
        )

    def _handle_anonymize_click(self, e):
        # TODO: Hier später die echte Anonymisierungs-Logik implementieren
        # Vorerst nur den Status setzen
        self.app_state.is_anonymized = True
        self._update_status_banner()

    def _update_status_banner(self):
        if self.app_state.is_anonymized:
            self._status_banner.content = ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.WHITE, size=16),
                ft.Text("Daten wurden erfolgreich anonymisiert", color=ft.Colors.WHITE, size=13)
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=8)
            self._status_banner.bgcolor = ft.Colors.GREEN
        else:
            self._status_banner.content = ft.Row([
                ft.Icon(ft.Icons.WARNING, color=ft.Colors.WHITE, size=16),
                ft.Text("Daten wurden noch nicht anonymisiert", color=ft.Colors.WHITE, size=13)
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=8)
            self._status_banner.bgcolor = ft.Colors.ORANGE
        self._status_banner.update()

    def update_data(self):
        patient_name = self.app_state.patient_name or ""
        self.temporal_blacklist = set(self.parse_inputs(patient_name))
        
        # Status-Banner aktualisieren
        if self.app_state.is_anonymized:
            self._status_banner.content = ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.WHITE, size=16),
                ft.Text("Daten wurden erfolgreich anonymisiert", color=ft.Colors.WHITE, size=13)
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=8)
            self._status_banner.bgcolor = ft.Colors.GREEN
        else:
            self._status_banner.content = ft.Row([
                ft.Icon(ft.Icons.WARNING, color=ft.Colors.WHITE, size=16),
                ft.Text("Daten wurden noch nicht anonymisiert", color=ft.Colors.WHITE, size=13)
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=8)
            self._status_banner.bgcolor = ft.Colors.ORANGE
        
        # Inhalt neu bauen
        self.content_col.controls = [
            self._status_banner,
            ft.Row([
                ft.Text("Anonymisierung der Daten", size=18, weight=ft.FontWeight.BOLD),
                ft.Icon(ft.Icons.LOCK, color=ft.Colors.GREY)
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Text("Für die Verwendung mit AI müssen alle personenbezogenen Daten entfernt werden."),
            ft.Text("Die Anonymisierung verwendet einen lokalen AI-Algorithmus (nicht absolut sicher).", size=12, color=ft.Colors.GREY_600),
            ft.Text("Außerdem werden alle Begriffe der Blacklist entfernt (absolut sicher, case-insensitive).", size=12, color=ft.Colors.GREY_600),
            ft.FloatingActionButton(
                text="Anonymisieren",
                icon=ft.Icons.PLAY_ARROW,
                on_click=self._handle_anonymize_click
            ),
            ft.Row([
                ft.Column([
                    self.render_temporal_blacklist(),
                ], expand=1),
                ft.Column([
                    self.render_permanent_blacklist()
                ], expand=1)
            ])
        ]
        self.content_col.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.update()

    def parse_inputs(self, text: str) -> List[str]:
        # Trenne den Text anhand von Kommas, Leerzeichen, Bindestrichen, Unterstrichen, Semikolons oder Pipes und bereinige die Einträge
        entries = [entry.strip() for entry in re.split(r'[,\s\-_;|]+', text) if entry.strip()]
        return entries

    def get_blacklist_path(self):
        if getattr(sys, 'frozen', False):
            # Wenn als PyInstaller-Exe ausgeführt
            application_path = os.path.dirname(sys.executable)
        else:
            # Im Entwicklungsmodus
            application_path = os.getcwd()
        return os.path.join(application_path, 'blacklist.txt')

    def load_permanent_blacklist(self) -> List[str]:
        path = self.get_blacklist_path()
        if not os.path.exists(path):
            return []
        with open(path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f.readlines() if line.strip()]

    def save_permanent_blacklist(self, blacklist: List[str]):
        path = self.get_blacklist_path()
        with open(path, 'w', encoding='utf-8') as f:
            for item in blacklist:
                f.write(f"{item}\n")

    def add_to_permanent_blacklist(self, entry: str):
        current_list = self.load_permanent_blacklist()
        if entry and entry not in current_list:
            current_list.append(entry)
            self.save_permanent_blacklist(current_list)
            self.update()

    def remove_from_permanent_blacklist(self, entry: str):
        current_list = self.load_permanent_blacklist()
        if entry in current_list:
            current_list.remove(entry)
            self.save_permanent_blacklist(current_list)
            self.update()

    def add_to_temporal_blacklist(self, text: str):
        entries = self.parse_inputs(text)
        for entry in entries:
            if entry:
                self.temporal_blacklist.add(entry)
        self._refresh_temporal_listview()

    def remove_from_temporal_blacklist(self, entry: str):
        if entry in self.temporal_blacklist:
            self.temporal_blacklist.remove(entry)
            self._refresh_temporal_listview()

    def _refresh_temporal_listview(self):
        self._temporal_listview.controls = [
            ft.Row([
                ft.Text(item, expand=True),
                ft.IconButton(
                    icon=ft.Icons.DELETE,
                    icon_color=ft.Colors.RED_400,
                    tooltip="Entfernen",
                    on_click=lambda e, i=item: self.remove_from_temporal_blacklist(i)
                )
            ]) for item in sorted(self.temporal_blacklist)
        ]
        self._temporal_listview.update()

    def _refresh_permanent_listview(self):
        items = self.load_permanent_blacklist()
        self._permanent_listview.controls = [
            ft.Row([
                ft.Text(item, expand=True),
                ft.IconButton(
                    icon=ft.Icons.DELETE,
                    icon_color=ft.Colors.RED_400,
                    tooltip="Entfernen",
                    on_click=lambda e, i=item: self._handle_remove_permanent(i)
                )
            ]) for item in sorted(items)
        ]
        self._permanent_listview.update()

    def _handle_add_temporal(self, e):
        if self._temporal_input.value:
            self.add_to_temporal_blacklist(self._temporal_input.value)
            self._temporal_input.value = ""
            self._temporal_input.update()

    def _handle_add_permanent(self, e):
        if self._permanent_input.value:
            entries = self.parse_inputs(self._permanent_input.value)
            for entry in entries:
                self.add_to_permanent_blacklist(entry)
            self._permanent_input.value = ""
            self._permanent_input.update()
            self._refresh_permanent_listview()

    def _handle_remove_permanent(self, entry: str):
        self.remove_from_permanent_blacklist(entry)
        self._refresh_permanent_listview()

    def render_temporal_blacklist(self):
        # Initial-Befüllung der ListView
        self._temporal_listview.controls = [
            ft.Row([
                ft.Text(item, expand=True),
                ft.IconButton(
                    icon=ft.Icons.DELETE,
                    icon_color=ft.Colors.RED_400,
                    tooltip="Entfernen",
                    on_click=lambda e, i=item: self.remove_from_temporal_blacklist(i)
                )
            ]) for item in sorted(self.temporal_blacklist)
        ]

        return ft.Column([
            ft.Text("Session-Blacklist", weight=ft.FontWeight.BOLD, size=14),
            ft.Row([
                self._temporal_input,
                ft.IconButton(
                    icon=ft.Icons.ADD,
                    icon_color=ft.Colors.BLUE,
                    tooltip="Hinzufügen",
                    on_click=self._handle_add_temporal
                )
            ]),
            ft.Container(
                content=self._temporal_listview,
                border=ft.border.all(1, ft.Colors.GREY_300),
                border_radius=5,
                padding=10
            )
        ], spacing=10)

    def render_permanent_blacklist(self):
        # Initial-Befüllung der ListView
        items = self.load_permanent_blacklist()
        self._permanent_listview.controls = [
            ft.Row([
                ft.Text(item, expand=True),
                ft.IconButton(
                    icon=ft.Icons.DELETE,
                    icon_color=ft.Colors.RED_400,
                    tooltip="Entfernen",
                    on_click=lambda e, i=item: self._handle_remove_permanent(i)
                )
            ]) for item in sorted(items)
        ]

        return ft.Column([
            ft.Text("Permanente Blacklist", weight=ft.FontWeight.BOLD, size=14),
            ft.Row([
                self._permanent_input,
                ft.IconButton(
                    icon=ft.Icons.ADD,
                    icon_color=ft.Colors.BLUE,
                    tooltip="Hinzufügen",
                    on_click=self._handle_add_permanent
                )
            ]),
            ft.Container(
                content=self._permanent_listview,
                border=ft.border.all(1, ft.Colors.GREY_300),
                border_radius=5,
                padding=10
            )
        ], spacing=10)
