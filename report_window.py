from tkinter import Toplevel, ttk, Canvas
from tkinter.font import Font
from collections import defaultdict
from datetime import timedelta


class ReportWindow:
    def __init__(self, root, data, label_settings):
        self.root = root
        self.data = data
        self.filtered_data = data
        self.label_settings = label_settings  # Labels und Farben

    def open(self):
        # Neues Fenster erstellen
        report_window = Toplevel(self.root)
        report_window.title("Zeiteinträge Bericht")
        report_window.geometry("1000x800")

        # Statistik-Übersicht hinzufügen
        self.add_statistics(report_window)

        # Filter hinzufügen
        self.add_filters(report_window)

        # Tabelle hinzufügen
        self.tree = self.add_data_display(report_window)

        # Initiale Daten laden
        self.update_table()
        self.update_statistics()

    def add_statistics(self, window):
        # Frame für Statistiken
        stats_frame = ttk.LabelFrame(window, text="Statistiken")
        stats_frame.pack(fill="x", padx=0, pady=0)

        # Canvas für Labels und Stunden
        self.stats_canvas = Canvas(stats_frame, height=150)
        self.stats_canvas.pack(fill="x", padx=10, pady=5)

        # Textuelle Statistiken
        self.total_time_label = ttk.Label(stats_frame, text="Gesamtdauer: 0 Stunden")
        self.total_time_label.pack(side="left", padx=10, pady=5)

        self.total_entries_label = ttk.Label(stats_frame, text="Anzahl der Einträge: 0")
        self.total_entries_label.pack(side="left", padx=10, pady=5)

        # Button zum Zurücksetzen
        reset_button = ttk.Button(stats_frame, text="Filter zurücksetzen", command=self.reset_filters)
        reset_button.pack(side="right", padx=10, pady=5)

    def add_filters(self, window):
        # Frame für Filter
        filter_frame = ttk.LabelFrame(window, text="Filter")
        filter_frame.pack(fill="x", padx=10, pady=10)

        # Datumsbereich
        ttk.Label(filter_frame, text="Startdatum (YYYY-MM-DD):").grid(row=0, column=0, padx=5, pady=5)
        self.start_date_entry = ttk.Entry(filter_frame, width=15)
        self.start_date_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(filter_frame, text="Enddatum (YYYY-MM-DD):").grid(row=0, column=2, padx=5, pady=5)
        self.end_date_entry = ttk.Entry(filter_frame, width=15)
        self.end_date_entry.grid(row=0, column=3, padx=5, pady=5)

        # Label-Filter
        unique_labels = [label_data["label"] for label_data in self.label_settings.values()]
        ttk.Label(filter_frame, text="Label:").grid(row=1, column=0, padx=5, pady=5)
        self.label_filter = ttk.Combobox(filter_frame, values=unique_labels, state="readonly")
        self.label_filter.grid(row=1, column=1, padx=5, pady=5)

        # Auftrag-Filter
        ttk.Label(filter_frame, text="Auftrag:").grid(row=1, column=2, padx=5, pady=5)
        self.job_filter = ttk.Entry(filter_frame, width=20)
        self.job_filter.grid(row=1, column=3, padx=5, pady=5)

        # Freitextsuche
        ttk.Label(filter_frame, text="Freitext:").grid(row=1, column=4, padx=5, pady=5)
        self.search_filter = ttk.Entry(filter_frame, width=20)
        self.search_filter.grid(row=1, column=5, padx=5, pady=5)

        # Filter anwenden Button
        apply_button = ttk.Button(filter_frame, text="Filter anwenden", command=self.apply_filters)
        apply_button.grid(row=1, column=6, padx=10, pady=5)



    def add_data_display(self, window):
        # Frame für Tabelle
        table_frame = ttk.LabelFrame(window, text="Zeiteinträge")
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Tabellenansicht (Treeview)
        columns = ["Datum", "Label", "Dauer", "Aufgabe", "Auftrag"]
        tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150)
        tree.pack(fill="both", expand=True)
        return tree

    def update_table(self):
        """Aktualisiert die Tabelle basierend auf den gefilterten Daten."""
        # Tabelle leeren
        for row in self.tree.get_children():
            self.tree.delete(row)

        # Neue Daten einfügen
        for entry in self.filtered_data:
            label = entry["label"]
            label_color = "#FFFFFF"  # Standardfarbe
            for key, value in self.label_settings.items():
                if value["label"] == label:
                    label_color = value["color"]
                    break

            # Zeile hinzufügen
            item_id = self.tree.insert(
                "", "end",
                values=(entry["date"], entry["label"], entry["duration"], entry["task"], entry["job"])
            )

            # Textfarbe für die "Label"-Spalte setzen
            self.tree.tag_configure(f"label_{item_id}", background=label_color, foreground="black")
            self.tree.item(item_id, tags=(f"label_{item_id}",))




    def update_statistics(self):
        """Aktualisiert die Statistik-Anzeige mit den richtigen Farben aus der Config."""
        label_hours = defaultdict(float)
        total_time = 0.0

        for entry in self.filtered_data:
            label = entry.get("label", "Unbekannt")
            duration_str = entry.get("duration", "")

            try:
                # Zeitformat prüfen und in Stunden umrechnen
                if ":" in duration_str:
                    time_parts = list(map(int, duration_str.split(":")))
                    duration_seconds = timedelta(
                        hours=time_parts[0], minutes=time_parts[1], seconds=time_parts[2]
                    ).total_seconds()
                    hours = duration_seconds / 3600
                else:
                    hours = float(duration_str.replace("h", "").strip())

                label_hours[label] += hours
                total_time += hours
            except (ValueError, AttributeError):
                continue

        # Gesamtdauer und Anzahl der Einträge
        self.total_time_label.config(text=f"Gesamtdauer: {total_time:.2f} Stunden")
        self.total_entries_label.config(text=f"Anzahl der Einträge: {len(self.filtered_data)}")

        # Labels und Stunden grafisch anzeigen
        self.stats_canvas.delete("all")
        card_width = 120
        card_height = 70
        padding = 10
        max_per_row = 6
        x, y = 10, 10

        for idx, (label, hours) in enumerate(label_hours.items()):
            # Hintergrundfarbe aus den Settings (label_settings)
            background_color = None
            for key, value in self.label_settings.items():
                if value["label"] == label:
                    background_color = value["color"]
                    break
            background_color = background_color or "#D1FFF7"  # Fallback-Farbe

            # Rechteck für die Box
            self.stats_canvas.create_rectangle(
                x, y, x + card_width, y + card_height, fill=background_color, outline="#ccc", width=2
            )
            # Labelname
            self.stats_canvas.create_text(
                x + 10, y + 15, text=label, font=("Helvetica", 12, "bold"), anchor="nw", fill="#000"
            )
            # Stunden
            self.stats_canvas.create_text(
                x + 10, y + 40, text=f"{hours:.2f} Stunden", font=("Helvetica", 10), anchor="nw", fill="#000"
            )

            x += card_width + padding
            if (idx + 1) % max_per_row == 0:
                x = 10
                y += card_height + padding




    def apply_filters(self):
        start_date = self.start_date_entry.get().strip()
        end_date = self.end_date_entry.get().strip()
        selected_label = self.label_filter.get().strip()
        job_filter = self.job_filter.get().strip()
        search_filter = self.search_filter.get().strip().lower()

        self.filtered_data = [
            entry for entry in self.data
            if (not start_date or entry["date"] >= start_date)
            and (not end_date or entry["date"] <= end_date)
            and (not selected_label or entry["label"] == selected_label)
            and (not job_filter or job_filter in entry["job"])
            and (not search_filter or search_filter in entry["task"].lower())
        ]

        self.update_table()
        self.update_statistics()


    def reset_filters(self):
        self.start_date_entry.delete(0, "end")
        self.end_date_entry.delete(0, "end")
        self.label_filter.set("")
        self.job_filter.delete(0, "end")
        self.search_filter.delete(0, "end")

        self.filtered_data = self.data
        self.update_table()
        self.update_statistics()

