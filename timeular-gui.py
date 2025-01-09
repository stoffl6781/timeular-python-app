import subprocess
import sys

# Funktion zur Prüfung und Installation von Paketen
def install_and_import(package):
    try:
        # Prüfen, ob das Paket bereits installiert ist
        __import__(package)
    except ImportError:
        # Paket ist nicht installiert, Installation starten
        print(f"{package} ist nicht installiert. Installation wird gestartet...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        

# Pakete prüfen und installieren
REQUIRED_PACKAGES = ["bleak", "tkcalendar"]

for package in REQUIRED_PACKAGES:
    install_and_import(package)

import asyncio
import threading
import tkinter as tk
from tkinter import ttk
from tkinter import Menu, Toplevel
from bleak import BleakScanner, BleakClient
from datetime import datetime
from tkcalendar import Calendar
import time
import json
from report_window import ReportWindow

DEVICE_NAME = "Timeular Tra"

MODEL_NUMBER_UUID = "00002a24-0000-1000-8000-00805f9b34fb"
MANUFACTURER_UUID = "00002a29-0000-1000-8000-00805f9b34fb"
SERIAL_NUMBER_UUID = "00002a25-0000-1000-8000-00805f9b34fb"
HARDWARE_REVISION_UUID = "00002a27-0000-1000-8000-00805f9b34fb"
SOFTWARE_REVISION_UUID = "00002a28-0000-1000-8000-00805f9b34fb"
FIRMWARE_REVISION_UUID = "00002a26-0000-1000-8000-00805f9b34fb"
ORIENTATION_UUID = "c7e70012-c847-11e6-8175-8c89a55d403c"
BATTERY_UUID = "00002a19-0000-1000-8000-00805f9b34fb"
POWER_UUID = "00002a1a-0000-1000-8000-00805f9b34fb"

#Globale Config
CONFIG_FILE = "config.json"
#Calendar Data
ENTRIES_FILE = "entries.json"


class TimeularApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Timeular Timer")
        self.connected_client = None
        self.device_address = None
        self.current_orientation = None
        self.timer_start = None
        self.orientation_log = []
        self.orientation_labels = {
            str(i): {"label": f"Fläche {i}", "color": "#FFFFFF"} for i in range(1, 9)
        }

        #Calendar
        self.calendar_data = {}  # {datum: [(orientierung, dauer, aufgabe, auftrag), ...]}

        #Global Settings
        self.load_config()

        # Layout erstellen
        self.create_menu()
        self.create_layout()

        self.load_calendar_entries()

        # Einträge für das heutige Datum anzeigen
        self.calendar.selection_set(datetime.now().strftime("%Y-%m-%d"))  # Heutiges Datum im Kalender auswählen
        self.show_calendar_entries()

        # Automatische Verbindung versuchen, falls MAC-Adresse vorhanden
        if self.device_address:
            self.auto_connect()

    def create_menu(self):
        """Erstellt das Hauptmenü."""
        menu_bar = Menu(self.root)
        self.root.config(menu=menu_bar)

        # Einstellungen-Menü
        settings_menu = Menu(menu_bar, tearoff=0)
        settings_menu.add_command(label="Geräte", command=self.open_device_settings)
        settings_menu.add_command(label="Labels bearbeiten", command=self.edit_orientation_labels)
        settings_menu.add_separator()
        settings_menu.add_command(label="Exit", command=self.exit_application)
        menu_bar.add_cascade(label="Einstellungen", menu=settings_menu)

    def create_layout(self):
        """Erstellt eine übersichtliche GUI mit 50/50-Aufteilung zwischen Kalender und Timer & Orientierung."""
        self.root.geometry("1000x800")

        # Hauptstruktur: 2 Spalten und dynamische Zeilenhöhe
        self.root.columnconfigure(0, weight=1) 
        self.root.columnconfigure(1, weight=1) 
        self.root.rowconfigure(1, weight=1)
        self.root.rowconfigure(2, weight=1)
        self.root.rowconfigure(3, weight=1)

        # Verbindungsstatus und Batterielevel (oben über die gesamte Breite)
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.connection_status = tk.Label(
            self.status_frame, text="Nicht verbunden", bg="red", fg="white", font=("Helvetica", 12)
        )
        self.connection_status.pack(side="left", padx=5)
        self.battery_label = ttk.Label(self.status_frame, text="Batterie: N/A", font=("Helvetica", 12))
        self.battery_label.pack(side="left", padx=10)

        # Reconnect-Button
        self.reconnect_button = ttk.Button(
            self.status_frame,
            text="Reconnect",
            command=self.auto_connect
        )
        self.reconnect_button.pack(side="right", padx=10)

        self.report_button = ttk.Button(
            self.status_frame,
            text="Bericht öffnen", 
            command=self.open_report
            )
        self.report_button.pack(side="right", padx=10)

        self.power_label = ttk.Label(self.status_frame, text="Ladezustand: N/A", font=("Helvetica", 8))
        self.power_label.pack(side="right", padx=10)

        # Timer und Orientierung (links)
        self.timer_frame = ttk.LabelFrame(self.root, text="Timer")
        self.timer_frame.grid(row=1, column=0, rowspan=2, padx=10, pady=5, sticky="nsew")
        self.timer_label = ttk.Label(self.timer_frame, text=" 0:00", font=("Helvetica", 20, "bold"))
        self.timer_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.orientation_label = ttk.Label(self.timer_frame, text="Pause", font=("Helvetica", 14))
        self.orientation_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        
        # Beschriftung für das erste Eingabefeld
        self.task_label = ttk.Label(self.timer_frame, text="Aufgabe:", font=("Helvetica", 10, "bold"))
        self.task_label.grid(row=2, column=0, padx=5, pady=2, sticky="w")

        # Mehrzeiliges Eingabefeld für "Aufgabe"
        self.task_entry = tk.Text(self.timer_frame, height=5, width=30)
        self.task_entry.grid(row=3, column=0, padx=5, pady=5)

        # Beschriftung für das zweite Eingabefeld
        self.job_label = ttk.Label(self.timer_frame, text="Auftragsnummer:")
        self.job_label.grid(row=4, column=0, padx=5, pady=2, sticky="w")  # Beschriftung linksbündig

        # Eingabefeld für "Auftrag"
        self.job_entry = ttk.Entry(self.timer_frame, width=30)
        self.job_entry.grid(row=5, column=0, padx=5, pady=5)
        self.job_entry.insert(0, "")

        # Kalender (rechts)
        self.calendar_frame = ttk.LabelFrame(self.root, text="Kalender")
        self.calendar_frame.grid(row=1, column=1, rowspan=1, padx=10, pady=5, sticky="nsew")

        self.calendar = Calendar(self.calendar_frame, selectmode="day", date_pattern="yyyy-mm-dd")
        self.calendar.pack(fill="both", expand=True)

        # Event-Handler für Datumsauswahl
        self.calendar.bind("<<CalendarSelected>>", lambda event: self.show_calendar_entries())

        # Frame für Einträge
        self.entry_list_frame = ttk.LabelFrame(self.root, text="Einträge")
        self.entry_list_frame.grid(row=2, column=1, padx=10, pady=5, sticky="nsew")

        # Konfiguration des Frames
        self.entry_list_frame.rowconfigure(0, weight=2)
        self.entry_list_frame.rowconfigure(1, weight=1)
        self.entry_list_frame.columnconfigure(0, weight=1)

        # Listbox
        self.entry_list = tk.Listbox(self.entry_list_frame, height=8)
        self.entry_list.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Buttons
        self.button_frame = ttk.Frame(self.entry_list_frame, height=50)
        self.button_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

        self.show_entries_button = tk.Button(
            self.button_frame, text="Einträge aktualisiseren", command=self.show_calendar_entries, height=2, width=15
        )
        self.show_entries_button.pack(side="left", padx=5, pady=5)

        self.delete_button = tk.Button(
            self.button_frame, text="Löschen", command=self.delete_calendar_entry, height=2, width=10
        )
        self.delete_button.pack(side="left", padx=5, pady=5)

        self.edit_button = tk.Button(
            self.button_frame, text="Ändern", command=self.edit_calendar_entry, height=2, width=10
        )
        self.edit_button.pack(side="left", padx=5, pady=5)



        # Auswertung (unten über die gesamte Breite)
        self.log_frame = ttk.LabelFrame(self.root, text="LOG")
        self.log_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")
        self.log_text = tk.Text(self.log_frame, height=10)
        self.log_text.pack(fill="both", expand=True)

        # Fußzeile
        self.footer_frame = tk.Frame(self.root, bg="#222") 
        self.footer_frame.grid(row=4, column=0, columnspan=2, padx=0, pady=0, sticky="ew")

        # Spaltenzentrierung aktivieren
        self.footer_frame.grid_columnconfigure(0, weight=1)
        self.footer_frame.grid_columnconfigure(1, weight=1)

        # Version & Status
        self.version_label = tk.Label(
            self.footer_frame, text="Version: 1.1.0", font=("Helvetica", 10), fg="white", bg="#222"
        )
        self.version_label.grid(row=0, column=0, pady=5, sticky="w")

        self.footer_label = tk.Label(
            self.footer_frame, text="Load device info", font=("Helvetica", 8), fg="white", bg="#222"
        )

        self.footer_label.grid(row=0, column=1, pady=5, sticky="w")

        # Dynamische Uhrzeit & Datum
        self.time_label = tk.Label(
            self.footer_frame, text="", font=("Helvetica", 10), fg="white", bg="#222"
        )
        self.time_label.grid(row=0, column=2, padx=10, pady=5, sticky="e")

        # Starten des Uhrzeit-Updates
        self.update_time()

    def open_report(self):
        """Öffnet das Bericht-Fenster."""
        report_data = self.get_calendar_data()
        
        # Stelle sicher, dass label_settings verfügbar ist
        label_settings = self.orientation_labels  # Labels und Farben aus der Konfiguration
        
        self.report = ReportWindow(self.root, report_data, label_settings)
        self.report.open()

    def log_message(self, message):
        """Zeigt Nachrichten in der Logbox an."""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def _safe_log(self, message):
        """Schreibt eine Log-Nachricht, entweder in die Konsole oder in das Log-Widget, falls verfügbar."""
        try:
            self.log_message(message)  # Versucht, die Log-Nachricht in der GUI anzuzeigen
        except AttributeError:
            print(message)  # Gibt die Nachricht stattdessen in der Konsole aus

    def exit_application(self):
        """Beendet die Anwendung."""
        self.root.quit()  # Beendet die Haupt-Event-Schleife von Tkinter
        self.root.destroy()  # Schließt das Fenster

    def update_time(self):
        """Aktualisiert die Uhrzeit und das Datum in der Fußzeile."""
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")  # Aktuelles Datum & Zeit
        self.time_label.config(text=f"Zeit: {current_time}")
        self.root.after(1000, self.update_time)  # Aktualisierung jede Sekunde

    def open_device_settings(self):
        """Öffnet ein Popup-Fenster für die Geräteverwaltung."""
        device_window = Toplevel(self.root)
        device_window.title("Geräteverwaltung")
        device_window.geometry("400x300")

        # Geräteliste
        device_list_frame = ttk.LabelFrame(device_window, text="Gefundene Geräte")
        device_list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        device_list = tk.Listbox(device_list_frame, height=10)
        device_list.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(device_list_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")
        device_list.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=device_list.yview)

        # Steuerung
        controls_frame = ttk.Frame(device_window)
        controls_frame.pack(fill="x", padx=10, pady=5)

        scan_button = ttk.Button(
            controls_frame,
            text="Scannen",
            command=lambda: self.scan_devices_popup(device_list),
        )
        scan_button.pack(side="left", padx=5)

        connect_button = ttk.Button(
            controls_frame,
            text="Verbinden",
            command=lambda: self.connect_selected_device(device_list, device_window),
        )
        connect_button.pack(side="left", padx=5)

        disconnect_button = ttk.Button(controls_frame, text="Trennen", command=self.start_disconnect_thread)
        disconnect_button.pack(side="left", padx=5)

    def connect_selected_device(self, device_list, device_window):
        """Speichert das ausgewählte Gerät, verbindet sich und schließt das Popup."""
        selection = device_list.curselection()
        if not selection:
            self.log_message("Kein Gerät ausgewählt.")
            return

        selected_device = device_list.get(selection[0])
        self.device_address = selected_device.split(" - ")[1]

        # MAC-Adresse speichern
        self.save_config()

        # Versuchen, sich zu verbinden
        try:
            self.log_message(f"Verbinde mit {self.device_address}...")
            asyncio.run(self.connect_device())  # Verbindet mit dem Gerät
            self.log_message("Verbindung erfolgreich.")
            device_window.destroy()  # Schließt das Popup
        except Exception as e:
            self.log_message(f"Fehler beim Verbinden: {e}")

    def scan_devices_popup(self, device_list):
        """Startet den Scan nach Geräten in einem separaten Thread und aktualisiert die GUI."""
        self.log_message("Starte Scan...")

        # Leert die Geräteliste in der GUI
        device_list.delete(0, tk.END)

        # Startet den Scan in einem separaten Thread
        def run_scan():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                devices = loop.run_until_complete(BleakScanner.discover())
                self.root.after(0, lambda: self.update_device_list(device_list, devices))
            except Exception as e:
                self.root.after(0, lambda: self.log_message(f"Fehler beim Scannen: {e}"))

        threading.Thread(target=run_scan, daemon=True).start()

    def update_device_list(self, device_list, devices):
        """Aktualisiert die Geräteliste in der GUI mit den gefundenen Geräten."""
        if not devices:
            device_list.insert(tk.END, "Keine Geräte gefunden.")
            self.log_message("Keine Geräte gefunden.")
            return

        for device in devices:
            if device.name:
                device_list.insert(tk.END, f"{device.name} - {device.address}")
                self.log_message(f"Gefunden: {device.name} - {device.address}")
                
    def save_selected_device(self, device_list, device_window):
        """Speichert das ausgewählte Gerät in der Konfigurationsdatei."""
        selection = device_list.curselection()
        if not selection:
            self.log_message("Kein Gerät ausgewählt")
            return

        selected_device = device_list.get(selection[0])
        self.device_address = selected_device.split(" - ")[1]

        # Konfigurationsdatei speichern
        self.save_config()

        self.log_message(f"MAC-Adresse {self.device_address} gespeichert.")
        device_window.destroy()

    def save_config(self):
        """Speichert die MAC-Adresse und Orientierungsetiketten in einer JSON-Konfigurationsdatei."""
        config = {
            "device_address": self.device_address,
            "orientation_labels": self.orientation_labels,
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
        self.log_message("Konfigurationsdatei aktualisiert.")

    def load_config(self):
        """Lädt die Konfigurationsdatei oder erstellt eine neue Datei mit Standardwerten."""
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                self.device_address = config.get("device_address", None)
                
                # Orientation Labels laden und validieren
                loaded_labels = config.get("orientation_labels", {})
                self.orientation_labels = {}
                for i in range(1, 9):
                    key = str(i)
                    if isinstance(loaded_labels.get(key), dict):
                        # Validieren und Standardwerte ergänzen
                        self.orientation_labels[key] = {
                            "label": loaded_labels[key].get("label", f"Fläche {i}"),
                            "color": loaded_labels[key].get("color", "#FFFFFF"),
                        }
                    else:
                        # Standardwert für nicht vorhandene Labels
                        self.orientation_labels[key] = {
                            "label": f"Fläche {i}",
                            "color": "#FFFFFF",
                        }
                self._safe_log(f"Konfiguration geladen. MAC-Adresse: {self.device_address}")
        except FileNotFoundError:
            # Standardwerte, falls die Datei fehlt
            self.device_address = None
            self.orientation_labels = {str(i): {"label": f"Fläche {i}", "color": "#FFFFFF"} for i in range(1, 9)}
            self.save_config()  # Erstellt die Datei
            self._safe_log("Keine Konfigurationsdatei gefunden. Neue Datei erstellt.")
        except Exception as e:
            self._safe_log(f"Fehler beim Laden der Konfigurationsdatei: {e}")

    def auto_connect(self):
        """Versucht, automatisch eine Verbindung zu einem gespeicherten Gerät herzustellen."""
        self.log_message("Versuche automatische Verbindung...")
        if self.device_address:
            try:
                asyncio.run(self.connect_device())
            except Exception as e:
                self.log_message(f"Automatische Verbindung fehlgeschlagen: {e}")
                self.connection_status.config(text="Nicht verbunden", bg="red", fg="white")

    def start_scan_thread(self):
        """Startet den Scanprozess in einem separaten Thread."""
        self.log_message("Starte Scan...")
        self.device_list.delete(0, tk.END)  # Alte Geräte entfernen
        scan_thread = threading.Thread(target=self.scan_devices, daemon=True)
        scan_thread.start()

    def scan_devices(self):
        """Scannt nach Geräten und aktualisiert die GUI."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            devices = loop.run_until_complete(BleakScanner.discover())

            self.log_message(f"{len(devices)} Geräte gefunden.")
            for device in devices:
                if device.name and DEVICE_NAME in device.name:
                    device_entry = f"{device.name} - {device.address}"
                    self.device_list.insert(tk.END, device_entry)
                    self.log_message(f"Gefunden: {device_entry}")

            if not devices:
                self.device_list.insert(tk.END, "Keine Geräte gefunden.")
        except Exception as e:
            self.log_message(f"Fehler beim Scannen: {e}")

    def start_connect_thread(self):
        """Startet den Verbindungsprozess in einem separaten Thread."""
        selection = self.device_list.curselection()
        if not selection:
            self.log_message("Kein Gerät ausgewählt")
            return

        device = self.device_list.get(selection[0])
        self.device_address = device.split(" - ")[1]
        self.log_message(f"Verbinde mit {self.device_address}...")
        connect_thread = threading.Thread(target=self.connect_device, daemon=True)
        connect_thread.start()

    def connect_device(self):
        """Verbindet sich mit einem Gerät."""
        try:
            self.log_message(f"Verbinde mit {self.device_address}...")
            self.notification_thread = threading.Thread(target=self._start_notify_loop, daemon=True)
            self.notification_thread.start()

            # Status auf verbunden setzen
            self.connection_status.config(text="Verbunden", bg="green", fg="white")

            # Einmalige Geräteinfo-Aktualisierung
            asyncio.run(self.fetch_device_info()) 

            # Starte die regelmäßigen Updates
            self.start_battery_update_loop()
            #self.start_device_info_update_loop()

        except Exception as e:
            self.log_message(f"Fehler beim Verbinden: {e}")
            self.connection_status.config(text="Nicht verbunden", bg="red", fg="white")


    async def fetch_battery_level(self):
        """Ruft den Batterielevel vom Gerät ab und aktualisiert die GUI."""
        try:
            if self.connected_client and self.connected_client.is_connected:
                # Batterielevel auslesen
                raw_value = await self.connected_client.read_gatt_char(BATTERY_UUID)
                battery_level = int(raw_value[0])  # Batterielevel ist das erste Byte
                self.root.after(0, lambda: self.battery_label.config(text=f"Batterie: {battery_level}%"))
                self.log_message(f"Batterielevel aktualisiert: {battery_level}%")
                self.connection_status.config(text="Verbunden", bg="green", fg="white")
        except Exception as e:
            self.root.after(0, lambda: self.battery_label.config(text="Batterie: Fehler"))
            self.log_message(f"Fehler beim Abrufen des Batterielevels: {e}")

    def start_battery_update_loop(self):
        """Startet die regelmäßige Aktualisierung des Batterielevels."""
        def run_update():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def update_battery():
                while self.connected_client and self.connected_client.is_connected:
                    await self.fetch_battery_level()
                    await asyncio.sleep(60)  # Alle 60 Sekunden aktualisieren

            try:
                loop.run_until_complete(update_battery())
            except Exception as e:
                self.log_message(f"Fehler in der Batterie-Update-Schleife: {e}")

        # Starte die Batterie-Aktualisierung in einem separaten Thread
        threading.Thread(target=run_update, daemon=True).start()

    def _start_notify_loop(self):
        """Startet den `asyncio`-Loop für Benachrichtigungen."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def notify_task():
            async with BleakClient(self.device_address) as client:
                self.connected_client = client  # Speichere den Client
                self.log_message(f"Verbunden mit {self.device_address}")
                self.connection_status.config(text="Verbunden", bg="green", fg="white")

                # Orientierung-Handler registrieren
                async def orientation_handler(sender, data):
                    #self.log_message(f"Orientierung-Benachrichtigung: Sender={sender}, Data={data}")
                    orientation = int(data[0])
                    self.root.after(0, self._update_gui_orientation, orientation)

                await client.start_notify(ORIENTATION_UUID, orientation_handler)
                #self.log_message("Orientierungs-Benachrichtigungen erfolgreich registriert.")

                # Batterie-Handler registrieren
                async def battery_handler(sender, data):
                    battery_level = int(data[0])  # Batterielevel ist das erste Byte
                    #self.log_message(f"Batterielevel-Benachrichtigung: {battery_level}%")
                    self.root.after(0, lambda: self.battery_label.config(text=f"Batterie: {battery_level}%"))

                await client.start_notify(BATTERY_UUID, battery_handler)
                #self.log_message("Batterie-Benachrichtigungen erfolgreich registriert.")

                # Ladezustand-Handler registrieren
                async def power_handler(sender, data):
                    power_status = int(data[0])  # Ladezustand ist das erste Byte
                    status_text = "Wird geladen" if power_status == 2 else "Wird nicht geladen"
                    #self.log_message(f"Ladezustand-Benachrichtigung: {status_text}")
                    self.root.after(0, lambda: self.power_label.config(text=f"Ladezustand: {status_text}"))

                await client.start_notify(POWER_UUID, power_handler)
                #self.log_message("Ladezustand-Benachrichtigungen erfolgreich registriert.")

                # Halte den Loop offen, um Benachrichtigungen zu empfangen
                while True:
                    await asyncio.sleep(1)

        try:
            loop.run_until_complete(notify_task())
        except Exception as e:
            self.log_message(f"Fehler im Benachrichtigungsprozess: {e}")


    def _update_gui_orientation(self, orientation):
        """Aktualisiert die GUI mit der empfangenen Orientierung."""
        self.log_message(f"Empfangene Orientierung: {orientation}")

        # Wenn die Orientierung ungültig ist (z. B. 0), setze auf "Pause"
        if orientation not in range(1, 9):
            if self.current_orientation is not None:  # Verhindert wiederholtes Setzen auf "Pause"
                if self.timer_start:
                    elapsed = datetime.now() - self.timer_start
                    self.add_new_event()  # Speichert das Event
                    self.save_log(self.current_orientation, elapsed)
                    self.timer_start = None

                self.current_orientation = None
                self.timer_label.config(text="0:00")
                self.orientation_label.config(text="Pause")
                self.log_message("Timer gestoppt. Pause")
            return

        # Starte den Timer bei neuer Orientierung
        if orientation != self.current_orientation:
            if self.timer_start:
                # Speichere die Dauer der vorherigen Orientierung
                elapsed = datetime.now() - self.timer_start
                self.add_new_event()  # Speichert das vorherige Event
                self.save_log(self.current_orientation, elapsed)

            # Aktualisiere die Orientierung und starte den Timer
            self.current_orientation = orientation
            self.timer_start = datetime.now()

            # Hole das Label (nur den Namen) oder verwende einen Standardwert
            label_data = self.orientation_labels.get(str(orientation), {})
            label_name = label_data.get("label", f"Fläche {orientation}")
            self.orientation_label.config(text=f"{label_name}")
            self.log_message(f"Orientierung geändert: {label_name}")

            # Aktualisiere den Timer in der GUI
            self._update_timer_gui()


    def _update_timer_gui(self):
        """Aktualisiert die Timer-Anzeige in der GUI."""
        if self.timer_start:
            elapsed = datetime.now() - self.timer_start
            self.timer_label.config(text=f"{str(elapsed).split('.')[0]}")
            # Aktualisierung alle 500 ms
            self.root.after(500, self._update_timer_gui)


    def _process_orientation(self, orientation):
        """Verarbeitet die empfangene Orientierung und aktualisiert die GUI."""
        try:
            self.log_message(f"Empfangene Orientierung: {orientation}")

            # Überprüfe, ob die Orientierung gültig ist (1-8)
            if orientation not in range(1, 9):
                if self.timer_start:
                    # Stoppe den Timer, wenn die Orientierung ungültig wird
                    elapsed = datetime.now() - self.timer_start
                    self.save_log(self.current_orientation, elapsed)
                    self.timer_start = None
                    self.timer_label.config(text="0:00")
                return

            # Starte den Timer bei neuer Orientierung
            if orientation != self.current_orientation:
                if self.timer_start:
                    # Speichere die vorherige Orientierung und Dauer
                    elapsed = datetime.now() - self.timer_start
                    self.save_log(self.current_orientation, elapsed)

                # Aktualisiere die aktuelle Orientierung
                self.current_orientation = orientation
                self.timer_start = datetime.now()

                # Hole das Label der aktuellen Orientierung
                label_data = self.orientation_labels.get(str(orientation), {})
                label_name = label_data.get("label", f"Fläche {orientation}")

                # Aktualisiere die GUI
                self.orientation_label.config(text=f"{label_name}")
                self.log_message(f"Orientierung geändert: {label_name}")

        except Exception as e:
            self.log_message(f"Fehler beim Verarbeiten der Orientierung: {e}")

    async def fetch_device_info(self):
        """Ruft Geräteinformationen ab und aktualisiert die Fußzeile."""
        try:
            if self.connected_client and self.connected_client.is_connected:
                model_number = await self.connected_client.read_gatt_char(MODEL_NUMBER_UUID)
                manufacturer = await self.connected_client.read_gatt_char(MANUFACTURER_UUID)
                serial_number = await self.connected_client.read_gatt_char(SERIAL_NUMBER_UUID)
                hardware_revision = await self.connected_client.read_gatt_char(HARDWARE_REVISION_UUID)
                software_revision = await self.connected_client.read_gatt_char(SOFTWARE_REVISION_UUID)
                firmware_revision = await self.connected_client.read_gatt_char(FIRMWARE_REVISION_UUID)

                device_info = (
                    f"Model: {model_number.decode('utf-8')}, "
                    f"Manufacturer: {manufacturer.decode('utf-8')}, "
                    f"Serial: {serial_number.decode('utf-8')}, "
                    f"HW: {hardware_revision.decode('utf-8')}, "
                    f"SW: {software_revision.decode('utf-8')}, "
                    f"FW: {firmware_revision.decode('utf-8')}"
                )
                self.footer_label.config(text=device_info)
                self.log_message(f"Geräteinformationen aktualisiert: {device_info}")
            else:
                self.footer_label.config(text="Nicht verbunden")
        except Exception as e:
            self.log_message(f"Fehler beim Abrufen der Geräteinformationen: {e}")
            self.footer_label.config(text="Fehler beim Abrufen der Geräteinformationen")

    def start_device_info_update_loop(self):
        """Startet die regelmäßige Aktualisierung der Geräteinformationen."""
        async def update_device_info():
            while self.connected_client and self.connected_client.is_connected:
                self.log_message("Aktualisiere Geräteinformationen...")  # Debug-Ausgabe
                await self.fetch_device_info()
                await asyncio.sleep(60)

        threading.Thread(target=lambda: asyncio.run(update_device_info()), daemon=True).start()



    def start_disconnect_thread(self):
        """Startet den Trennungsprozess in einem separaten Thread."""
        if self.connected_client is None or not self.connected_client.is_connected:
            self.log_message("Kein Gerät verbunden.")
            return

        self.log_message("Starte Trennungsprozess...")
        disconnect_thread = threading.Thread(target=self.disconnect_device, daemon=True)
        disconnect_thread.start()

    def disconnect_device(self):
        """Trennt die Verbindung und setzt den Status zurück."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Trenne die Verbindung, falls vorhanden
            if self.connected_client:
                loop.run_until_complete(self.connected_client.disconnect())
                self.log_message(f"Verbindung zu {self.device_address} getrennt.")
                self.connected_client = None
                self.device_address = None

            # Setze den Timer und die Orientierung zurück
            self.current_orientation = None
            self.timer_start = None
            self.timer_label.config(text="0:00")
            self.orientation_label.config(text="Pause")

            # Aktualisiere den Verbindungsstatus
            self.connection_status.config(text="Nicht verbunden", bg="red", fg="white")

            # Setze Batterie- und Power-Labels zurück
            self.battery_label.config(text="Batterie: Nicht verfügbar")
            self.power_label.config(text="Ladezustand: Unbekannt")

            # Setze die Fußzeile zurück
            self.footer_label.config(text="Geräteinformationen werden hier angezeigt.")

        except Exception as e:
            self.log_message(f"Fehler beim Trennen: {e}")


    def _notification_handler(self, sender, data):
        """Verarbeitet Orientierungsänderungen."""
        try:
            self.log_message(f"RAW-Daten empfangen: {data}")

            # Konvertiere die empfangenen Daten in die Orientierung
            orientation = int(data[0])
            self.log_message(f"Empfangene Orientierung: {orientation}")

            # Überprüfe, ob die Orientierung gültig ist (1-8)
            if orientation not in range(1, 9):
                if self.timer_start:
                    # Stoppe den Timer, wenn die Orientierung ungültig wird
                    elapsed = datetime.now() - self.timer_start
                    self.save_log(self.current_orientation, elapsed)
                    self.timer_start = None
                    self.timer_label.config(text="0:00")
                return

            # Starte den Timer bei neuer Orientierung
            if orientation != self.current_orientation:
                if self.timer_start:
                    # Speichere die vorherige Orientierung und Dauer
                    elapsed = datetime.now() - self.timer_start
                    self.save_log(self.current_orientation, elapsed)

                # Aktualisiere die aktuelle Orientierung
                self.current_orientation = orientation
                self.timer_start = datetime.now()

                # Hole das Label der aktuellen Orientierung
                label_data = self.orientation_labels.get(str(orientation), {})
                label_name = label_data.get("label", f"Fläche {orientation}")

                # Aktualisiere die GUI
                self.orientation_label.config(text=f"{label_name}")
                self.log_message(f"Orientierung geändert: {label_name}")

        except Exception as e:
            self.log_message(f"Fehler beim Verarbeiten der Orientierung: {e}")


    def save_log(self, orientation, elapsed):
        """Speichert die Aktivität in der Auswertung und im Log."""
        task = self.task_entry.get("1.0", "end-1c")
        job = self.job_entry.get()
        date = self.calendar.get_date()  # Das aktuelle Datum aus dem Kalender holen

        # Log-Meldung erstellen
        log_message = f"Speichere: {date} - Orientierung {orientation}, Dauer: {elapsed}, Aufgabe: {task}, Auftrag: {job}"
        self.log_message(log_message)

    def reset_input_fields(self):
        """Setzt die Eingabefelder für Aufgabe und Auftrag zurück."""
        self.task_entry.delete("1.0", tk.END)
        self.job_entry.delete(0, tk.END)

    #Calendar functions
    def save_calendar_entries(self):
        """Speichert alle Kalendereinträge in der JSON-Datei."""
        try:
            with open(ENTRIES_FILE, "w") as f:
                json.dump(self.calendar_data, f, indent=4)  # Schön formatierte JSON-Ausgabe
            self.log_message(f"Kalendereinträge erfolgreich in {ENTRIES_FILE} gespeichert.")
        except Exception as e:
            self.log_message(f"Fehler beim Speichern der Kalendereinträge: {e}")

    def add_new_event(self):
        """Fügt einen neuen Eintrag basierend auf der aktuellen Orientierung und Zeit hinzu, falls er nicht existiert."""
        task = self.task_entry.get("1.0", "end-1c") 
        job = self.job_entry.get()
        elapsed = datetime.now() - self.timer_start if self.timer_start else "0:00:00"
        date = self.calendar.get_date()
        orientation = self.current_orientation if self.current_orientation else "Pause"

        # Hole das Label der Orientierung oder verwende einen Standardwert
        label_data = self.orientation_labels.get(str(orientation), {})
        label_name = label_data.get("label", f"Fläche {orientation}")

        # Prüfen, ob der Eintrag bereits existiert
        entry = [label_name, str(elapsed).split(".")[0], task, job]
        if date in self.calendar_data:
            for existing_entry in self.calendar_data[date]:
                if existing_entry[0] == label_name and existing_entry[2] == task and existing_entry[3] == job:
                    self.log_message(f"Eintrag bereits vorhanden: {entry} für Datum {date}")
                    return  # Kein erneutes Speichern

        # Speichern des neuen Eintrags
        self.save_calendar_entry(date, label_name, elapsed, task, job)

        self.reset_input_fields()


    def save_calendar_entry(self, date, label, elapsed, task, job):
        """Speichert einen neuen Kalendereintrag und aktualisiert die JSON-Datei."""
        # Sicherstellen, dass das Datum im Kalender existiert
        if date not in self.calendar_data:
            self.calendar_data[date] = []

        # Neuen Eintrag erstellen
        entry = [label, str(elapsed).split(".")[0], task, job]
        if entry not in self.calendar_data[date]:  # Prüfen, ob der Eintrag bereits vorhanden ist
            self.calendar_data[date].append(entry)

        # Speichern in JSON-Datei
        self.save_calendar_entries()

        # Aktualisierung der Kalenderanzeige und Log-Ausgabe
        self.update_calendar_events()
        self.show_calendar_entries()
        self.log_message(f"Neuer Eintrag gespeichert: {entry} für Datum {date}")


    def load_calendar_entries(self):
        """Lädt die Kalendereinträge aus einer JSON-Datei oder erstellt eine neue leere Datei."""
        try:
            with open(ENTRIES_FILE, "r") as f:
                self.calendar_data = json.load(f)
            self._safe_log("Kalendereinträge geladen.")
            self.update_calendar_events()  # Markiert Tage im Kalender
        except FileNotFoundError:
            # Datei erstellen, wenn sie nicht existiert
            self.calendar_data = {} 
            with open(ENTRIES_FILE, "w") as f:
                json.dump(self.calendar_data, f, indent=4)
            self._safe_log("Keine Kalendereinträge gefunden. Neue Datei wurde erstellt.")


    def update_calendar_events(self):
        """Aktualisiert den Kalender und hebt Tage mit Einträgen hervor."""
        self.calendar.calevent_remove("all")  # Alte Events entfernen

        for date in self.calendar_data:
            if self.calendar_data[date]:  # Wenn Einträge vorhanden sind
                date_obj = datetime.strptime(date, "%Y-%m-%d").date()
                self.calendar.calevent_create(date_obj, "Eintrag", "highlight")  # Tag markieren

        # Stil für hervorgehobene Tage anpassen
        self.calendar.tag_config("highlight", background="lightgreen", foreground="black")

    def show_calendar_entries(self):
        """Zeigt die Einträge für das ausgewählte Datum in der Liste an."""
        selected_date = self.calendar.get_date()  # Vom Benutzer ausgewähltes Datum
        self.entry_list.delete(0, tk.END)  # Alte Einträge löschen

        if selected_date in self.calendar_data:
            seen_entries = set()  # Set zur Vermeidung von Duplikaten
            for entry in self.calendar_data[selected_date]:
                try:
                    if isinstance(entry, dict):
                        # Konvertiere dict in tuple
                        label = entry.get("label", "Unbekannt")
                        elapsed = entry.get("duration", "0:00:00")
                        task = entry.get("task", "")
                        job = entry.get("job", "")
                        entry_tuple = (label, elapsed, task, job)
                    elif isinstance(entry, list):
                        # Verarbeite Liste
                        if len(entry) >= 4:
                            label, elapsed, task, job = entry
                        else:
                            label, elapsed, task, job = "Unbekannt", "0:00:00", "", ""
                        entry_tuple = (label, elapsed, task, job)
                    else:
                        # Unbekanntes Format überspringen
                        print(f"Unbekanntes Format in Einträgen: {entry}")
                        continue

                    # Prüfen, ob der Eintrag bereits angezeigt wurde
                    if entry_tuple not in seen_entries:
                        entry_text = f"{label}, Dauer: {elapsed}, Aufgabe: {task}, Auftrag: {job}"
                        self.entry_list.insert(tk.END, entry_text)
                        seen_entries.add(entry_tuple)
                except Exception as e:
                    print(f"Fehler beim Verarbeiten des Eintrags: {entry}, Fehler: {e}")
        else:
            self.entry_list.insert(tk.END, "Keine Einträge für dieses Datum.")



    def delete_calendar_entry(self):
        """Löscht den ausgewählten Eintrag aus der Datei und aktualisiert die GUI."""
        selected_index = self.entry_list.curselection()
        if not selected_index:
            self.log_message("Kein Eintrag ausgewählt.")
            return

        selected_date = self.calendar.get_date()
        selected_entry = self.calendar_data[selected_date][selected_index[0]]

        # Löschen des Eintrags
        del self.calendar_data[selected_date][selected_index[0]]

        # Wenn keine Einträge mehr für das Datum vorhanden sind, löschen
        if not self.calendar_data[selected_date]:
            del self.calendar_data[selected_date]

        # Änderungen speichern
        self.save_calendar_entries()

        # Frontend aktualisieren
        self.update_calendar_events()
        self.show_calendar_entries()

        self.log_message(f"Eintrag gelöscht: {selected_entry}")

    
    def edit_calendar_entry(self):
        """Bearbeitet den ausgewählten Kalendereintrag."""
        selected_index = self.entry_list.curselection()
        if not selected_index:
            self.log_message("Kein Eintrag ausgewählt.")
            return

        selected_date = self.calendar.get_date()
        entry = self.calendar_data[selected_date][selected_index[0]]

        # Popup-Fenster für Bearbeitung
        edit_window = Toplevel(self.root)
        edit_window.title("Eintrag bearbeiten")
        edit_window.geometry("400x500")

        # Datum ändern
        ttk.Label(edit_window, text="Datum (yyyy-mm-dd)").pack(pady=5)
        date_entry = ttk.Entry(edit_window, width=30)
        date_entry.insert(0, selected_date)
        date_entry.pack(pady=5)

        # Orientierung ändern (Dropdown)
        ttk.Label(edit_window, text="Orientierung").pack(pady=5)
        orientation_var = tk.StringVar(value=entry[0])
        orientation_dropdown = ttk.Combobox(
            edit_window,
            textvariable=orientation_var,
            values=[self.orientation_labels[str(i)]["label"] for i in range(1, 9)],
            state="readonly"
        )
        orientation_dropdown.pack(pady=5)

        # Zeit ändern
        ttk.Label(edit_window, text="Zeit (Dauer)").pack(pady=5)
        time_entry = ttk.Entry(edit_window, width=30)
        time_entry.insert(0, entry[1])  # Aktuelle Zeit
        time_entry.pack(pady=5)

        # Aufgabe ändern
        ttk.Label(edit_window, text="Aufgabe").pack(pady=5)
        task_entry = tk.Text(edit_window, width=30, height=5, wrap="word")  # Mehrzeiliges Textfeld
        task_entry.insert("1.0", entry[2])  # Eintrag in das Textfeld einfügen
        task_entry.pack(pady=5)

        # Auftrag ändern
        ttk.Label(edit_window, text="Auftrag").pack(pady=5)
        job_entry = ttk.Entry(edit_window, width=30)
        job_entry.insert(0, entry[3])
        job_entry.pack(pady=5)

        # Speichern-Button
        def save_changes():
            new_date = date_entry.get()
            new_orientation = orientation_var.get()
            new_time = time_entry.get()
            new_task = task_entry.get("1.0", "end-1c")
            new_job = job_entry.get()

            # Validierung der Datumseingabe
            try:
                datetime.strptime(new_date, "%Y-%m-%d")
            except ValueError:
                self.log_message("Ungültiges Datum. Bitte im Format yyyy-mm-dd eingeben.")
                return

            # Entferne alten Eintrag
            del self.calendar_data[selected_date][selected_index[0]]
            if not self.calendar_data[selected_date]:
                del self.calendar_data[selected_date]  # Lösche Datum, falls leer

            # Füge aktualisierten Eintrag hinzu
            self.save_calendar_entry(new_date, new_orientation, new_time, new_task, new_job)

            # Fenster schließen und GUI aktualisieren
            edit_window.destroy()
            self.update_calendar_events()
            self.show_calendar_entries()
            self.log_message("Eintrag geändert.")

        ttk.Button(edit_window, text="Speichern", command=save_changes).pack(pady=10)

    #Globale Settings
    def round_time(self, minutes):
        """Rundet die Zeit auf die nächsten `minutes` Minuten."""
        rounded_seconds = ((minutes * 60 + 59) // 60) * 60
        return rounded_seconds
    
    def save_settings(self, settings):
        """Speichert globale Einstellungen in einer JSON-Datei."""
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f)

    def load_settings(self):
        """Lädt globale Einstellungen aus einer JSON-Datei."""
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"rounding": 5}  # Standardwerte

    def update_timer_orientation_label(self):
        """Aktualisiert die Anzeige der aktuellen Orientierung im Timer."""
        if self.current_orientation:
            # Hole das benutzerdefinierte Label oder Standardlabel
            label = self.orientation_labels.get(self.current_orientation, f"Fläche {self.current_orientation}")
            self.orientation_label.config(text=f"{label}")
        else:
            self.orientation_label.config(text="Pause")

    def edit_orientation_labels(self):
        """Öffnet ein Fenster, um die Orientierung/Labels und deren Farben zu bearbeiten."""
        edit_window = Toplevel(self.root)
        edit_window.title("Orientierungen bearbeiten")
        edit_window.geometry("400x500")

        # Frame für Orientierungseinstellungen
        labels_frame = ttk.LabelFrame(edit_window, text="Orientierung Labels und Farben")
        labels_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Eingabefelder für jede Orientierung
        label_entries = {}
        color_entries = {}
        for i in range(1, 9):  # Orientierung 1 bis 8
            ttk.Label(labels_frame, text=f"Orientierung {i}:").grid(row=i, column=0, padx=5, pady=5, sticky="e")

            # Labelname bearbeiten
            label_var = tk.StringVar(value=self.orientation_labels.get(str(i), {}).get("label", f"Fläche {i}"))
            label_entry = ttk.Entry(labels_frame, textvariable=label_var, width=25)
            label_entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            label_entries[str(i)] = label_var

            # Farbcode bearbeiten
            ttk.Label(labels_frame, text="Farbe (HEX):").grid(row=i, column=2, padx=5, pady=5, sticky="e")
            color_var = tk.StringVar(value=self.orientation_labels.get(str(i), {}).get("color", "#FFFFFF"))
            color_entry = ttk.Entry(labels_frame, textvariable=color_var, width=10)
            color_entry.grid(row=i, column=3, padx=5, pady=5, sticky="w")
            color_entries[str(i)] = color_var

        def save_orientation_labels():
            """Speichert die geänderten Orientierung Labels und Farben."""
            for i in range(1, 9):
                self.orientation_labels[str(i)] = {
                    "label": label_entries[str(i)].get(),
                    "color": color_entries[str(i)].get()
                }

            # Speichere die aktualisierten Labels in der Konfigurationsdatei
            self.save_orientation_labels_to_config()

            # Aktualisiere das Timer-Label sofort
            self.update_timer_orientation_label()

            self.log_message("Orientierung Labels und Farben aktualisiert.")
            edit_window.destroy()

        ttk.Button(edit_window, text="Speichern", command=save_orientation_labels).pack(pady=10)

        # Abbrechen-Button
        ttk.Button(edit_window, text="Abbrechen", command=edit_window.destroy).pack()


    def save_orientation_labels_to_config(self):
        """Speichert die Orientierungslabels und Farben in der Konfigurationsdatei."""
        config = {
            "device_address": self.device_address,
            "orientation_labels": self.orientation_labels
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
        self.log_message("Orientierungslabels und Farben in der Konfiguration gespeichert.")

    def load_orientation_labels(self):
        """Lädt die Orientierungslabels und Farben aus der Konfigurationsdatei."""
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                self.orientation_labels = config.get("orientation_labels", {})
                self.log_message("Orientierungslabels und Farben geladen.")
        except FileNotFoundError:
            # Standardwerte, wenn Datei fehlt
            self.orientation_labels = {str(i): {"label": f"Fläche {i}", "color": "#FFFFFF"} for i in range(1, 9)}
            self.log_message("Keine Konfigurationsdatei gefunden. Standardlabels und -farben werden verwendet.")


    #Report Data
    def get_calendar_data(self, start_date=None, end_date=None):
        """
        Gibt die Kalenderdaten zurück, optional gefiltert nach einem Datumsbereich.
        :param start_date: Startdatum (YYYY-MM-DD) als String oder None
        :param end_date: Enddatum (YYYY-MM-DD) als String oder None
        :return: Liste der gefilterten Einträge
        """
        filtered_data = []
        for date, entries in self.calendar_data.items():
            if start_date and date < start_date:
                continue
            if end_date and date > end_date:
                continue
            for entry in entries:
                filtered_data.append({
                    "date": date,
                    "label": entry[0],
                    "duration": entry[1],
                    "task": entry[2],
                    "job": entry[3],
                })
        return filtered_data

if __name__ == "__main__":
    
    root = tk.Tk()
    app = TimeularApp(root)
    root.mainloop()
