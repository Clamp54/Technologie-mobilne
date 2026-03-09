import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib

matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class BaseStationSim:
    def __init__(self, root):
        self.root = root
        self.root.title("Stacja Bazowa - Zadanie 2")

        self.params = {
            "Liczba kanałów": 10,
            "Długość kolejki": 10,
            "Lambda": 1.0,
            "Średnia (N)": 20,
            "Odchylenie (σ)": 5,
            "Min": 10,
            "Maks": 30,
            "Czas": 30
        }

        self.running = False
        self.current_time = 0
        self.chan_status = []
        self.queue = []
        self.history = {"Q": [], "W": [], "Ro": [], "T": []}
        self.served_count = 0

        self.setup_ui()

    def setup_ui(self):
        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = tk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="ns", padx=5)

        param_lb = tk.LabelFrame(left_frame, text="Parametry")
        param_lb.pack(fill="x")

        self.entries = {}
        for i, (key, val) in enumerate(self.params.items()):
            tk.Label(param_lb, text=key).grid(row=i, column=0, sticky="w")
            ent = tk.Entry(param_lb, width=8)
            ent.insert(0, str(val))
            ent.grid(row=i, column=1)
            self.entries[key] = ent

        cols = ("Pois", "Gaus", "Klienci", "Start", "Czas_Obs")
        self.tree = ttk.Treeview(left_frame, columns=cols, show='headings', height=12)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=55, anchor="center")
        self.tree.pack(pady=10)

        mid_frame = tk.Frame(main_frame)
        mid_frame.grid(row=0, column=1, padx=20, sticky="n")

        tk.Label(mid_frame, text="Kanały", font=("Arial", 12, "bold")).pack()
        self.chan_frame = tk.Frame(mid_frame)
        self.chan_frame.pack()
        self.chan_labels = []
        for i in range(10):
            lbl = tk.Label(self.chan_frame, text="0", bg="red", fg="white", width=6, height=2, relief="sunken")
            lbl.grid(row=i // 2, column=i % 2, padx=2, pady=2)
            self.chan_labels.append(lbl)

        self.progress = ttk.Progressbar(mid_frame, length=150)
        self.progress.pack(pady=15)

        self.stats_lbl = tk.Label(mid_frame, text="Kolejka: 0 / 10\nObsłużone: 0\nCzas: 0/30", justify="left")
        self.stats_lbl.pack()

        tk.Button(mid_frame, text="START", command=self.start_sim, bg="lightgrey", width=10).pack(pady=10)

        right_frame = tk.Frame(main_frame)
        right_frame.grid(row=0, column=2)

        self.fig, (self.ax_q, self.ax_w, self.ax_ro) = plt.subplots(3, 1, figsize=(4, 6))
        self.fig.tight_layout()
        self.canvas = FigureCanvasTkAgg(self.fig, master=right_frame)
        self.canvas.get_tk_widget().pack()

    def start_sim(self):
        self.params = {k: float(v.get()) for k, v in self.entries.items()}
        self.chan_status = [0] * int(self.params["Liczba kanałów"])
        self.queue = []
        self.current_time = 0
        self.served_count = 0
        self.history = {"Q": [], "W": [], "Ro": [], "T": []}

        for i in self.tree.get_children():
            self.tree.delete(i)

        self.running = True
        self.run_step()

    def run_step(self):
        if not self.running or self.current_time >= self.params["Czas"]:
            return

        self.current_time += 1
        num_arrivals = np.random.poisson(self.params["Lambda"])

        for _ in range(num_arrivals):
            duration = np.random.normal(self.params["Średnia (N)"], self.params["Odchylenie (σ)"])
            duration = int(max(self.params["Min"], min(self.params["Maks"], duration)))

            assigned = False
            for i in range(len(self.chan_status)):
                if self.chan_status[i] <= 0:
                    self.chan_status[i] = duration
                    self.served_count += 1
                    assigned = True
                    break

            if not assigned and len(self.queue) < self.params["Długość kolejki"]:
                self.queue.append(duration)

            total_clients = sum(1 for x in self.chan_status if x > 0) + len(self.queue)
            self.tree.insert("", "end", values=(num_arrivals, duration, total_clients, self.current_time, duration))
            self.tree.yview_moveto(1)

        for i in range(len(self.chan_status)):
            if self.chan_status[i] > 0:
                self.chan_status[i] -= 1
            elif self.queue:
                self.chan_status[i] = self.queue.pop(0)
                self.served_count += 1

        ro = sum(1 for x in self.chan_status if x > 0) / self.params["Liczba kanałów"]
        self.history["T"].append(self.current_time)
        self.history["Q"].append(len(self.queue))
        self.history["Ro"].append(ro)
        self.history["W"].append(sum(self.queue) / max(1, len(self.queue)))

        self.update_visuals()
        self.root.after(400, self.run_step)

    def update_visuals(self):
        for i, val in enumerate(self.chan_status):
            if i < len(self.chan_labels):
                self.chan_labels[i].config(text=str(val), bg="green" if val > 0 else "red")

        self.progress["value"] = (self.current_time / self.params["Czas"]) * 100
        self.stats_lbl.config(text=f"Kolejka: {len(self.queue)} / {int(self.params['Długość kolejki'])}\n"
                                   f"Obsłużone: {self.served_count}\n"
                                   f"Czas: {self.current_time}/{int(self.params['Czas'])}")

        self.ax_q.clear();
        self.ax_q.plot(self.history["T"], self.history["Q"], 'r');
        self.ax_q.set_title("Q")
        self.ax_w.clear();
        self.ax_w.plot(self.history["T"], self.history["W"], 'b');
        self.ax_w.set_title("W")
        self.ax_ro.clear();
        self.ax_ro.plot(self.history["T"], self.history["Ro"], 'g');
        self.ax_ro.set_title("Ro")
        self.canvas.draw()


if __name__ == "__main__":
    root = tk.Tk()
    app = BaseStationSim(root)
    root.mainloop()