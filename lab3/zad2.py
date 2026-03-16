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
        self.root.title("Stacja Bazowa")

        # Domyślne parametry symulacji
        self.params = {
            "Liczba kanałów": 10,
            "Długość kolejki": 10,
            "Lambda": 3.0,
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
        self.history = {"Q": [], "W": [], "Ro": [], "T": [], "rho": []}

        # Zmienne do liczenia średnich wyników
        self.served_count = 0
        self.sum_q = 0
        self.total_w = 0
        self.w_count = 0

        self.lambda_list = []
        self.mu_list = []

        self.setup_ui()

    def setup_ui(self):
        # Budowa głównego okna aplikacji
        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = tk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="ns", padx=5)

        param_lb = tk.LabelFrame(left_frame, text="Parametry")
        param_lb.pack(fill="x")

        # Pola do wprowadzania parametrów
        self.entries = {}
        for i, (key, val) in enumerate(self.params.items()):
            tk.Label(param_lb, text=key).grid(row=i, column=0, sticky="w")
            ent = tk.Entry(param_lb, width=8)
            ent.insert(0, str(val))
            ent.grid(row=i, column=1)
            self.entries[key] = ent

        # Tabela wyświetlająca nowe zgłoszenia
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

        # Miejsce na kafelki reprezentujące kanały
        self.chan_labels = []

        self.progress = ttk.Progressbar(mid_frame, length=150)
        self.progress.pack(pady=15)

        self.stats_lbl = tk.Label(mid_frame, text="ρ: 0.00\nQ: 0.0\nW: 0.0\nObsłużone: 0\nCzas: 0/30", justify="left")
        self.stats_lbl.pack()

        tk.Button(mid_frame, text="START", command=self.start_sim, bg="lightgrey", width=10).pack(pady=10)

        right_frame = tk.Frame(main_frame)
        right_frame.grid(row=0, column=2)

        # Inicjalizacja obszaru wykresów
        self.fig, (self.ax_rho, self.ax_q, self.ax_w) = plt.subplots(3, 1, figsize=(4, 6))
        self.fig.tight_layout()
        self.canvas = FigureCanvasTkAgg(self.fig, master=right_frame)
        self.canvas.get_tk_widget().pack()

    def generate_lists(self):
        # Generowanie odstępów czasu i długości rozmów na całą symulację
        self.lambda_list = []
        self.mu_list = []
        total_time = 0

        while total_time <= self.params["Czas"] + 10:
            l_i = np.random.exponential(1.0 / self.params["Lambda"])
            mu = np.random.normal(self.params["Średnia (N)"], self.params["Odchylenie (σ)"])
            mu = int(max(self.params["Min"], min(self.params["Maks"], mu)))

            self.lambda_list.append(l_i)
            self.mu_list.append(mu)
            total_time += l_i

    def start_sim(self):
        # Pobranie parametrów z interfejsu
        self.params = {k: float(v.get()) for k, v in self.entries.items()}
        self.chan_status = [0] * int(self.params["Liczba kanałów"])

        # Rysowanie odpowiedniej liczby kanałów
        for lbl in self.chan_labels:
            lbl.grid_forget()
        self.chan_labels = []
        for i in range(int(self.params["Liczba kanałów"])):
            lbl = tk.Label(self.chan_frame, text="0", bg="green", fg="white", width=6, height=2, relief="sunken")
            lbl.grid(row=i // 2, column=i % 2, padx=2, pady=2)
            self.chan_labels.append(lbl)

        # Resetowanie zmiennych przed nową symulacją
        self.queue = []
        self.current_time = 0
        self.served_count = 0
        self.sum_q = 0
        self.total_w = 0
        self.w_count = 0
        self.history = {"Q": [], "W": [], "Ro": [], "T": [], "rho": []}

        for i in self.tree.get_children():
            self.tree.delete(i)

        self.generate_lists()
        self.running = True
        self.run_step()

    def run_step(self):
        # Sprawdzenie, czy symulacja dobiegła końca
        if not self.running or self.current_time >= self.params["Czas"]:
            self.running = False
            self.save_report()
            return

        self.current_time += 1

        # Sumowanie ułamków czasu, aby pobrać zgłoszenia z bieżącej sekundy
        sum_l = 0
        k = 0
        while k < len(self.lambda_list):
            if sum_l + self.lambda_list[k] <= 1.0:
                sum_l += self.lambda_list[k]
                k += 1
            else:
                self.lambda_list[k] -= (1.0 - sum_l)
                break

        new_lambdas = self.lambda_list[:k]
        new_mus = self.mu_list[:k]

        # Usunięcie pobranych zgłoszeń z głównej listy
        self.lambda_list = self.lambda_list[k:]
        self.mu_list = self.mu_list[k:]

        # Przydzielanie nowych zgłoszeń do wolnych kanałów lub kolejki
        for i in range(k):
            assigned = False
            for ch in range(len(self.chan_status)):
                if self.chan_status[ch] == 0:
                    self.chan_status[ch] = new_mus[i]
                    assigned = True
                    break

            if not assigned and len(self.queue) < self.params["Długość kolejki"]:
                self.queue.append({'mu': new_mus[i], 'wait': 0})

            # Dodanie wpisu do tabeli w interfejsie
            if assigned or (not assigned and len(self.queue) <= self.params["Długość kolejki"]):
                total_clients = sum(1 for x in self.chan_status if x > 0) + len(self.queue)
                self.tree.insert("", "end",
                                 values=(f"{new_lambdas[i]:.2f}", new_mus[i], total_clients, self.current_time,
                                         new_mus[i]))
                self.tree.yview_moveto(1)

        # Zmniejszanie czasu obsługi i dobieranie kolejnych zgłoszeń z kolejki
        for i in range(len(self.chan_status)):
            if self.chan_status[i] > 0:
                self.chan_status[i] -= 1
                if self.chan_status[i] == 0:
                    self.served_count += 1
                    if self.queue:
                        next_client = self.queue.pop(0)
                        self.chan_status[i] = next_client['mu']
                        self.total_w += next_client['wait']
                        self.w_count += 1

        # Zwiększanie czasu oczekiwania dla każdego w kolejce
        for q in self.queue:
            q['wait'] += 1

        # Obliczanie średnich statystyk do wykresów
        occupied_channels = sum(1 for status in self.chan_status if status > 0)
        rho = occupied_channels / self.params["Liczba kanałów"]

        self.sum_q += len(self.queue)
        q_avg = self.sum_q / self.current_time
        w_avg = (self.total_w / self.w_count) if self.w_count > 0 else 0

        self.history["T"].append(self.current_time)
        self.history["Q"].append(q_avg)
        self.history["Ro"].append(rho)
        self.history["rho"].append(rho)
        self.history["W"].append(w_avg)

        self.update_visuals()

        # Wywołanie kolejnego kroku symulacji
        self.root.after(400, self.run_step)

    def update_visuals(self):
        # Odświeżanie kolorów i wartości na kafelkach kanałów
        for i, val in enumerate(self.chan_status):
            if i < len(self.chan_labels):
                self.chan_labels[i].config(text=str(val), bg="red" if val > 0 else "green")

        self.progress["value"] = (self.current_time / self.params["Czas"]) * 100

        rho_current = self.history["rho"][-1]
        q_current = self.history["Q"][-1]
        w_current = self.history["W"][-1]

        # Aktualizacja tekstu ze statystykami
        self.stats_lbl.config(
            text=f"ρ (chwilowe): {rho_current:.2f}\nQ (średnie): {q_current:.2f}\nW (średnie): {w_current:.2f}\n"
                 f"Obsłużone: {self.served_count}\n"
                 f"Czas: {self.current_time}/{int(self.params['Czas'])}")

        # Rysowanie wykresów
        self.ax_rho.clear()
        self.ax_rho.plot(self.history["T"], self.history["rho"], 'g', linewidth=2)
        self.ax_rho.set_title("ρ - Intensywność ruchu")
        self.ax_rho.set_ylim([-0.05, 1.1])
        self.ax_rho.grid(True, alpha=0.3)

        self.ax_q.clear()
        self.ax_q.plot(self.history["T"], self.history["Q"], 'r', linewidth=2)
        self.ax_q.set_title("Q - Średnia długość kolejki")
        self.ax_q.grid(True, alpha=0.3)

        self.ax_w.clear()
        self.ax_w.plot(self.history["T"], self.history["W"], 'b', linewidth=2)
        self.ax_w.set_title("W - Średni czas oczekiwania")
        self.ax_w.grid(True, alpha=0.3)

        self.canvas.draw()

    def save_report(self):
        # Zapisanie wyników symulacji do pliku tekstowego
        filename = "wyniki.txt"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for key, value in self.params.items():
                    f.write(f"{key}: {value}\n")
                f.write("-" * 50 + "\n")
                f.write("Czas\tp\tQ\tW\n")
                for i in range(len(self.history["T"])):
                    f.write(f"{self.history['T'][i]}\t{self.history['rho'][i]:.4f}\t"
                            f"{self.history['Q'][i]:.2f}\t{self.history['W'][i]:.2f}\n")
            print(f"Raport zapisany do: {filename}")
        except Exception as e:
            print(f"Błąd zapisu: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = BaseStationSim(root)
    root.mainloop()