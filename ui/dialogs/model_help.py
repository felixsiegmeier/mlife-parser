"""
Dialog-Komponenten für die manuelle SpaCy-Modell Installation.
"""

import flet as ft
import os
import subprocess
import sys
from typing import Callable, Optional

from deidentifier_engine import (
    get_model_directory,
    get_model_size_mb,
    DEFAULT_MODEL_NAME,
    MODEL_VERSION,
    MODEL_URL,
)


def _open_folder(path: str) -> None:
    """Öffnet einen Ordner im System-Dateiexplorer."""
    # Ordner erstellen falls nicht vorhanden
    os.makedirs(path, exist_ok=True)
    
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.run(["open", path])
    else:
        subprocess.run(["xdg-open", path])


def show_model_install_help(page: ft.Page, on_retry: Optional[Callable[[], None]] = None) -> None:
    """
    Zeigt ein BottomSheet mit der ausführlichen Anleitung zur manuellen Installation.
    
    Args:
        page: Die Flet Page-Instanz.
        on_retry: Optionale Callback-Funktion für "Erneut versuchen".
    """
    model_dir = get_model_directory()
    model_size = get_model_size_mb()
    
    def close_sheet(e):
        bottom_sheet.open = False
        page.update()
    
    def open_folder_click(e):
        _open_folder(model_dir)
    
    def open_download_link(e):
        page.launch_url(MODEL_URL)
    
    def retry_click(e):
        bottom_sheet.open = False
        page.update()
        if on_retry:
            on_retry()
    
    content = ft.Container(
        padding=20,
        content=ft.Column(
            spacing=15,
            controls=[
                # Header
                ft.Row([
                    ft.Icon(ft.Icons.DOWNLOAD, size=28, color=ft.Colors.BLUE),
                    ft.Text("Manuelle Modell-Installation", size=20, weight=ft.FontWeight.BOLD),
                ], spacing=10),
                
                ft.Divider(),
                
                ft.Text(
                    "So installierst du das Sprachmodell manuell:",
                    size=14,
                    color=ft.Colors.GREY_700,
                ),
                
                # Schritt 1
                ft.Container(
                    padding=15,
                    bgcolor=ft.Colors.BLUE_50,
                    border_radius=8,
                    content=ft.Column([
                        ft.Row([
                            ft.Container(
                                content=ft.Text("1", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                bgcolor=ft.Colors.BLUE,
                                width=24,
                                height=24,
                                border_radius=12,
                                alignment=ft.alignment.center,
                            ),
                            ft.Text("Lade die Modell-Datei herunter:", weight=ft.FontWeight.W_500),
                        ], spacing=10),
                        ft.Container(height=5),
                        ft.ElevatedButton(
                            f"{DEFAULT_MODEL_NAME}-{MODEL_VERSION}.tar.gz ({model_size:.0f} MB)",
                            icon=ft.Icons.OPEN_IN_NEW,
                            on_click=open_download_link,
                        ),
                    ], spacing=5),
                ),
                
                # Schritt 2
                ft.Container(
                    padding=15,
                    bgcolor=ft.Colors.GREEN_50,
                    border_radius=8,
                    content=ft.Column([
                        ft.Row([
                            ft.Container(
                                content=ft.Text("2", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                bgcolor=ft.Colors.GREEN,
                                width=24,
                                height=24,
                                border_radius=12,
                                alignment=ft.alignment.center,
                            ),
                            ft.Text("Lege die .tar.gz Datei in diesen Ordner:", weight=ft.FontWeight.W_500),
                        ], spacing=10),
                        ft.Container(height=5),
                        ft.Row([
                            ft.Container(
                                content=ft.Text(
                                    "spacy_models/",
                                    font_family="monospace",
                                    size=12,
                                ),
                                bgcolor=ft.Colors.WHITE,
                                padding=8,
                                border_radius=4,
                                border=ft.border.all(1, ft.Colors.GREY_300),
                            ),
                            ft.ElevatedButton(
                                "Ordner öffnen",
                                icon=ft.Icons.FOLDER_OPEN,
                                on_click=open_folder_click,
                            ),
                        ], spacing=10),
                    ], spacing=5),
                ),
                
                # Schritt 3
                ft.Container(
                    padding=15,
                    bgcolor=ft.Colors.ORANGE_50,
                    border_radius=8,
                    content=ft.Column([
                        ft.Row([
                            ft.Container(
                                content=ft.Text("3", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                bgcolor=ft.Colors.ORANGE,
                                width=24,
                                height=24,
                                border_radius=12,
                                alignment=ft.alignment.center,
                            ),
                            ft.Column([
                                ft.Text("Klicke auf 'Erneut versuchen'", weight=ft.FontWeight.W_500),
                                ft.Text(
                                    "Das Programm entpackt die Datei automatisch!",
                                    size=12,
                                    color=ft.Colors.GREY_700,
                                ),
                            ], spacing=2),
                        ], spacing=10),
                    ], spacing=5),
                ),
                
                # Info-Box
                ft.Container(
                    padding=10,
                    bgcolor=ft.Colors.GREY_100,
                    border_radius=8,
                    content=ft.Row([
                        ft.Icon(ft.Icons.INFO, size=16, color=ft.Colors.GREY_600),
                        ft.Text(
                            "Die Datei wird nach dem Entpacken automatisch gelöscht.",
                            size=12,
                            color=ft.Colors.GREY_600,
                            italic=True,
                        ),
                    ], spacing=8),
                ),
                
                ft.Container(height=10),
                
                # Buttons
                ft.Row([
                    ft.TextButton("Schließen", on_click=close_sheet),
                    ft.ElevatedButton(
                        "Erneut versuchen",
                        icon=ft.Icons.REFRESH,
                        on_click=retry_click,
                    ),
                ], alignment=ft.MainAxisAlignment.END, spacing=10),
            ],
        ),
    )
    
    bottom_sheet = ft.BottomSheet(
        content=content,
        open=True,
    )
    
    page.overlay.append(bottom_sheet)
    page.update()


def show_model_error_dialog(
    page: ft.Page,
    error_message: str,
    on_retry: Optional[Callable[[], None]] = None,
) -> None:
    """
    Zeigt einen AlertDialog bei Download-Fehler mit Option zur manuellen Installation.
    
    Args:
        page: Die Flet Page-Instanz.
        error_message: Die Fehlermeldung vom Download-Versuch.
        on_retry: Optionale Callback-Funktion für "Erneut versuchen".
    """
    
    def close_dialog(e):
        dialog.open = False
        page.update()
    
    def show_help(e):
        dialog.open = False
        page.update()
        show_model_install_help(page, on_retry)
    
    def retry_click(e):
        dialog.open = False
        page.update()
        if on_retry:
            on_retry()
    
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row([
            ft.Icon(ft.Icons.WARNING, color=ft.Colors.ORANGE),
            ft.Text("Modell-Download fehlgeschlagen"),
        ], spacing=10),
        content=ft.Column([
            ft.Text(
                "Das Sprachmodell konnte nicht automatisch heruntergeladen werden.",
                size=14,
            ),
            ft.Container(height=10),
            ft.Container(
                padding=10,
                bgcolor=ft.Colors.RED_50,
                border_radius=6,
                content=ft.Text(
                    error_message,
                    size=12,
                    color=ft.Colors.RED_700,
                ),
            ),
            ft.Container(height=10),
            ft.Text(
                "Mögliche Ursachen: Firewall, Proxy oder keine Internetverbindung.",
                size=12,
                color=ft.Colors.GREY_600,
                italic=True,
            ),
        ], tight=True),
        actions=[
            ft.TextButton("Schließen", on_click=close_dialog),
            ft.OutlinedButton("Mehr Infos", icon=ft.Icons.HELP, on_click=show_help),
            ft.ElevatedButton("Erneut versuchen", icon=ft.Icons.REFRESH, on_click=retry_click),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    
    page.overlay.append(dialog)
    dialog.open = True
    page.update()
