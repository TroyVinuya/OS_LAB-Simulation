"""
Disk Scheduling Algorithm Simulator (SSTF & C-SCAN)
- Dark themed UI using customtkinter (fallback to tkinter if missing)
- Scrollable results table with both vertical and horizontal scrollbars
- Animated head movement (gantt-like line on the canvas)
- Aligns input boxes to their labels and fits in 1000x700 window
"""

import tkinter as tk
from tkinter import ttk, messagebox
import random

# Try to import customtkinter for dark theme; if not present, proceed with tkinter widgets
try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
except Exception:
    CTK_AVAILABLE = False

# Create the main window (use CTk if available)
if CTK_AVAILABLE:
    Root = ctk.CTk
    Frame = ctk.CTkFrame
    Button = ctk.CTkButton
    ComboBox = ctk.CTkComboBox
    Label = ctk.CTkLabel
else:
    Root = tk.Tk
    Frame = tk.Frame
    Button = tk.Button
    # Use ttk Combobox for fallback
    class ComboBox(ttk.Combobox):
        def __init__(self, master=None, **kw):
            super().__init__(master=master, **kw)
    def Label(master=None, **kw):
        return tk.Label(master=master, **kw)

# -------------------------
# Core algorithms (SSTF & C-SCAN)
# -------------------------
def sstf(requests_list, head):
    if not requests_list:
        return [], 0
    seq = []
    total = 0
    visited = [False] * len(requests_list)
    cur = head
    # Use a copy so original request order isn't mutated
    reqs = list(requests_list)
    for _ in range(len(reqs)):
        nearest_idx = None
        min_dist = float("inf")
        for i, r in enumerate(reqs):
            if not visited[i]:
                d = abs(cur - r)
                if d < min_dist:
                    min_dist = d
                    nearest_idx = i
        visited[nearest_idx] = True
        total += min_dist
        cur = reqs[nearest_idx]
        seq.append(cur)
    return seq, total

def cscan(requests_list, head, disk_size=200, count_jump=True):
    if not requests_list:
        return [], 0
    seq = []
    total = 0
    curr = head
    left = sorted([r for r in requests_list if r < head])
    right = sorted([r for r in requests_list if r >= head])

    for r in right:
        total += abs(curr - r)
        curr = r
        seq.append(curr)

    # move to end
    if curr != disk_size - 1:
        total += abs((disk_size - 1) - curr)
        curr = disk_size - 1

    # jump to 0: either count or ignore jump cost
    if count_jump:
        total += curr  # from end to 0 (curr is disk_size - 1)
    curr = 0

    for r in left:
        total += abs(curr - r)
        curr = r
        seq.append(curr)

    return seq, total

# -------------------------
# UI / App
# -------------------------
class DiskSchedulerApp:
    def __init__(self, master):
        self.master = master
        master.title("Disk Scheduling Algorithm Simulator (SSTF & C-SCAN)")
        master.geometry("1000x700")
        master.resizable(False, False)

        # State
        self.requests = []
        self.seek_sequence = []
        self.total_seek = 0
        self.animation_index = 0
        self.head_position = 0

        # Build UI
        self.build_controls()
        self.build_request_label()
        self.build_table_area()
        self.build_gantt_area()
        self.build_stats_area()
        self.build_buttons()

    # -------------------------
    # Top Controls
    # -------------------------
    def build_controls(self):
        # Big top control frame
        self.controls_frame = Frame(self.master, width=980, height=110, corner_radius=8 if CTK_AVAILABLE else 0)
        # place size passed at constructor to satisfy customtkinter rules
        self.controls_frame.place(x=10, y=8)

        # Number of Requests
        lbl_num = Label(self.controls_frame, text="Number of Requests:")
        lbl_num.place(x=6, y=8)
        self.combo_num = ComboBox(self.controls_frame, values=[str(x) for x in range(4, 17)], width=90)
        self.combo_num.place(x=150, y=8)
        self.combo_num.set("8")

        # Disk size
        lbl_disk = Label(self.controls_frame, text="Disk Size (cylinders):")
        lbl_disk.place(x=260, y=8)
        self.entry_disk = tk.Entry(self.controls_frame, width=8)
        self.entry_disk.place(x=480, y=18)
        self.entry_disk.insert(0, "200")

        # Initial head
        lbl_head = Label(self.controls_frame, text="Initial Head Position:")
        lbl_head.place(x=495, y=8)
        self.entry_head = tk.Entry(self.controls_frame, width=8)
        self.entry_head.place(x=770, y=18)
        self.entry_head.insert(0, "50")

        # ms per cylinder
        lbl_ms = Label(self.controls_frame, text="ms / cylinder (latency):")
        lbl_ms.place(x=740, y=8)
        self.entry_ms = tk.Entry(self.controls_frame, width=6)
        self.entry_ms.place(x=1100, y=18)
        self.entry_ms.insert(0, "0.5")

        # Algorithm dropdown
        lbl_algo = Label(self.controls_frame, text="Algorithm:")
        lbl_algo.place(x=6, y=48)
        self.combo_algo = ComboBox(self.controls_frame, values=["SSTF", "C-SCAN"], width=120)
        self.combo_algo.place(x=70, y=48)
        self.combo_algo.set("SSTF")

        # C-SCAN jump counted? (checkbox)
        self.count_jump_var = tk.IntVar(value=1)
        chk_text = "Count C-SCAN jump cost"
        # Use dark gray background when customtkinter is active (for contrast)
        self.chk_jump = tk.Checkbutton(
            self.controls_frame,
            text=chk_text,
            variable=self.count_jump_var,
            bg="#2B2B2B" if CTK_AVAILABLE else None,
            fg="white" if CTK_AVAILABLE else "black",
            selectcolor="#1C1C1C" if CTK_AVAILABLE else None,
            activebackground="#2B2B2B" if CTK_AVAILABLE else None
        )
        # place manually (appearance slightly different in fallback)
        self.chk_jump.place(x=280, y=65)

    def build_request_label(self):
        # Disk requests preview label
        self.lbl_reqs = tk.Label(self.master, text="Disk Requests:", anchor="w", bg=self.master.cget("bg") if not CTK_AVAILABLE else None, fg="black" if CTK_AVAILABLE else "black")
        self.lbl_reqs.place(x=12, y=125, width=976)

    # -------------------------
    # Scrollable Table Area (both scrolls)
    # -------------------------
    def build_table_area(self):
        # Outer pool frame (rounded if CTK available)
        self.pool_frame = Frame(self.master, width=975, height=200, corner_radius=8 if CTK_AVAILABLE else 0)
        self.pool_frame.place(x=10, y=150)

        # Create a canvas inside pool_frame to host the scrollable inner frame
        self.table_canvas = tk.Canvas(self.pool_frame, bg="#FFFFFF", highlightthickness=0)
        self.table_canvas.place(x=10, y=10, width=955, height=180)

        # Scrollbars
        self.v_scroll = ttk.Scrollbar(self.pool_frame, orient="vertical", command=self.table_canvas.yview)
        self.h_scroll = ttk.Scrollbar(self.pool_frame, orient="horizontal", command=self.table_canvas.xview)
        # place them so they appear on right and bottom of canvas
        self.v_scroll.place(x=975 - 10, y=10, height=180)  # relative to pool_frame
        self.h_scroll.place(x=10, y=10 + 180, width=955)

        self.table_canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)

        # Inner frame that will contain header and rows
        self.inner_table = tk.Frame(self.table_canvas, bg="#FFFFFF")
        # Put the inner frame in canvas
        self.table_window = self.table_canvas.create_window((0, 0), window=self.inner_table, anchor="nw")

        # Bind resizing events to update scrollregion
        self.inner_table.bind("<Configure>", lambda e: self.table_canvas.configure(scrollregion=self.table_canvas.bbox("all")))
        self.table_canvas.bind("<Configure>", self._table_canvas_configure)

        # Table headers (5 columns)
        headers = ["Move #", "Cylinder", "Seek Dist", "Move Latency (ms)", "Cumulative Seek"]
        self.table_cols = len(headers)
        for c, txt in enumerate(headers):
            lbl = tk.Label(self.inner_table, text=txt, bg="#EAEAEA", font=("Arial", 10, "bold"), borderwidth=1, relief="solid")
            lbl.grid(row=0, column=c, sticky="nsew", padx=0, pady=0)
            self.inner_table.grid_columnconfigure(c, weight=1, minsize=140)  # allow horizontal scroll if needed

        # store row widgets for easy clearing
        self.table_rows = []

    def _table_canvas_configure(self, event):
        # When the canvas is resized, ensure the inner window width is at least canvas width
        canvas_width = event.width
        # set min width so horizontal scrollbar appears when content exceeds
        self.table_canvas.itemconfig(self.table_window, width=max(canvas_width, self.table_canvas.bbox("all")[2] if self.table_canvas.bbox("all") else canvas_width))

    # -------------------------
    # Gantt / Animation area
    # -------------------------
    def build_gantt_area(self):
        self.gantt_frame = Frame(self.master, width=975, height=150, corner_radius=8 if CTK_AVAILABLE else 0)
        self.gantt_frame.place(x=10, y=360)

        self.gantt_canvas = tk.Canvas(self.gantt_frame, bg="#111213" if CTK_AVAILABLE else "#FFFFFF", highlightthickness=0)
        self.gantt_canvas.place(x=10, y=10, width=955, height=130)

        # draw baseline ruler placeholder
        self.gantt_canvas.create_line(5, 65, 950, 65, fill="#444444", width=2)

    # -------------------------
    # Stats area
    # -------------------------
    def build_stats_area(self):
        # Stats left
        self.cpu_frame = Frame(self.master, width=480, height=120, corner_radius=8 if CTK_AVAILABLE else 0)
        self.cpu_frame.place(x=10, y=520)

        # inner white box (visual)
        inner = tk.Frame(self.cpu_frame, bg="#FFFFFF")
        inner.place(x=10, y=10, width=460, height=100)

        tk.Label(inner, text="Total Seek Distance:", bg="#FFFFFF", font=("Arial", 10, "bold")).place(x=6, y=6)
        tk.Label(inner, text="Average Seek:", bg="#FFFFFF", font=("Arial", 10, "bold")).place(x=6, y=36)

        self.total_seek_var = tk.StringVar(value="0")
        self.avg_seek_var = tk.StringVar(value="0")

        tk.Label(inner, textvariable=self.total_seek_var, bg="#FFFFFF").place(x=170, y=6)
        tk.Label(inner, textvariable=self.avg_seek_var, bg="#FFFFFF").place(x=170, y=36)

        # Queue / stats right
        self.queue_frame = Frame(self.master, width=480, height=120, corner_radius=8 if CTK_AVAILABLE else 0)
        self.queue_frame.place(x=500, y=520)

        inner2 = tk.Frame(self.queue_frame, bg="#FFFFFF")
        inner2.place(x=10, y=10, width=460, height=100)

        self.queue_label = tk.Label(inner2, text="Seek Sequence:", bg="#FFFFFF", wraplength=420, justify="left")
        self.queue_label.place(x=6, y=6)

    # -------------------------
    # Buttons area
    # -------------------------
    def build_buttons(self):
        btn_frame = Frame(self.master, width=975, height=50, corner_radius=8 if CTK_AVAILABLE else 0)
        btn_frame.place(x=10, y=650)
        # Use normal tk Buttons where CTkButton may not accept width/height in place
        self.btn_generate = Button(btn_frame, text="Generate Requests", command=self.generate_data, width=160)
        self.btn_generate.place(x=120, y=8)
        self.btn_simulate = Button(btn_frame, text="Simulate", command=self.simulate, state="disabled", width=120)
        self.btn_simulate.place(x=320, y=8)
        self.btn_reset = Button(btn_frame, text="Reset", command=self.reset_all, width=120)
        self.btn_reset.place(x=460, y=8)

    # -------------------------
    # Data generation & filling table
    # -------------------------
    def generate_data(self):
        # clear first
        self.clear_table_rows()
        try:
            n = int(self.combo_num.get())
            disk_size = int(self.entry_disk.get())
            if n <= 0 or disk_size <= 1:
                raise ValueError
        except Exception:
            messagebox.showerror("Input Error", "Enter valid number of requests and disk size.")
            return

        # create requests (unique if possible)
        if n > disk_size:
            # allow duplicates
            reqs = [random.randrange(0, disk_size) for _ in range(n)]
        else:
            reqs = sorted(random.sample(range(0, disk_size), n))

        self.requests = reqs
        self.lbl_reqs.config(text="Disk Requests: " + ", ".join(map(str, self.requests)))
        # enable simulate
        self.btn_simulate.configure(state="normal")

        # adjust header columns minsize to handle more columns if horizontal needed
        # add rows empty (they will be filled after simulation)
        # For now only show request list; table rows will be filled by simulate()
        # But add placeholder rows so scrollbar can be tested
        for r in range(1, max(10, n) + 1):
            for c in range(self.table_cols):
                # empty labels to ensure grid expands
                lbl = tk.Label(self.inner_table, text="", bg="#FFFFFF", borderwidth=1, relief="solid")
                lbl.grid(row=r, column=c, sticky="nsew", padx=0, pady=0)
            # no need to retain placeholders

    def clear_table_rows(self):
        # destroy all widgets in inner_table except header row (row=0)
        for w in self.inner_table.winfo_children():
            info = w.grid_info()
            if info and info.get("row", 0) != 0:
                w.destroy()
        self.table_rows = []

    # -------------------------
    # Simulation -> fills table and starts animation
    # -------------------------
    def simulate(self):
        # clear previous
        self.clear_table_rows()
        if not self.requests:
            messagebox.showinfo("No requests", "Generate requests first.")
            return

        try:
            head = int(self.entry_head.get())
            disk_size = int(self.entry_disk.get())
            ms_per_cyl = float(self.entry_ms.get())
        except Exception:
            messagebox.showerror("Input Error", "Enter valid numeric values for head, disk size, and ms/cylinder.")
            return

        algo = self.combo_algo.get()
        count_jump = bool(self.count_jump_var.get())

        if algo == "SSTF":
            seq, total = sstf(self.requests, head)
        elif algo == "C-SCAN":
            seq, total = cscan(self.requests, head, disk_size=disk_size, count_jump=count_jump)
        else:
            messagebox.showerror("Algorithm", "Unknown algorithm selected.")
            return

        self.seek_sequence = seq
        self.total_seek = total

        # fill table rows (per-move)
        cumulative = 0
        curr = head
        for i, pos in enumerate(seq, start=1):
            dist = abs(curr - pos)
            cumulative += dist
            latency = dist * float(ms_per_cyl)
            # create labels for each column
            lbl_move = tk.Label(self.inner_table, text=str(i), bg="#FFFFFF", borderwidth=1, relief="solid")
            lbl_cyl  = tk.Label(self.inner_table, text=str(pos), bg="#FFFFFF", borderwidth=1, relief="solid")
            lbl_dist = tk.Label(self.inner_table, text=str(dist), bg="#FFFFFF", borderwidth=1, relief="solid")
            lbl_lat  = tk.Label(self.inner_table, text=f"{latency:.2f}", bg="#FFFFFF", borderwidth=1, relief="solid")
            lbl_cum  = tk.Label(self.inner_table, text=str(cumulative), bg="#FFFFFF", borderwidth=1, relief="solid")

            row_index = i
            lbl_move.grid(row=row_index, column=0, sticky="nsew")
            lbl_cyl.grid(row=row_index, column=1, sticky="nsew")
            lbl_dist.grid(row=row_index, column=2, sticky="nsew")
            lbl_lat.grid(row=row_index, column=3, sticky="nsew")
            lbl_cum.grid(row=row_index, column=4, sticky="nsew")

            self.table_rows.append((lbl_move, lbl_cyl, lbl_dist, lbl_lat, lbl_cum))
            curr = pos

        # update stats
        self.total_seek_var.set(str(self.total_seek))
        avg_seek = self.total_seek / len(self.requests) if self.requests else 0
        self.avg_seek_var.set(f"{avg_seek:.2f}")
        self.queue_label.config(text="Seek Sequence: " + " → ".join(map(str, self.seek_sequence)))

        # prepare and run animation
        self.gantt_canvas.delete("all")
        # baseline
        self.gantt_canvas.create_line(5, 65, 950, 65, fill="#444444", width=2)
        self.animation_index = 0
        self.head_position = head

        # compute scale px per cylinder (avoid division by zero)
        if disk_size <= 0:
            disk_size = 200
        canvas_w = self.gantt_canvas.winfo_width()
        if canvas_w < 10:
            canvas_w = 955
        self.scale_px = canvas_w / disk_size

        # draw initial head marker
        self._draw_head_marker(self.head_position)
        # start animation loop
        self.master.after(400, self.animate_seek_step)

    # -------------------------
    # Animation step
    # -------------------------
    def animate_seek_step(self):
        if self.animation_index >= len(self.seek_sequence):
            # final marker, done
            self._draw_head_marker(self.head_position, final=True)
            return

        next_pos = self.seek_sequence[self.animation_index]
        y_mid = self.gantt_canvas.winfo_height() // 2
        curr_x = self.head_position * self.scale_px
        next_x = next_pos * self.scale_px

        # draw line from current to next
        self.gantt_canvas.create_line(curr_x, y_mid, next_x, y_mid, fill="#02C39A", width=3)
        # arrival dot
        self.gantt_canvas.create_oval(next_x - 5, y_mid - 5, next_x + 5, y_mid + 5, fill="#B22222", outline="")

        # update position
        self.head_position = next_pos
        self.animation_index += 1

        # schedule next
        self.master.after(450, self.animate_seek_step)

    def _draw_head_marker(self, head_pos, final=False):
        # draw head marker (blue) with label
        y_mid = self.gantt_canvas.winfo_height() // 2
        x = head_pos * getattr(self, "scale_px", 1)
        r = 7 if final else 5
        self.gantt_canvas.create_oval(x - r, y_mid - r, x + r, y_mid + r, outline="#1E90FF", width=2)
        self.gantt_canvas.create_text(x, y_mid - 16, text=f"H:{head_pos}", fill="#FFFFFF", font=("Arial", 9, "bold"))

    # -------------------------
    # Reset
    # -------------------------
    def reset_all(self):
        self.requests = []
        self.seek_sequence = []
        self.total_seek = 0
        self.animation_index = 0
        self.head_position = 0
        self.lbl_reqs.config(text="Disk Requests:")
        self.clear_table_rows()
        self.gantt_canvas.delete("all")
        self.total_seek_var.set("0")
        self.avg_seek_var.set("0")
        self.queue_label.config(text="Seek Sequence:")
        self.combo_num.set("8")
        self.entry_disk.delete(0, tk.END)
        self.entry_disk.insert(0, "200")
        self.entry_head.delete(0, tk.END)
        self.entry_head.insert(0, "50")
        self.entry_ms.delete(0, tk.END)
        self.entry_ms.insert(0, "0.5")
        self.btn_simulate.configure(state="disabled")

# -------------------------
# Run app
# -------------------------
if __name__ == "__main__":
    root = Root()
    app = DiskSchedulerApp(root)
    root.mainloop()
