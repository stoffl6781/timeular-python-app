import asyncio
import threading
import tkinter as tk
from tkinter import ttk
from bleak import BleakScanner, BleakClient
from datetime import datetime

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


class TimeularApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Timeular Timer")
        self.connected_client = None
        self.device_address = None
        self.current_orientation = None
        self.timer_start = None
        self.orientation_log = []
        self.orientation_labels = {i: f"{i}" for i in range(1, 9)}

        # Layout
        self.create_layout()

    def create_layout(self):
        """Erstellt die GUI."""
        # Verbindungsstatus und Batterielevel
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        self.connection_status = tk.Label(
            self.status_frame, text="Nicht verbunden", bg="red", fg="white", font=("Helvetica", 12)
        )
        self.connection_status.pack(side="left", padx=5)

        # Batterielevel-Anzeige
        self.battery_label = ttk.Label(self.status_frame, text="Batterie: N/A", font=("Helvetica", 12))
        self.battery_label.pack(side="left", padx=5)

        # Ladezustand-Anzeige
        self.power_label = ttk.Label(self.status_frame, text="Ladezustand: N/A", font=("Helvetica", 8))
        self.power_label.pack(side="right", padx=5)

        # Geräteliste
        self.device_list_frame = ttk.LabelFrame(self.root, text="Geräte")
        self.device_list_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        self.device_list = tk.Listbox(self.device_list_frame, height=5)
        self.device_list.pack(side="left", fill="both", expand=True)

        self.scrollbar = tk.Scrollbar(self.device_list_frame, orient="vertical")
        self.scrollbar.pack(side="right", fill="y")
        self.device_list.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.device_list.yview)

        self.controls_frame = ttk.Frame(self.root)
        self.controls_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")

        self.scan_button = ttk.Button(self.controls_frame, text="Scannen", command=self.start_scan_thread)
        self.scan_button.pack(side="left", padx=5)

        self.connect_button = ttk.Button(self.controls_frame, text="Verbinden", command=self.start_connect_thread)
        self.connect_button.pack(side="left", padx=5)

        self.disconnect_button = ttk.Button(self.controls_frame, text="Trennen", command=self.start_disconnect_thread)
        self.disconnect_button.pack(side="left", padx=5)

        # Timer und Orientierung
        self.timer_frame = ttk.LabelFrame(self.root, text="Timer & Orientierung")
        self.timer_frame.grid(row=1, column=1, rowspan=2, padx=5, pady=5, sticky="nsew")

        self.timer_label = ttk.Label(self.timer_frame, text="Timer: 0:00", font=("Helvetica", 16))
        self.timer_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.orientation_label = ttk.Label(self.timer_frame, text="Fläche: Pause", font=("Helvetica", 14))
        self.orientation_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        self.task_entry = ttk.Entry(self.timer_frame, width=30)
        self.task_entry.grid(row=2, column=0, padx=5, pady=5)
        self.task_entry.insert(0, "")

        self.job_entry = ttk.Entry(self.timer_frame, width=30)
        self.job_entry.grid(row=3, column=0, padx=5, pady=5)
        self.job_entry.insert(0, "")

        # Auswertung
        self.log_frame = ttk.LabelFrame(self.root, text="Auswertung")
        self.log_frame.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")

        self.log_text = tk.Text(self.log_frame, height=10)
        self.log_text.pack(fill="both", expand=True)

        # Fußzeile für Geräteinformationen
        self.footer_frame = ttk.LabelFrame(self.root, text="Geräteinformationen")
        self.footer_frame.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        self.footer_label = ttk.Label(self.footer_frame, text="Geräteinformationen werden hier angezeigt.", font=("Helvetica", 10))
        self.footer_label.pack(fill="both", expand=True)


    def log_message(self, message):
        """Zeigt Nachrichten in der Logbox an."""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

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

            # Starte die regelmäßigen Updates
            self.start_battery_update_loop()
            self.start_device_info_update_loop()

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

                # Orientierung-Handler registrieren
                async def orientation_handler(sender, data):
                    self.log_message(f"Orientierung-Benachrichtigung: Sender={sender}, Data={data}")
                    orientation = int(data[0])
                    self.root.after(0, self._update_gui_orientation, orientation)

                await client.start_notify(ORIENTATION_UUID, orientation_handler)
                self.log_message("Orientierungs-Benachrichtigungen erfolgreich registriert.")

                # Batterie-Handler registrieren
                async def battery_handler(sender, data):
                    battery_level = int(data[0])  # Batterielevel ist das erste Byte
                    self.log_message(f"Batterielevel-Benachrichtigung: {battery_level}%")
                    self.root.after(0, lambda: self.battery_label.config(text=f"Batterie: {battery_level}%"))

                await client.start_notify(BATTERY_UUID, battery_handler)
                self.log_message("Batterie-Benachrichtigungen erfolgreich registriert.")

                # Ladezustand-Handler registrieren
                async def power_handler(sender, data):
                    power_status = int(data[0])  # Ladezustand ist das erste Byte
                    status_text = "Wird geladen" if power_status == 2 else "Wird nicht geladen"
                    self.log_message(f"Ladezustand-Benachrichtigung: {status_text}")
                    self.root.after(0, lambda: self.power_label.config(text=f"Ladezustand: {status_text}"))

                await client.start_notify(POWER_UUID, power_handler)
                self.log_message("Ladezustand-Benachrichtigungen erfolgreich registriert.")

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
                    self.save_log(self.current_orientation, elapsed)
                    self.timer_start = None

                self.current_orientation = None
                self.timer_label.config(text="Timer: 0:00")
                self.orientation_label.config(text="Fläche: Pause")
                self.log_message("Timer gestoppt. Fläche: Pause")
            return

        # Starte den Timer bei neuer Orientierung
        if orientation != self.current_orientation:
            if self.timer_start:
                # Speichere die Dauer der vorherigen Orientierung
                elapsed = datetime.now() - self.timer_start
                self.save_log(self.current_orientation, elapsed)

            # Aktualisiere die Orientierung und starte den Timer
            self.current_orientation = orientation
            self.timer_start = datetime.now()
            self.orientation_label.config(text=f"Fläche: {self.orientation_labels[orientation]}")
            self.log_message(f"Orientierung geändert: Fläche {self.orientation_labels[orientation]}")

            # Aktualisiere den Timer in der GUI
            self._update_timer_gui()


    def _update_timer_gui(self):
        """Aktualisiert die Timer-Anzeige in der GUI."""
        if self.timer_start:
            elapsed = datetime.now() - self.timer_start
            self.timer_label.config(text=f"Timer: {str(elapsed).split('.')[0]}")
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
                    self.timer_label.config(text="Timer: 0:00")
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
                self.orientation_label.config(text=f"Fläche: {self.orientation_labels[orientation]}")
                self.log_message(f"Orientierung geändert: {self.orientation_labels[orientation]}")

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
                await self.fetch_device_info()
                await asyncio.sleep(60)  # Alle 60 Sekunden aktualisieren

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
            self.timer_label.config(text="Timer: 0:00")
            self.orientation_label.config(text="Fläche: Pause")

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
                    self.timer_label.config(text="Timer: 0:00")
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
                self.orientation_label.config(text=f"Fläche: {self.orientation_labels[orientation]}")
                self.log_message(f"Orientierung geändert: {self.orientation_labels[orientation]}")

        except Exception as e:
            self.log_message(f"Fehler beim Verarbeiten der Orientierung: {e}")

    def save_log(self, orientation, elapsed):
        """Speichert die Aktivität in der Auswertung."""
        task = self.task_entry.get()
        job = self.job_entry.get()
        self.log_message(f"Orientierung {orientation} - Dauer: {elapsed} - Aufgabe: {task} - Auftrag: {job}")


if __name__ == "__main__":
    root = tk.Tk()
    app = TimeularApp(root)
    root.mainloop()
