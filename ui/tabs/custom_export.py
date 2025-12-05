import flet as ft
from ui.app_state import AppState
from mlife_core.utils.export import STANDARD_CATEGORIES, save_dataframe

class CustomExportTab(ft.Container):
    def __init__(self, page: ft.Page, app_state: AppState):
        super().__init__(padding=20)
        self.page = page
        self.app_state = app_state
        
        # File Picker
        self.save_custom_picker = ft.FilePicker(on_result=self.save_custom_csv)
        self.page.overlay.append(self.save_custom_picker)

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
        self.standard_checkboxes_col = ft.Column()
        self.other_sources_col = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
        
        self.export_selection_btn = ft.ElevatedButton(
            "Auswahl exportieren (0 ausgewählt)",
            icon=ft.Icons.SAVE,
            disabled=True # Initially disabled
        )

        self.export_custom_row = ft.Row([
            ft.ElevatedButton("Export CSV", icon=ft.Icons.DESCRIPTION, bgcolor=ft.Colors.BLUE_100, color=ft.Colors.BLUE_900, on_click=lambda _: self.export_custom_click("csv")),
            ft.ElevatedButton("Export Excel", icon=ft.Icons.TABLE_VIEW, bgcolor=ft.Colors.GREEN_100, color=ft.Colors.GREEN_900, on_click=lambda _: self.export_custom_click("xlsx"))
        ])

        self.content = ft.Column([
            self.anonymize_warning,
            ft.Row([
                # Linke Spalte: Standard Kategorien
                ft.Container(
                    content=ft.Column([
                        self.standard_checkboxes_col,
                        ft.Divider(),
                        ft.Text("Exportieren", size=14, weight=ft.FontWeight.BOLD),
                        self.export_custom_row
                    ]),
                    width=300,
                    padding=10,
                    bgcolor=ft.Colors.GREY_50,
                    border_radius=5,
                    alignment=ft.alignment.top_left
                ),
                # Rechte Spalte: Übrige Quellen
                ft.Container(
                    content=self.other_sources_col,
                    expand=True,
                    padding=10,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    border_radius=5
                )
            ], expand=True)
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

    def update_filter_options(self):
        df = self.app_state.df
        if df is None: return
        
        # 1. Standard Kategorien Checkboxen bauen
        self.standard_checkboxes_col.controls.clear()
        self.standard_checkboxes_col.controls.append(ft.Text("Standard Kategorien", size=18, weight=ft.FontWeight.BOLD))
        
        for label in STANDARD_CATEGORIES.keys():
            chk = ft.Checkbox(
                label=label,
                value=False,
                on_change=lambda e, l=label: self.toggle_standard_category(l, e.control.value)
            )
            self.standard_checkboxes_col.controls.append(chk)

        # 2. "Andere" Quellen finden
        all_sources = set(df['source_type'].astype(str).unique())
        
        # Alle Quellen, die bereits in Standard-Kategorien abgedeckt sind
        covered_sources = set()
        for sources in STANDARD_CATEGORIES.values():
            covered_sources.update(sources)
            
        # Die "Übrigen" sind die Differenz
        other_sources = sorted(list(all_sources - covered_sources))
        
        self.other_sources_col.controls.clear()
        self.other_sources_col.controls.append(ft.Text("Übrige Patientendaten", size=18, weight=ft.FontWeight.BOLD))
        
        if not other_sources:
            self.other_sources_col.controls.append(ft.Text("Keine weiteren Datenquellen gefunden.", italic=True, color=ft.Colors.GREY))
        else:
            for src in other_sources:
                chk = ft.Checkbox(
                    label=src,
                    value=False,
                    on_change=lambda e, s=src: self.toggle_other_source(s, e.control.value)
                )
                self.other_sources_col.controls.append(chk)
        
        self.update()

    def toggle_standard_category(self, category, is_checked):
        if is_checked:
            self.app_state.custom_export["standard_categories"].add(category)
        else:
            self.app_state.custom_export["standard_categories"].discard(category)
        # self.update_export_button_text() # Not needed anymore as we have static buttons, but maybe we want to show count?

    def toggle_other_source(self, source, is_checked):
        if is_checked:
            self.app_state.custom_export["other_sources"].add(source)
        else:
            self.app_state.custom_export["other_sources"].discard(source)
        # self.update_export_button_text()

    def export_custom_click(self, ext):
        count_std = len(self.app_state.custom_export["standard_categories"])
        count_other = len(self.app_state.custom_export["other_sources"])
        if count_std == 0 and count_other == 0:
             self.page.open(ft.SnackBar(ft.Text("Bitte wähle mindestens eine Kategorie aus.")))
             return
        self.save_custom_picker.save_file(allowed_extensions=[ext], file_name=f"custom_export.{ext}")

    def save_custom_csv(self, e: ft.FilePickerResultEvent):
        if not e.path: return
        
        df = self.app_state.df
        if df is None: return
        
        selected_std = self.app_state.custom_export["standard_categories"]
        selected_other = self.app_state.custom_export["other_sources"]
        
        if not selected_std and not selected_other:
            self.page.open(ft.SnackBar(ft.Text("Bitte wähle mindestens eine Kategorie aus.")))
            return

        # Sammle alle source_types, die wir exportieren wollen
        target_source_types = set()
        
        # 1. Aus Standard Kategorien
        for cat in selected_std:
            target_source_types.update(STANDARD_CATEGORIES[cat])
            
        # 2. Aus "Andere"
        target_source_types.update(selected_other)
        
        # Filtern
        filtered_df = df[df['source_type'].isin(target_source_types)]
        
        try:
            count = save_dataframe(filtered_df, e.path)
            self.page.open(ft.SnackBar(ft.Text(f"Gespeichert: {count} Zeilen")))
        except Exception as ex:
            self.page.open(ft.SnackBar(ft.Text(f"Fehler beim Speichern: {ex}")))
