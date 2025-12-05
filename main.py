import flet as ft
import os
from mlife_core.services.pipeline import run_parsing_pipeline
from ui.app_state import AppState
from ui.tabs.overview import OverviewTab
from ui.tabs.anonymize import AnonymizeTab
from ui.tabs.quick_export import QuickExportTab
from ui.tabs.custom_export import CustomExportTab

def main(page: ft.Page):
    # --- Grundeinstellungen der Seite ---
    page.title = "Medical Data Pipeline & Export"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 10
    page.window.height = 900
    page.window.width = 1200

    # --- App State ---
    app_state = AppState()

    # --- UI Komponenten ---

    # 1. Header & Datei-Auswahl
    header_text = ft.Text("mLife Data Parser", size=22, weight=ft.FontWeight.BOLD)
    status_text = ft.Text("Bitte wähle eine CSV-Datei (gesamte_akte.csv aus mLife) aus.", color=ft.Colors.GREY_700, size=12)
    progress_ring = ft.ProgressRing(visible=False, width=16, height=16)
    selected_file_text = ft.Text("Keine Datei ausgewählt", italic=True, size=12)

    def on_file_picked(e: ft.FilePickerResultEvent):
        if e.files:
            path = e.files[0].path
            app_state.filepath = path
            selected_file_text.value = f"Datei: {os.path.basename(path)}"
            process_btn.disabled = False
            page.update()

    file_picker = ft.FilePicker(on_result=on_file_picked)
    page.overlay.append(file_picker)

    select_file_btn = ft.ElevatedButton(
        "Datei auswählen",
        icon=ft.Icons.FOLDER_OPEN,
        on_click=lambda _: file_picker.pick_files(allowed_extensions=["csv", "txt"])
    )

    # Navigation-Funktion für Tabs
    def navigate_to_tab(index: int):
        tabs_control.selected_index = index
        page.update()

    # Tabs initialisieren
    overview_tab = OverviewTab(app_state, on_navigate=navigate_to_tab)
    anonymize_tab = AnonymizeTab(app_state)
    quick_export_tab = QuickExportTab(page, app_state)
    custom_export_tab = CustomExportTab(page, app_state)

    # Tab-Wechsel Handler für Warnungs-Updates
    def on_tab_change(e):
        # Warnungen auf Export-Tabs aktualisieren
        if tabs_control.selected_index == 2:  # Quick Export
            quick_export_tab.update_warning()
        elif tabs_control.selected_index == 3:  # Custom Export
            custom_export_tab.update_warning()

    tabs_control = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        visible=False, # not visible on App-start
        on_change=on_tab_change,
        tabs=[
            ft.Tab(
                text="Übersicht",
                icon=ft.Icons.DASHBOARD,
                content=overview_tab
            ),
            ft.Tab(
                text="Anonymisierung",
                icon=ft.Icons.LOCK,
                content=anonymize_tab
            ),
            ft.Tab(
                text="Quick Export",
                icon=ft.Icons.FLASH_ON,
                content=quick_export_tab
            ),
            ft.Tab(
                text="Custom Export",
                icon=ft.Icons.BUILD,
                content=custom_export_tab
            ),
        ],
        expand=True
    )

    # 2. Pipeline Ausführung
    def run_pipeline_click(e):
        if not app_state.filepath:
            return
        
        # UI auf "Laden" setzen
        process_btn.disabled = True
        select_file_btn.disabled = True
        progress_ring.visible = True
        status_text.value = "Pipeline läuft... Daten werden verarbeitet."
        status_text.color = ft.Colors.BLUE
        page.update()

        try:
            # Pipeline ausführen
            df, patient_name = run_parsing_pipeline(app_state.filepath)
            app_state.df = df
            app_state.patient_name = patient_name
            
            # Erfolgsfall
            status_text.value = f"Erfolg! {len(df)} Datenpunkte geladen. Patient: {patient_name or 'Unbekannt'}"
            status_text.color = ft.Colors.GREEN
            
            # Tabs aktivieren und Daten laden
            tabs_control.visible = True
            big_button_container.visible = False
            overview_tab.update_data()
            anonymize_tab.update_data()
            custom_export_tab.update_filter_options()
            
        except Exception as ex:
            # Fehlerfall
            status_text.value = f"Fehler: {str(ex)}"
            status_text.color = ft.Colors.RED
            import traceback
            traceback.print_exc()
        
        # UI zurücksetzen
        progress_ring.visible = False
        process_btn.disabled = False
        select_file_btn.disabled = False
        page.update()

    process_btn = ft.ElevatedButton(
        "Daten verarbeiten",
        icon=ft.Icons.PLAY_ARROW,
        on_click=run_pipeline_click,
        disabled=True
    )

    # Großer zentraler Button (vor Verarbeitung sichtbar)
    big_process_btn = ft.ElevatedButton(
        "Daten verarbeiten",
        icon=ft.Icons.PLAY_ARROW,
        on_click=run_pipeline_click,
        style=ft.ButtonStyle(
            padding=ft.padding.symmetric(horizontal=50, vertical=20),
            text_style=ft.TextStyle(size=20, weight=ft.FontWeight.BOLD),
        ),
        bgcolor=ft.Colors.BLUE,
        color=ft.Colors.WHITE,
        visible=False
    )

    # Container für den großen Button (zentriert)
    big_button_container = ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.UPLOAD_FILE, size=80, color=ft.Colors.GREY_400),
            ft.Text("Datei ausgewählt - bereit zur Verarbeitung", size=16, color=ft.Colors.GREY_600),
            ft.Container(height=20),
            big_process_btn
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER),
        alignment=ft.alignment.center,
        expand=True,
        visible=False
    )

    # Modifiziere on_file_picked um den großen Button anzuzeigen
    def on_file_picked_updated(e: ft.FilePickerResultEvent):
        if e.files:
            path = e.files[0].path
            app_state.filepath = path
            selected_file_text.value = f"Datei: {os.path.basename(path)}"
            process_btn.disabled = False
            big_process_btn.visible = True
            big_button_container.visible = True
            page.update()

    file_picker.on_result = on_file_picked_updated

    # Haupt-Layout der Seite
    page.add(
        ft.Column([
            # Header Bereich (kompakt)
            ft.Row([header_text], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([
                select_file_btn,
                selected_file_text,
                ft.VerticalDivider(width=15),
                process_btn,
                progress_ring
            ], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            
            ft.Row([status_text], alignment=ft.MainAxisAlignment.CENTER),
            
            # Großer Button vor Verarbeitung
            big_button_container,
            
            # Hauptinhalt (Tabs)
            tabs_control
            
        ], expand=True, spacing=5)
    )

if __name__ == "__main__":
    ft.app(target=main)