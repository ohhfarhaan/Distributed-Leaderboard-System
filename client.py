import socket
import threading
import json
import tkinter as tk
from tkinter import font as tkfont
import ssl

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 9999

# ─── Palette ──────────────────────────────────────────────────────────────────
BG       = "#0d0d0d"
BG_CARD  = "#161616"
BG_INPUT = "#1e1e1e"
FG       = "#ffffff"
FG_DIM   = "#555555"
FG_MID   = "#999999"
BORDER   = "#2a2a2a"
ACCENT   = "#ffffff"


class LeaderboardApp:
    def __init__(self) -> None:
        self.sock: socket.socket | None = None
        self.connected = False
        self._buf = ""
        self._reconnect_after: str | None = None

        self._build_window()
        self._build_ui()
        self._connect()
        self.root.mainloop()

    # ─── Window ───────────────────────────────────────────────────────────────

    def _build_window(self) -> None:
        self.root = tk.Tk()
        self.root.title("Leaderboard")
        self.root.geometry("460x680")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)
        # Centre on screen
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 460) // 2
        y = (self.root.winfo_screenheight() - 680) // 2
        self.root.geometry(f"460x680+{x}+{y}")

    # ─── UI layout ────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        pad = 32

        # ── Header ──────────────────────────────────────────────────────────
        hdr = tk.Frame(self.root, bg=BG)
        hdr.pack(fill="x", padx=pad, pady=(32, 0))

        tk.Label(
            hdr, text="LEADERBOARD",
            font=("Helvetica", 20, "bold"), bg=BG, fg=FG
        ).pack(anchor="w")
        tk.Label(
            hdr, text="Live · updates automatically",
            font=("Helvetica", 9), bg=BG, fg=FG_DIM
        ).pack(anchor="w", pady=(2, 0))

        self._sep(pad)

        # ── Submit form ──────────────────────────────────────────────────────
        form = tk.Frame(self.root, bg=BG)
        form.pack(fill="x", padx=pad)

        tk.Label(
            form, text="SUBMIT SCORE",
            font=("Helvetica", 8, "bold"), bg=BG, fg=FG_DIM
        ).pack(anchor="w", pady=(0, 10))

        self.team_var  = tk.StringVar()
        self.score_var = tk.StringVar()

        self._field(form, "Team name", self.team_var)
        self._field(form, "Score",     self.score_var)

        btn_row = tk.Frame(form, bg=BG)
        btn_row.pack(fill="x", pady=(6, 0))

        self.status_var = tk.StringVar(value="")
        tk.Label(
            btn_row, textvariable=self.status_var,
            font=("Helvetica", 9), bg=BG, fg=FG_MID, anchor="w"
        ).pack(side="left", fill="x", expand=True)

        self.submit_btn = tk.Button(
            btn_row, text="SUBMIT",
            font=("Helvetica", 9, "bold"),
            bg=FG, fg=BG, bd=0, padx=18, pady=7,
            cursor="hand2", relief="flat",
            activebackground="#cccccc", activeforeground=BG,
            command=self._submit,
        )
        self.submit_btn.pack(side="right")

        self._sep(pad)

        # ── Rankings ────────────────────────────────────────────────────────
        rank_frame = tk.Frame(self.root, bg=BG)
        rank_frame.pack(fill="both", expand=True, padx=pad, pady=(0, 4))

        col_hdr = tk.Frame(rank_frame, bg=BG)
        col_hdr.pack(fill="x", pady=(0, 6))
        tk.Label(col_hdr, text="#",     font=("Helvetica", 8, "bold"), width=3,
                 bg=BG, fg=FG_DIM, anchor="w").pack(side="left")
        tk.Label(col_hdr, text="TEAM",  font=("Helvetica", 8, "bold"),
                 bg=BG, fg=FG_DIM, anchor="w").pack(side="left", fill="x", expand=True)
        tk.Label(col_hdr, text="SCORE", font=("Helvetica", 8, "bold"),
                 bg=BG, fg=FG_DIM, anchor="e").pack(side="right")

        # Scrollable canvas for entries
        canvas_frame = tk.Frame(rank_frame, bg=BG)
        canvas_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(
            canvas_frame, bg=BG, bd=0, highlightthickness=0
        )
        self.scrollbar = tk.Scrollbar(
            canvas_frame, orient="vertical", command=self.canvas.yview,
            bg=BG, troughcolor=BG_CARD, bd=0, highlightthickness=0,
            width=4
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.lb_inner = tk.Frame(self.canvas, bg=BG)
        self._canvas_win = self.canvas.create_window(
            (0, 0), window=self.lb_inner, anchor="nw"
        )
        self.lb_inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Mouse-wheel scrolling
        self.canvas.bind_all("<MouseWheel>",     self._on_mousewheel)
        self.canvas.bind_all("<Button-4>",       self._on_mousewheel)
        self.canvas.bind_all("<Button-5>",       self._on_mousewheel)

        # ── Footer ───────────────────────────────────────────────────────────
        self._sep(pad)
        self.conn_var = tk.StringVar(value="Connecting…")
        tk.Label(
            self.root, textvariable=self.conn_var,
            font=("Helvetica", 8), bg=BG, fg=FG_DIM
        ).pack(side="bottom", pady=(0, 14))

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _sep(self, pad: int) -> None:
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x", padx=pad, pady=18)

    def _field(self, parent: tk.Frame, placeholder: str, var: tk.StringVar) -> None:
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=(0, 8))

        entry = tk.Entry(
            row, textvariable=var,
            font=("Helvetica", 11), bg=BG_INPUT, fg=FG,
            insertbackground=FG, bd=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=FG,
        )
        entry.pack(fill="x", ipady=9, ipadx=10)

        # Placeholder behaviour
        self._add_placeholder(entry, var, placeholder)
        if placeholder == "Score":
            entry.bind("<Return>", lambda _e: self._submit())

    @staticmethod
    def _add_placeholder(entry: tk.Entry, var: tk.StringVar, text: str) -> None:
        def on_focus_in(_e):
            if var.get() == text:
                var.set("")
                entry.configure(fg=FG)

        def on_focus_out(_e):
            if not var.get():
                var.set(text)
                entry.configure(fg="#444444")

        var.set(text)
        entry.configure(fg="#444444")
        entry.bind("<FocusIn>",  on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)

    def _on_inner_configure(self, _e=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event) -> None:
        self.canvas.itemconfig(self._canvas_win, width=event.width)

    def _on_mousewheel(self, event) -> None:
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ─── Networking ───────────────────────────────────────────────────────────

     # ─── Networking ───────────────────────────────────────────────────────────

    def _connect(self) -> None:
        if self._reconnect_after:
            self.root.after_cancel(self._reconnect_after)
            self._reconnect_after = None

        try:
            # SSL context (allow self-signed certificate)
            context = ssl._create_unverified_context()

            # create TCP socket
            raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # wrap socket with SSL
            self.sock = context.wrap_socket(raw_sock)

            # connect to server
            self.sock.connect((SERVER_HOST, SERVER_PORT))

            self.connected = True
            self._buf = ""
            self.conn_var.set(f"Connected  ·  {SERVER_HOST}:{SERVER_PORT}")

            threading.Thread(target=self._listen, daemon=True).start()

        except Exception as e:
            self.connected = False
            self.conn_var.set("Connection failed — retrying…")
            self._reconnect_after = self.root.after(4000, self._connect)
            
        

    def _listen(self) -> None:
        try:
            while self.connected:
                chunk = self.sock.recv(4096).decode()
                if not chunk:
                    break
                self._buf += chunk
                while "\n" in self._buf:
                    line, self._buf = self._buf.split("\n", 1)
                    line = line.strip()
                    if line:
                        try:
                            self.root.after(0, self._handle_message, json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except Exception:
            pass
        self.connected = False
        self.root.after(0, lambda: self.conn_var.set("Disconnected — reconnecting…"))
        self._reconnect_after = self.root.after(4000, self._connect)

    def _send(self, payload: dict) -> bool:
        if not self.connected or not self.sock:
            return False
        try:
            self.sock.sendall((json.dumps(payload) + "\n").encode())
            return True
        except Exception:
            return False

    # ─── Message handling ─────────────────────────────────────────────────────

    def _handle_message(self, data: dict) -> None:
        t = data.get("type")
        if t == "leaderboard":
            self._render_leaderboard(data.get("data", []))
        elif t == "status":
            self._flash_status(data.get("message", ""))

    def _render_leaderboard(self, entries: list[dict]) -> None:
        for w in self.lb_inner.winfo_children():
            w.destroy()

        if not entries:
            tk.Label(
                self.lb_inner, text="No scores yet.",
                font=("Helvetica", 10), bg=BG, fg=FG_DIM
            ).pack(pady=24)
            return

        for i, entry in enumerate(entries):
            is_top3 = i < 3
            row_bg = BG_CARD if i % 2 == 0 else BG

            row = tk.Frame(self.lb_inner, bg=row_bg)
            row.pack(fill="x", pady=1)

            # Rank badge colours: 1st bright, 2nd/3rd mid, rest dim
            rank_fg = FG if is_top3 else FG_DIM
            rank_font = ("Helvetica", 10, "bold") if is_top3 else ("Helvetica", 10)

            tk.Label(
                row, text=str(i + 1),
                font=rank_font, bg=row_bg, fg=rank_fg,
                width=3, anchor="w"
            ).pack(side="left", padx=(10, 0), pady=8)

            tk.Label(
                row, text=entry["team"],
                font=("Helvetica", 10), bg=row_bg, fg=FG, anchor="w"
            ).pack(side="left", fill="x", expand=True, pady=8)

            tk.Label(
                row, text=f"{entry['score']:,}",
                font=("Helvetica", 10, "bold"), bg=row_bg, fg=FG, anchor="e"
            ).pack(side="right", padx=(0, 12), pady=8)

        self.canvas.yview_moveto(0)

    def _flash_status(self, msg: str, duration_ms: int = 4000) -> None:
        self.status_var.set(msg)
        self.root.after(duration_ms, lambda: self.status_var.set(""))

    # ─── Submit ───────────────────────────────────────────────────────────────

    def _submit(self) -> None:
        PLACEHOLDER_TEAM  = "Team name"
        PLACEHOLDER_SCORE = "Score"

        team  = self.team_var.get().strip()
        score = self.score_var.get().strip()

        # Ignore placeholder text
        if team  == PLACEHOLDER_TEAM:  team  = ""
        if score == PLACEHOLDER_SCORE: score = ""

        if not team:
            self._flash_status("Enter a team name.")
            return
        if not score:
            self._flash_status("Enter a score.")
            return
        try:
            score_int = int(score)
        except ValueError:
            self._flash_status("Score must be a whole number.")
            return

        if not self.connected:
            self._flash_status("Not connected to server.")
            return

        ok = self._send({"action": "submit", "team": team, "score": score_int})
        if ok:
            # Clear fields (restore placeholders via focus-out simulation)
            self.team_var.set("Team name")
            self.score_var.set("Score")
            for w in self.root.winfo_children():
                w.focus_set()
                break
        else:
            self._flash_status("Failed to send. Reconnecting…")


if __name__ == "__main__":
    LeaderboardApp()
