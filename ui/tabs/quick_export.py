import flet as ft
from ui.app_state import AppState
from mlife_core.utils.export import get_subset_df, save_dataframe

class QuickExportTab(ft.Container):
    def __init__(self, page: ft.Page, app_state: AppState):
        super().__init__(padding=20)
        self.page = page
        self.app_state = app_state
        
        # File Pickers
        self.save_all_picker = ft.FilePicker(on_result=self.export_all_result)
        self.subset_file_picker = ft.FilePicker(on_result=self.save_subset_result)
        self.page.overlay.extend([self.save_all_picker, self.subset_file_picker])

        # Status-Banner (immer sichtbar, Farbe je nach Anonymisierungsstatus)
        self.anonymize_warning = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.WARNING, color=ft.Colors.WHITE, size=16),
                ft.Text("Achtung: Die Daten wurden noch nicht anonymisiert!", color=ft.Colors.WHITE, size=13)
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=8),
            bgcolor=ft.Colors.ORANGE,
            padding=ft.padding.symmetric(horizontal=15, vertical=8),
            border_radius=6
        )

        # UI Components
        self.export_all_row = ft.Row([
            ft.ElevatedButton(
                "Alles als CSV",
                icon=ft.Icons.DESCRIPTION,
                bgcolor=ft.Colors.BLUE_100,
                color=ft.Colors.BLUE_900,
                on_click=lambda _: self.save_all_picker.save_file(allowed_extensions=["csv"], file_name="full_export.csv")
            ),
            ft.ElevatedButton(
                "Alles als Excel",
                icon=ft.Icons.TABLE_VIEW,
                bgcolor=ft.Colors.GREEN_100,
                color=ft.Colors.GREEN_900,
                on_click=lambda _: self.save_all_picker.save_file(allowed_extensions=["xlsx"], file_name="full_export.xlsx")
            )
        ])

        self.quick_export_grid = ft.GridView(
            expand=True,
            max_extent=300,
            child_aspect_ratio=1.5,
            spacing=10,
            run_spacing=10,
        )
        
        self.build_grid()

        self.content = ft.Column([
            self.anonymize_warning,
            ft.Text("Schnell-Export Optionen", size=18, weight=ft.FontWeight.BOLD),
            self.export_all_row,
            ft.Divider(),
            ft.Text("Spezifische Datensätze exportieren:", size=14),
            self.quick_export_grid
        ], expand=True)

    def update_warning(self):
        if self.app_state.is_anonymized:
            self.anonymize_warning.content = ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.WHITE, size=16),
                ft.Text("Daten wurden anonymisiert", color=ft.Colors.WHITE, size=13)
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=8)
            self.anonymize_warning.bgcolor = ft.Colors.GREEN
        else:
            self.anonymize_warning.content = ft.Row([
                ft.Icon(ft.Icons.WARNING, color=ft.Colors.WHITE, size=16),
                ft.Text("Achtung: Die Daten wurden noch nicht anonymisiert!", color=ft.Colors.WHITE, size=13)
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=8)
            self.anonymize_warning.bgcolor = ft.Colors.ORANGE
        self.anonymize_warning.update()

    def build_grid(self):
        export_options = [
            {"title": "Vitalwerte", "key": "vitals", "icon": ft.Icons.MONITOR_HEART, "desc": "HF, NIBP, SpO2..."},
            {"title": "Laborwerte", "key": "lab", "icon": ft.Icons.SCIENCE, "desc": "Blutwerte, Urin..."},
            {"title": "Respirator", "key": "respiratory", "icon": ft.Icons.AIR, "desc": "Beatmungsparameter"},
            {"title": "Medikamente", "key": "medication", "icon": ft.Icons.MEDICATION, "desc": "Verabreichte Meds"},
            {"title": "Impella", "key": "impella", "icon": ft.Icons.DEVICE_THERMOSTAT, "desc": "Pumpenparameter"},
            {"title": "CRRT (Hämofilter)", "key": "crrt", "icon": ft.Icons.WATER_DROP, "desc": "Dialyse Daten"},
            {"title": "ECMO", "key": "ecmo", "icon": ft.Icons.HEART_BROKEN, "desc": "ECMO Parameter"},
            {"title": "NIRS", "key": "nirs", "icon": ft.Icons.SENSORS, "desc": "Sauerstoffsättigung Gewebe"},
            {"title": "Arzt Verlauf", "key": "doctor_notes", "icon": ft.Icons.NOTE, "desc": "Verlaufsdokumentation"},
        ]

        for opt in export_options:
            def create_on_click(k, t, ext):
                return lambda e: self.export_subset_click(e, k, t, ext)

            card = ft.Container(
                content=ft.Column([
                    ft.Icon(opt["icon"], size=30, color=ft.Colors.BLUE),
                    ft.Text(opt["title"], weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                    ft.Text(opt["desc"], size=12, color=ft.Colors.GREY, text_align=ft.TextAlign.CENTER),
                    ft.Row([
                        ft.ElevatedButton("CSV", bgcolor=ft.Colors.BLUE_100, color=ft.Colors.BLUE_900, on_click=create_on_click(opt["key"], opt["title"], "csv")),
                        ft.ElevatedButton("Excel", bgcolor=ft.Colors.GREEN_100, color=ft.Colors.GREEN_900, on_click=create_on_click(opt["key"], opt["title"], "xlsx"))
                    ], alignment=ft.MainAxisAlignment.CENTER)
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=ft.Colors.BLUE_50,
                border_radius=10,
                padding=10,
            )
            self.quick_export_grid.controls.append(card)

    def export_subset_click(self, e, key, title, ext):
        df_subset = get_subset_df(self.app_state.df, key)
        if df_subset.empty:
            self.page.open(ft.SnackBar(ft.Text(f"Keine Daten für '{title}' gefunden.")))
            return
            
        self.app_state.export_df = df_subset
        self.subset_file_picker.save_file(allowed_extensions=[ext], file_name=f"{key}_export.{ext}")

    def save_subset_result(self, e: ft.FilePickerResultEvent):
        if not e.path: return
        df_subset = self.app_state.export_df
        if df_subset is None: return
        try:
            count = save_dataframe(df_subset, e.path)
            self.page.open(ft.SnackBar(ft.Text(f"Gespeichert: {count} Zeilen")))
        except Exception as ex:
            self.page.open(ft.SnackBar(ft.Text(f"Fehler beim Speichern: {ex}")))

    def export_all_result(self, e: ft.FilePickerResultEvent):
        if not e.path: return
        df = self.app_state.df
        if df is None: return
        try:
            save_dataframe(df, e.path)
            self.page.open(ft.SnackBar(ft.Text("Kompletter Datensatz gespeichert!")))
        except Exception as ex:
            self.page.open(ft.SnackBar(ft.Text(f"Fehler: {ex}")))
