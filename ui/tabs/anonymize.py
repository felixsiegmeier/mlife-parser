import flet as ft
from ui.app_state import AppState
import re
import os
import sys
import threading
from typing import List

from deidentifier_engine import (
    is_model_available,
    download_model_with_progress,
    get_model_size_mb,
    anonymize_dataframe,
)


class AnonymizeTab(ft.Container):
    def __init__(self, app_state: AppState):
        super().__init__(padding=20)
        self.app_state = app_state
        self.content_col = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
        self.content = self.content_col
        self.temporal_blacklist = set()
        self._is_downloading = False
        self._is_anonymizing = False
        
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
        
        # Status-Banner für Erfolg/Fehler
        self._status_banner = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.WARNING, color=ft.Colors.WHITE, size=16),
                ft.Text("Daten wurden noch nicht anonymisiert", color=ft.Colors.WHITE, size=13)
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=8),
            bgcolor=ft.Colors.ORANGE,
            padding=ft.padding.symmetric(horizontal=15, vertical=8),
            border_radius=6
        )
        
        # Fortschrittsbalken für Download/Anonymisierung
        self._progress_bar = ft.ProgressBar(width=400, value=0, visible=False)
        self._progress_text = ft.Text("", size=12, color=ft.Colors.GREY_600, visible=False)
        
        # Action Button (dynamisch: Download oder Anonymisieren)
        self._action_button = ft.FloatingActionButton(
            text="Anonymisieren",
            icon=ft.Icons.PLAY_ARROW,
            on_click=self._handle_action_click
        )
        
        # Model-Status Info
        self._model_info = ft.Container(visible=False)

    def _get_combined_blacklist(self) -> List[str]:
        """Kombiniert Session- und permanente Blacklist."""
        combined = list(self.temporal_blacklist)
        combined.extend(self.load_permanent_blacklist())
        return combined

    def _handle_action_click(self, e):
        """Handler für den Action-Button (Download oder Anonymisieren)."""
        if self._is_downloading or self._is_anonymizing:
            return
        
        if not is_model_available():
            self._start_model_download()
        else:
            self._start_anonymization()

    def _start_model_download(self):
        """Startet den Modell-Download in einem separaten Thread."""
        self._is_downloading = True
        self._action_button.disabled = True
        self._action_button.text = "Lädt herunter..."
        self._action_button.icon = ft.Icons.DOWNLOADING
        self._progress_bar.visible = True
        self._progress_bar.value = 0
        self._progress_text.visible = True
        self._progress_text.value = "Starte Download..."
        self.update()
        
        def download_thread():
            def progress_callback(progress: float, status: str):
                self._progress_bar.value = progress
                self._progress_text.value = status
                try:
                    self._progress_bar.update()
                    self._progress_text.update()
                except Exception:
                    pass  # UI möglicherweise nicht mehr verfügbar
            
            success, message = download_model_with_progress(progress_callback)
            
            self._is_downloading = False
            self._progress_bar.visible = False
            self._progress_text.visible = False
            
            if success:
                self._action_button.text = "Anonymisieren"
                self._action_button.icon = ft.Icons.PLAY_ARROW
                self._action_button.disabled = False
                self._update_model_info()
                if self.page:
                    self.page.open(ft.SnackBar(ft.Text("Modell erfolgreich heruntergeladen!")))
            else:
                self._action_button.text = "Modell herunterladen"
                self._action_button.icon = ft.Icons.DOWNLOAD
                self._action_button.disabled = False
                if self.page:
                    self.page.open(ft.SnackBar(ft.Text(f"Fehler: {message}")))
            
            try:
                self.update()
            except Exception:
                pass
        
        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()

    def _start_anonymization(self):
        """Startet die Anonymisierung in einem separaten Thread."""
        if self.app_state.df is None or self.app_state.df.empty:
            if self.page:
                self.page.open(ft.SnackBar(ft.Text("Keine Daten zum Anonymisieren vorhanden.")))
            return
        
        self._is_anonymizing = True
        self._action_button.disabled = True
        self._action_button.text = "Anonymisiert..."
        self._action_button.icon = ft.Icons.HOURGLASS_EMPTY
        self._progress_bar.visible = True
        self._progress_bar.value = 0
        self._progress_text.visible = True
        self._progress_text.value = "Starte Anonymisierung..."
        self.update()
        
        blacklist = self._get_combined_blacklist()
        
        def anonymize_thread():
            def progress_callback(progress: float, status: str):
                self._progress_bar.value = progress
                self._progress_text.value = status
                try:
                    self._progress_bar.update()
                    self._progress_text.update()
                except Exception:
                    pass
            
            try:
                # DataFrame anonymisieren
                anonymized_df = anonymize_dataframe(
                    self.app_state.df,
                    blacklist=blacklist,
                    fuzzy_matching=True,
                    fuzzy_threshold=85,
                    progress_callback=progress_callback
                )
                
                # Original DataFrame ersetzen
                self.app_state.df = anonymized_df
                self.app_state.is_anonymized = True
                
                self._is_anonymizing = False
                self._progress_bar.visible = False
                self._progress_text.visible = False
                self._action_button.text = "Anonymisieren"
                self._action_button.icon = ft.Icons.PLAY_ARROW
                self._action_button.disabled = False
                self._update_status_banner()
                
                # Callback für Status-Update im Hauptfenster aufrufen
                if self.app_state.on_anonymization_complete:
                    self.app_state.on_anonymization_complete()
                
                if self.page:
                    self.page.open(ft.SnackBar(ft.Text("Daten erfolgreich anonymisiert!")))
                
            except Exception as e:
                self._is_anonymizing = False
                self._progress_bar.visible = False
                self._progress_text.visible = False
                self._action_button.text = "Anonymisieren"
                self._action_button.icon = ft.Icons.PLAY_ARROW
                self._action_button.disabled = False
                
                if self.page:
                    self.page.open(ft.SnackBar(ft.Text(f"Fehler: {str(e)}")))
            
            try:
                self.update()
            except Exception:
                pass
        
        thread = threading.Thread(target=anonymize_thread, daemon=True)
        thread.start()

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
        try:
            self._status_banner.update()
        except Exception:
            pass

    def _update_model_info(self):
        """Aktualisiert die Modell-Info-Anzeige."""
        model_available = is_model_available()
        
        if model_available:
            # Modell vorhanden - keine Info anzeigen, nur Button aktualisieren
            self._model_info.visible = False
            self._action_button.text = "Anonymisieren"
            self._action_button.icon = ft.Icons.PLAY_ARROW
        else:
            # Modell fehlt - Hinweis anzeigen
            model_size = get_model_size_mb()
            self._model_info.content = ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.WARNING, color=ft.Colors.ORANGE, size=14),
                    ft.Text("NLP-Modell nicht installiert", size=12, color=ft.Colors.ORANGE_700)
                ], spacing=5),
                ft.Text(f"Für die NLP-Anonymisierung wird ein Sprachmodell benötigt (~{model_size:.0f} MB).", 
                       size=11, color=ft.Colors.GREY_600),
            ], spacing=2)
            self._model_info.visible = True
            self._action_button.text = "Modell herunterladen"
            self._action_button.icon = ft.Icons.DOWNLOAD

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
        
        # Modell-Status aktualisieren
        self._update_model_info()
        
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
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
            ft.Row([self._model_info], alignment=ft.MainAxisAlignment.CENTER),
            ft.Column([
                self._action_button,
                self._progress_bar,
                self._progress_text,
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
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
