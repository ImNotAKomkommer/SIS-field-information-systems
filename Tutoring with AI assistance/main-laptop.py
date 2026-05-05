import sqlite3
import os
import hashlib
import webbrowser
from datetime import datetime
import tkinter as tk
from tkinter import messagebox

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


DB_NAME = "tutor_app.db"

BG = "#111827"
SIDEBAR = "#0b1220"
CARD = "#1f2937"
CARD_2 = "#273449"
INPUT = "#0b1220"
TEXT = "#f9fafb"
MUTED = "#9ca3af"
ACCENT = "#38bdf8"
ACCENT_DARK = "#0284c7"
GREEN = "#22c55e"
RED = "#ef4444"
YELLOW = "#facc15"
BORDER = "#374151"

FONT_TITLE = ("Segoe UI", 19, "bold")
FONT_H2 = ("Segoe UI", 13, "bold")
FONT_BODY = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)


def get_connection():
    return sqlite3.connect(DB_NAME)


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        english_level TEXT NOT NULL,
        learning_goal TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        tutor_name TEXT NOT NULL,
        lesson_topic TEXT NOT NULL,
        preferred_time TEXT NOT NULL,
        message TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS progress (
        user_id INTEGER PRIMARY KEY,
        lecture_unlocked INTEGER DEFAULT 0,
        lecture_completed INTEGER DEFAULT 0,
        quiz_completed INTEGER DEFAULT 0,
        quiz_score INTEGER DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()


def create_user(full_name, email, password, english_level, learning_goal):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
        INSERT INTO users(full_name, email, password_hash, english_level, learning_goal, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            full_name,
            email,
            hash_password(password),
            english_level,
            learning_goal,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        user_id = cur.lastrowid
        cur.execute("INSERT INTO progress(user_id) VALUES (?)", (user_id,))
        conn.commit()
        return True, "Account created successfully."
    except sqlite3.IntegrityError:
        return False, "This email is already registered."
    finally:
        conn.close()


def login_user(email, password):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT id, full_name, email, english_level, learning_goal
    FROM users
    WHERE email=? AND password_hash=?
    """, (email, hash_password(password)))
    user = cur.fetchone()
    conn.close()
    return user


def get_user(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT id, full_name, email, english_level, learning_goal, created_at
    FROM users
    WHERE id=?
    """, (user_id,))
    user = cur.fetchone()
    conn.close()
    return user


def get_progress(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT lecture_unlocked, lecture_completed, quiz_completed, quiz_score
    FROM progress
    WHERE user_id=?
    """, (user_id,))
    progress = cur.fetchone()
    conn.close()

    if progress is None:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO progress(user_id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()
        return (0, 0, 0, 0)

    return progress


def set_lecture_unlocked(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE progress SET lecture_unlocked=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


def set_lecture_completed(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE progress SET lecture_completed=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


def set_quiz_completed(user_id, score):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE progress SET quiz_completed=1, quiz_score=? WHERE user_id=?", (score, user_id))
    conn.commit()
    conn.close()


def create_booking(user_id, tutor_name, lesson_topic, preferred_time, message):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT id FROM bookings
    WHERE user_id=? AND tutor_name=?
    """, (user_id, tutor_name))
    existing = cur.fetchone()

    if existing:
        conn.close()
        return False, "You have already booked this tutor."

    cur.execute("""
    INSERT INTO bookings(user_id, tutor_name, lesson_topic, preferred_time, message, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        tutor_name,
        lesson_topic,
        preferred_time,
        message,
        "Accepted",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()

    set_lecture_unlocked(user_id)
    return True, "Tutor accepted your request. The lecture is now unlocked."


def get_bookings(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT tutor_name, lesson_topic, preferred_time, status, created_at
    FROM bookings
    WHERE user_id=?
    ORDER BY id DESC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


class DarkButton(tk.Button):
    def __init__(self, master, text, command=None, bg=ACCENT_DARK, fg=TEXT, **kwargs):
        super().__init__(
            master,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=ACCENT,
            activeforeground="#0f172a",
            relief="flat",
            bd=0,
            padx=12,
            pady=7,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
            **kwargs
        )


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        init_db()

        self.title("AI Assisted Tutor Desktop App")
        self.geometry("1050x680")
        self.minsize(920, 620)
        self.configure(bg=BG)

        self.current_user_id = None
        self.current_user_name = None

        self.container = tk.Frame(self, bg=BG)
        self.container.pack(fill="both", expand=True)

        self.show_login()

    # ---------- basic helpers ----------

    def clear(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def entry(self, parent, show=None):
        return tk.Entry(
            parent,
            bg=INPUT,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=FONT_BODY,
            show=show,
            highlightbackground=BORDER,
            highlightthickness=1
        )

    def label(self, parent, text, font=FONT_BODY, fg=TEXT, bg=None, wraplength=None):
        return tk.Label(
            parent,
            text=text,
            font=font,
            fg=fg,
            bg=bg or CARD,
            justify="left",
            anchor="w",
            wraplength=wraplength
        )

    def card(self, parent, padx=16, pady=10, expand=False):
        frame = tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        frame.pack(fill="both", expand=expand, padx=padx, pady=pady)
        return frame

    def make_scrollable(self, parent, bg=BG, padx=16, pady=10):
        outer = tk.Frame(parent, bg=bg)
        outer.pack(fill="both", expand=True, padx=padx, pady=pady)

        canvas = tk.Canvas(outer, bg=bg, highlightthickness=0)
        scrollbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        frame = tk.Frame(canvas, bg=bg)

        frame.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        window_id = canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def resize_frame(event):
            canvas.itemconfig(window_id, width=event.width)

        canvas.bind("<Configure>", resize_frame)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", on_mousewheel)

        return frame, canvas

    def safe_unbind_mousewheel(self, canvas):
        try:
            canvas.unbind_all("<MouseWheel>")
        except Exception:
            pass

    # ---------- auth screens ----------

    def show_login(self):
        self.clear()

        outer = tk.Frame(self.container, bg=BG)
        outer.pack(fill="both", expand=True)

        tk.Label(
            outer,
            text="AI Assisted Tutoring",
            font=("Segoe UI", 26, "bold"),
            fg=TEXT,
            bg=BG
        ).pack(pady=(55, 5))

        tk.Label(
            outer,
            text="Desktop application for tutor booking, learning and AI support",
            font=("Segoe UI", 11),
            fg=MUTED,
            bg=BG
        ).pack(pady=(0, 22))

        box = tk.Frame(outer, bg=CARD, padx=32, pady=26, highlightbackground=BORDER, highlightthickness=1)
        box.pack()

        tk.Label(box, text="Login", font=FONT_TITLE, fg=TEXT, bg=CARD).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 18))

        tk.Label(box, text="Email", font=FONT_BODY, fg=MUTED, bg=CARD).grid(row=1, column=0, sticky="w")
        email = self.entry(box)
        email.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 12), ipady=7)

        tk.Label(box, text="Password", font=FONT_BODY, fg=MUTED, bg=CARD).grid(row=3, column=0, sticky="w")
        password = self.entry(box, show="*")
        password.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(4, 16), ipady=7)

        box.columnconfigure(0, weight=1)
        box.columnconfigure(1, weight=1)

        def do_login():
            user = login_user(email.get().strip(), password.get().strip())
            if user:
                self.current_user_id = user[0]
                self.current_user_name = user[1]
                self.show_dashboard()
            else:
                messagebox.showerror("Login failed", "Wrong email or password.")

        DarkButton(box, "Login", do_login).grid(row=5, column=0, sticky="ew", padx=(0, 6))
        DarkButton(box, "Create account", self.show_register, bg="#334155").grid(row=5, column=1, sticky="ew", padx=(6, 0))

        tk.Label(
            outer,
            text="Create a new account first. Data is saved locally in SQLite.",
            font=FONT_SMALL,
            fg=MUTED,
            bg=BG
        ).pack(pady=16)

    def show_register(self):
        self.clear()

        outer = tk.Frame(self.container, bg=BG)
        outer.pack(fill="both", expand=True)

        box = tk.Frame(outer, bg=CARD, padx=32, pady=24, highlightbackground=BORDER, highlightthickness=1)
        box.pack(pady=30)

        tk.Label(box, text="Create Account", font=FONT_TITLE, fg=TEXT, bg=CARD).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 16))

        fields = {}
        labels = [
            ("Full name", "full_name"),
            ("Email", "email"),
            ("Password", "password"),
            ("English level", "english_level"),
            ("Learning goal", "learning_goal")
        ]

        for i, (label, key) in enumerate(labels, start=1):
            tk.Label(box, text=label, fg=MUTED, bg=CARD, font=FONT_BODY).grid(row=i * 2 - 1, column=0, sticky="w", pady=(6, 0))
            entry = self.entry(box, show="*" if key == "password" else None)
            entry.grid(row=i * 2, column=0, columnspan=2, sticky="ew", pady=(4, 6), ipady=7)
            fields[key] = entry

        fields["english_level"].insert(0, "A2")
        fields["learning_goal"].insert(0, "Improve grammar and speaking")

        box.columnconfigure(0, weight=1)
        box.columnconfigure(1, weight=1)

        def do_register():
            values = {k: v.get().strip() for k, v in fields.items()}

            if not all(values.values()):
                messagebox.showwarning("Missing data", "Please fill in all fields.")
                return

            if len(values["password"]) < 4:
                messagebox.showwarning("Weak password", "Password must contain at least 4 characters.")
                return

            ok, msg = create_user(
                values["full_name"],
                values["email"],
                values["password"],
                values["english_level"],
                values["learning_goal"]
            )

            if ok:
                messagebox.showinfo("Success", msg)
                self.show_login()
            else:
                messagebox.showerror("Error", msg)

        DarkButton(box, "Register", do_register).grid(row=11, column=0, sticky="ew", padx=(0, 6), pady=(14, 0))
        DarkButton(box, "Back to login", self.show_login, bg="#334155").grid(row=11, column=1, sticky="ew", padx=(6, 0), pady=(14, 0))

    # ---------- layout ----------

    def sidebar(self, parent):
        side = tk.Frame(parent, bg=SIDEBAR, width=190)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        tk.Label(
            side,
            text="Search and Learn",
            font=("Segoe UI", 15, "bold"),
            fg=TEXT,
            bg=SIDEBAR
        ).pack(anchor="w", padx=14, pady=(18, 4))

        tk.Label(
            side,
            text=f"User: {self.current_user_name}",
            font=FONT_SMALL,
            fg=MUTED,
            bg=SIDEBAR,
            wraplength=160,
            justify="left"
        ).pack(anchor="w", padx=14, pady=(0, 14))

        buttons = [
            ("Dashboard", self.show_dashboard),
            ("My Profile", self.show_profile),
            ("Tutor Search", self.show_tutor),
            ("English Lecture", self.show_lecture),
            ("Quiz", self.show_quiz),
            ("AI Assistant", self.show_ai),
            ("Logout", self.logout),
        ]

        for text, cmd in buttons:
            DarkButton(side, text, cmd, bg="#172033").pack(fill="x", padx=12, pady=4)

    def page_base(self, title, subtitle=""):
        self.clear()

        root = tk.Frame(self.container, bg=BG)
        root.pack(fill="both", expand=True)

        self.sidebar(root)

        main = tk.Frame(root, bg=BG)
        main.pack(side="right", fill="both", expand=True)

        tk.Label(main, text=title, font=FONT_TITLE, fg=TEXT, bg=BG).pack(anchor="w", padx=22, pady=(18, 4))

        if subtitle:
            tk.Label(
                main,
                text=subtitle,
                font=FONT_BODY,
                fg=MUTED,
                bg=BG,
                wraplength=850,
                justify="left"
            ).pack(anchor="w", padx=22, pady=(0, 8))

        return main

    # ---------- dashboard and profile ----------

    def show_dashboard(self):
        main = self.page_base(
            "Dashboard",
            "Project prototype with authentication, profile, tutor booking, lecture, quiz and AI assistant."
        )

        progress = get_progress(self.current_user_id)
        lecture_unlocked, lecture_completed, quiz_completed, quiz_score = progress

        grid = tk.Frame(main, bg=BG)
        grid.pack(fill="x", padx=16, pady=8)

        cards = [
            ("Tutor booking", "Available", GREEN),
            ("Lecture access", "Unlocked" if lecture_unlocked else "Locked", GREEN if lecture_unlocked else RED),
            ("Lecture status", "Completed" if lecture_completed else "Not completed", GREEN if lecture_completed else YELLOW),
            ("Quiz result", f"{quiz_score}/10" if quiz_completed else "Not completed", GREEN if quiz_completed else YELLOW),
        ]

        for i, (name, value, color) in enumerate(cards):
            c = tk.Frame(grid, bg=CARD, padx=12, pady=12, highlightbackground=BORDER, highlightthickness=1)
            c.grid(row=0, column=i, sticky="nsew", padx=4)
            tk.Label(c, text=name, font=FONT_SMALL, fg=MUTED, bg=CARD).pack(anchor="w")
            tk.Label(c, text=value, font=("Segoe UI", 13, "bold"), fg=color, bg=CARD).pack(anchor="w", pady=(6, 0))
            grid.columnconfigure(i, weight=1)

        info = self.card(main)
        self.label(info, "How the app works", FONT_H2).pack(anchor="w", padx=14, pady=(14, 6))

        text = (
            "1. Create an account and log in.\n"
            "2. Open Tutor Search and choose an available tutor.\n"
            "3. Send a message and book a lesson.\n"
            "4. After booking, the English lecture becomes available.\n"
            "5. Read the lecture and mark it as completed.\n"
            "6. After completing the lecture, the quiz becomes available.\n"
            "7. Use the AI assistant to ask questions about grammar, booking or learning plans."
        )

        self.label(info, text, FONT_BODY, wraplength=780).pack(anchor="w", padx=14, pady=(0, 14))

        bookings = get_bookings(self.current_user_id)
        if bookings:
            bcard = self.card(main)
            self.label(bcard, "Latest booking", FONT_H2).pack(anchor="w", padx=14, pady=(14, 6))
            tutor, topic, time, status, created = bookings[0]
            self.label(
                bcard,
                f"Tutor: {tutor}\nTopic: {topic}\nPreferred time: {time}\nStatus: {status}\nCreated: {created}",
                FONT_BODY,
                wraplength=780
            ).pack(anchor="w", padx=14, pady=(0, 14))

    def show_profile(self):
        main = self.page_base("My Profile", "Your learning profile and unlocked learning materials.")

        user = get_user(self.current_user_id)
        lecture_unlocked, lecture_completed, quiz_completed, quiz_score = get_progress(self.current_user_id)

        c = self.card(main)
        self.label(c, "User Information", FONT_H2).pack(anchor="w", padx=14, pady=(14, 6))

        info = (
            f"Full name: {user[1]}\n"
            f"Email: {user[2]}\n"
            f"English level: {user[3]}\n"
            f"Learning goal: {user[4]}\n"
            f"Created at: {user[5]}"
        )

        self.label(c, info, FONT_BODY, wraplength=780).pack(anchor="w", padx=14, pady=(0, 14))

        p = self.card(main)
        self.label(p, "Learning Progress", FONT_H2).pack(anchor="w", padx=14, pady=(14, 6))

        status = (
            f"Lecture unlocked: {'Yes' if lecture_unlocked else 'No'}\n"
            f"Lecture completed: {'Yes' if lecture_completed else 'No'}\n"
            f"Quiz completed: {'Yes' if quiz_completed else 'No'}\n"
            f"Quiz score: {quiz_score}/10"
        )

        self.label(p, status, FONT_BODY, wraplength=780).pack(anchor="w", padx=14, pady=(0, 12))

        if lecture_unlocked:
            DarkButton(p, "Open lecture", self.show_lecture).pack(anchor="w", padx=14, pady=(0, 14))
        else:
            self.label(
                p,
                "Book a lesson with an available tutor to unlock the lecture.",
                FONT_BODY,
                fg=YELLOW,
                wraplength=780
            ).pack(anchor="w", padx=14, pady=(0, 14))

    # ---------- tutors ----------

    def get_tutors(self):
        return [
            {
                "id": 1,
                "name": "Yegor Gorokhvodatsky",
                "subject": "English Tutor | Grammar, Speaking, Vocabulary",
                "phone": "+7 708 163 19 67",
                "price": "2500 KZT per lesson",
                "rating": "4.9/5",
                "format": "Online / Offline",
                "status": "Available",
                "bio": (
                    "I help students improve English grammar, speaking confidence and vocabulary. "
                    "My lessons include simple explanations, real examples, speaking practice, "
                    "grammar exercises and personal feedback."
                )
            },
            {
                "id": 2,
                "name": "Aigerim Nurlanova",
                "subject": "English Tutor | IELTS, Academic Writing",
                "phone": "+7 701 555 20 11",
                "price": "8000 KZT per lesson",
                "rating": "4.8/5",
                "format": "Online",
                "status": "Busy",
                "bio": (
                    "Aigerim specializes in IELTS preparation, academic writing and university entrance English. "
                    "At the moment she is fully booked and cannot accept new students."
                )
            },
            {
                "id": 3,
                "name": "Daniel Smith",
                "subject": "English Tutor | Speaking, Pronunciation",
                "phone": "+7 708 222 90 44",
                "price": "7000 KZT per lesson",
                "rating": "4.7/5",
                "format": "Online",
                "status": "Busy",
                "bio": (
                    "Daniel helps students improve pronunciation, listening and speaking fluency. "
                    "He is currently busy and is not available for new lesson requests."
                )
            }
        ]

    def user_has_booking_with_tutor(self, tutor_name):
        bookings = get_bookings(self.current_user_id)
        return any(row[0] == tutor_name for row in bookings)

    def draw_tutor_avatar(self, canvas, cx, cy, scale=1):
        canvas.create_oval(cx - 18 * scale, cy - 28 * scale, cx + 18 * scale, cy + 8 * scale, fill="#64748b", outline="")
        canvas.create_rectangle(cx - 25 * scale, cy + 8 * scale, cx + 25 * scale, cy + 38 * scale, fill="#475569", outline="")
        canvas.create_text(cx, cy + 34 * scale, text="Tutor", fill=TEXT, font=("Segoe UI", max(7, int(8 * scale)), "bold"))

    def show_tutor(self):
        main = self.page_base("Tutor Search", "Search for an English tutor and open a tutor profile.")

        search_card = tk.Frame(main, bg=CARD, padx=14, pady=12, highlightbackground=BORDER, highlightthickness=1)
        search_card.pack(fill="x", padx=16, pady=10)

        tk.Label(search_card, text="Search by tutor name", bg=CARD, fg=MUTED, font=FONT_BODY).pack(anchor="w")
        search_entry = self.entry(search_card)
        search_entry.pack(fill="x", pady=(5, 8), ipady=6)

        button_row = tk.Frame(search_card, bg=CARD)
        button_row.pack(fill="x")

        list_frame, canvas = self.make_scrollable(main, bg=BG, padx=16, pady=10)

        def open_selected_tutor(tutor):
            self.safe_unbind_mousewheel(canvas)
            self.show_tutor_profile(tutor)

        def render_list():
            for widget in list_frame.winfo_children():
                widget.destroy()

            query = search_entry.get().strip().lower()
            tutors = self.get_tutors()

            if query:
                tutors = [t for t in tutors if query in t["name"].lower()]

            if not tutors:
                empty = tk.Frame(list_frame, bg=CARD, padx=14, pady=14, highlightbackground=BORDER, highlightthickness=1)
                empty.pack(fill="x", pady=(0, 8))
                self.label(empty, "No tutors found.", FONT_H2).pack(anchor="w")
                return

            for tutor in tutors:
                status_color = GREEN if tutor["status"] == "Available" else RED

                card = tk.Frame(
                    list_frame,
                    bg=CARD,
                    padx=14,
                    pady=12,
                    highlightbackground=BORDER,
                    highlightthickness=1,
                    cursor="hand2"
                )
                card.pack(fill="x", pady=(0, 10))

                header = tk.Frame(card, bg=CARD, cursor="hand2")
                header.pack(fill="x")

                photo = tk.Canvas(
                    header,
                    width=82,
                    height=82,
                    bg=CARD_2,
                    highlightthickness=1,
                    highlightbackground=BORDER,
                    cursor="hand2"
                )
                photo.pack(side="left", padx=(0, 12), anchor="n")
                self.draw_tutor_avatar(photo, 41, 40, 1)

                info = tk.Frame(header, bg=CARD, cursor="hand2")
                info.pack(side="left", fill="x", expand=True)

                name_label = tk.Label(info, text=tutor["name"], bg=CARD, fg=TEXT, font=("Segoe UI", 14, "bold"), cursor="hand2")
                name_label.pack(anchor="w")

                subject_label = tk.Label(info, text=tutor["subject"], bg=CARD, fg=ACCENT, font=FONT_SMALL, cursor="hand2", justify="left", wraplength=650)
                subject_label.pack(anchor="w", pady=(2, 3))

                meta_label = tk.Label(
                    info,
                    text=f"Status: {tutor['status']} | Price: {tutor['price']} | Rating: {tutor['rating']}",
                    bg=CARD,
                    fg=status_color,
                    font=FONT_SMALL,
                    cursor="hand2",
                    justify="left",
                    wraplength=650
                )
                meta_label.pack(anchor="w")

                bio_label = tk.Label(
                    card,
                    text=tutor["bio"],
                    bg=CARD,
                    fg=MUTED,
                    font=FONT_SMALL,
                    justify="left",
                    anchor="w",
                    wraplength=760,
                    cursor="hand2"
                )
                bio_label.pack(fill="x", pady=(8, 8))

                btn_row = tk.Frame(card, bg=CARD)
                btn_row.pack(fill="x")
                DarkButton(btn_row, "Open profile", lambda t=tutor: open_selected_tutor(t), bg="#334155").pack(anchor="w")

                clickable = [card, header, photo, info, name_label, subject_label, meta_label, bio_label]
                for w in clickable:
                    w.bind("<Button-1>", lambda event, t=tutor: open_selected_tutor(t))

        DarkButton(button_row, "Search", render_list, bg="#334155").pack(side="left")
        DarkButton(button_row, "Clear", lambda: (search_entry.delete(0, "end"), render_list()), bg="#334155").pack(side="left", padx=8)

        search_entry.bind("<KeyRelease>", lambda event: render_list())
        render_list()

    def show_tutor_profile(self, tutor):
        main = self.page_base("Tutor Profile", "View tutor information and send a lesson request.")
        content, canvas = self.make_scrollable(main, bg=BG, padx=16, pady=10)

        c = tk.Frame(content, bg=CARD, padx=16, pady=16, highlightbackground=BORDER, highlightthickness=1)
        c.pack(fill="both", expand=True)

        top = tk.Frame(c, bg=CARD)
        top.pack(fill="x")

        photo = tk.Canvas(top, width=110, height=110, bg=CARD_2, highlightthickness=1, highlightbackground=BORDER)
        photo.pack(side="left", padx=(0, 16), anchor="n")
        self.draw_tutor_avatar(photo, 55, 52, 1.25)

        details = tk.Frame(top, bg=CARD)
        details.pack(side="left", fill="both", expand=True)

        status_color = GREEN if tutor["status"] == "Available" else RED

        tk.Label(
            details,
            text=tutor["name"],
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 18, "bold"),
            wraplength=700,
            justify="left"
        ).pack(anchor="w")

        tk.Label(
            details,
            text=tutor["subject"],
            bg=CARD,
            fg=ACCENT,
            font=FONT_BODY,
            wraplength=700,
            justify="left"
        ).pack(anchor="w", pady=(4, 6))

        tk.Label(details, text=f"Status: {tutor['status']}", bg=CARD, fg=status_color, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 5))
        tk.Label(details, text=f"Phone: {tutor['phone']}", bg=CARD, fg=TEXT, font=FONT_BODY).pack(anchor="w")

        tk.Label(
            details,
            text=f"Format: {tutor['format']} | Price: {tutor['price']} | Rating: {tutor['rating']}",
            bg=CARD,
            fg=MUTED,
            font=FONT_BODY,
            wraplength=700,
            justify="left"
        ).pack(anchor="w", pady=(4, 8))

        bio_box = tk.Frame(c, bg=CARD_2, padx=12, pady=10, highlightbackground=BORDER, highlightthickness=1)
        bio_box.pack(fill="x", pady=(14, 12))

        tk.Label(bio_box, text="Short bio", bg=CARD_2, fg=TEXT, font=FONT_H2).pack(anchor="w", pady=(0, 6))

        tk.Label(
            bio_box,
            text=tutor["bio"],
            bg=CARD_2,
            fg=TEXT,
            font=FONT_BODY,
            justify="left",
            anchor="w",
            wraplength=780
        ).pack(fill="x", anchor="w")

        def back_to_search():
            self.safe_unbind_mousewheel(canvas)
            self.show_tutor()

        if tutor["status"] != "Available":
            locked = tk.Frame(c, bg=CARD_2, padx=12, pady=10, highlightbackground=BORDER, highlightthickness=1)
            locked.pack(fill="x", pady=(0, 12))

            tk.Label(
                locked,
                text="This tutor is currently busy and cannot accept new messages or bookings.",
                bg=CARD_2,
                fg=YELLOW,
                font=FONT_BODY,
                justify="left",
                wraplength=780
            ).pack(anchor="w")

            DarkButton(c, "Back to search", back_to_search, bg="#334155").pack(anchor="w")
            return

        if self.user_has_booking_with_tutor(tutor["name"]):
            already = tk.Frame(c, bg=CARD_2, padx=12, pady=10, highlightbackground=BORDER, highlightthickness=1)
            already.pack(fill="x", pady=(0, 12))

            tk.Label(
                already,
                text="You have already booked this tutor. You cannot book the same tutor twice.",
                bg=CARD_2,
                fg=YELLOW,
                font=FONT_BODY,
                justify="left",
                wraplength=780
            ).pack(anchor="w")

            DarkButton(c, "Open lecture", lambda: (self.safe_unbind_mousewheel(canvas), self.show_lecture())).pack(anchor="w")
            return

        form = tk.Frame(c, bg=CARD_2, padx=12, pady=10, highlightbackground=BORDER, highlightthickness=1)
        form.pack(fill="x", pady=(0, 12))

        tk.Label(form, text="Write to tutor and book a lesson", bg=CARD_2, fg=TEXT, font=FONT_H2).pack(anchor="w", pady=(0, 8))

        tk.Label(form, text="Preferred date and time", bg=CARD_2, fg=MUTED, font=FONT_BODY).pack(anchor="w")
        preferred = self.entry(form)
        preferred.insert(0, "Monday 18:00")
        preferred.pack(fill="x", pady=(4, 8), ipady=6)

        tk.Label(form, text="Message", bg=CARD_2, fg=MUTED, font=FONT_BODY).pack(anchor="w")

        message_box = tk.Text(
            form,
            bg=INPUT,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            height=5,
            font=FONT_BODY,
            wrap="word",
            highlightbackground=BORDER,
            highlightthickness=1
        )
        message_box.insert("1.0", "Hello, I want to book an English lesson and improve my grammar and speaking.")
        message_box.pack(fill="x", pady=(4, 10))

        def send_and_book():
            preferred_time = preferred.get().strip()
            message = message_box.get("1.0", "end").strip()

            if not preferred_time:
                messagebox.showwarning("Missing time", "Please enter preferred lesson time.")
                return

            ok, msg = create_booking(
                self.current_user_id,
                tutor["name"],
                "English Grammar and Speaking",
                preferred_time,
                message
            )

            self.safe_unbind_mousewheel(canvas)

            if ok:
                messagebox.showinfo("Tutor response", "Tutor accepted your request.\n\nLecture access is now unlocked in your profile.")
                self.show_profile()
            else:
                messagebox.showwarning("Booking problem", msg)
                self.show_profile()

        actions = tk.Frame(form, bg=CARD_2)
        actions.pack(fill="x")

        DarkButton(actions, "Send message and book lesson", send_and_book).pack(side="left")
        DarkButton(actions, "Back to search", back_to_search, bg="#334155").pack(side="left", padx=8)

    # ---------- lecture ----------

    def show_lecture(self):
        lecture_unlocked, lecture_completed, quiz_completed, quiz_score = get_progress(self.current_user_id)

        main = self.page_base("English Lecture", "Lecture becomes available after booking a lesson with an available tutor.")

        if not lecture_unlocked:
            c = self.card(main)
            self.label(c, "Lecture is locked", FONT_H2, fg=RED).pack(anchor="w", padx=14, pady=(14, 6))
            self.label(
                c,
                "Please book a lesson with an available tutor first. After booking, the lecture will appear in your profile.",
                FONT_BODY,
                wraplength=780
            ).pack(anchor="w", padx=14, pady=(0, 14))
            DarkButton(c, "Go to Tutor Search", self.show_tutor).pack(anchor="w", padx=14, pady=(0, 14))
            return

        content, canvas = self.make_scrollable(main, bg=BG, padx=16, pady=10)

        c = tk.Frame(content, bg=CARD, padx=14, pady=14, highlightbackground=BORDER, highlightthickness=1)
        c.pack(fill="both", expand=True)

        self.label(c, "Test Lecture: Present Simple in English", FONT_H2).pack(anchor="w", padx=0, pady=(0, 8))

        lecture = (
            "Present Simple is one of the basic English tenses. It is used when we talk about habits, repeated actions, facts, "
            "general truths and permanent situations.\n\n"
            "1. Habits and repeated actions\n"
            "We use Present Simple for actions that happen regularly. For example: I study English every day. "
            "She reads books in the evening. They play football on Sundays.\n\n"
            "2. Facts and general truths\n"
            "Present Simple is also used for facts that are always true. For example: Water boils at 100 degrees Celsius. "
            "The Earth goes around the Sun. English has many irregular verbs.\n\n"
            "3. Positive sentences\n"
            "For I, you, we and they, we use the base form of the verb: I work, you study, we learn, they speak. "
            "For he, she and it, we usually add -s or -es: he works, she studies, it goes.\n\n"
            "4. Negative sentences\n"
            "We use do not or does not. For I, you, we and they, we use do not. Example: I do not speak French. "
            "For he, she and it, we use does not. Example: She does not play tennis.\n\n"
            "5. Questions\n"
            "Questions are formed with do or does. Example: Do you like English? Does he study every day? "
            "After does, the main verb does not take -s. We say: Does she speak English? Not: Does she speaks English.\n\n"
            "6. Common time markers\n"
            "Present Simple is often used with words like always, usually, often, sometimes, rarely, never, every day, every week and on Mondays.\n\n"
            "Examples:\n"
            "I usually wake up at 7 o'clock.\n"
            "She often watches educational videos.\n"
            "They do not study at night.\n"
            "Does your friend speak English?\n\n"
            "Main rule: use the base verb for I, you, we and they. Add -s or -es for he, she and it in positive sentences."
        )

        tk.Label(
            c,
            text=lecture,
            bg=INPUT,
            fg=TEXT,
            font=FONT_BODY,
            justify="left",
            anchor="w",
            wraplength=820,
            padx=12,
            pady=12
        ).pack(fill="x", pady=(0, 12))

        actions = tk.Frame(c, bg=CARD)
        actions.pack(fill="x")

        def open_video():
            webbrowser.open("https://www.youtube.com/results?search_query=present+simple+english+grammar+lesson")

        DarkButton(actions, "Open YouTube video", open_video, bg="#334155").pack(side="left", padx=(0, 8))

        def complete():
            set_lecture_completed(self.current_user_id)
            self.safe_unbind_mousewheel(canvas)
            messagebox.showinfo("Lecture completed", "Lecture marked as completed. Quiz is now unlocked.")
            self.show_quiz()

        DarkButton(actions, "I have read the lecture, unlock quiz", complete).pack(side="left")

    # ---------- quiz ----------

    def show_quiz(self):
        lecture_unlocked, lecture_completed, quiz_completed, quiz_score = get_progress(self.current_user_id)

        main = self.page_base("Quiz", "10 questions based on the Present Simple lecture.")

        if not lecture_unlocked:
            c = self.card(main)
            self.label(c, "Quiz is locked", FONT_H2, fg=RED).pack(anchor="w", padx=14, pady=(14, 6))
            self.label(c, "Book a lesson first, then read the lecture.", FONT_BODY).pack(anchor="w", padx=14, pady=(0, 14))
            return

        if not lecture_completed:
            c = self.card(main)
            self.label(c, "Quiz is locked until the lecture is completed", FONT_H2, fg=YELLOW).pack(anchor="w", padx=14, pady=(14, 6))
            self.label(
                c,
                "Please read the lecture and press the completion button before starting the quiz.",
                FONT_BODY,
                wraplength=780
            ).pack(anchor="w", padx=14, pady=(0, 14))
            DarkButton(c, "Open lecture", self.show_lecture).pack(anchor="w", padx=14, pady=(0, 14))
            return

        questions = [
            ("1. She ___ English every day.", ["study", "studies", "studying"], "studies"),
            ("2. They ___ football on Sundays.", ["plays", "play", "playing"], "play"),
            ("3. ___ you like English?", ["Do", "Does", "Are"], "Do"),
            ("4. He ___ not speak French.", ["do", "does", "is"], "does"),
            ("5. Water ___ at 100 degrees Celsius.", ["boil", "boils", "boiling"], "boils"),
            ("6. My brother usually ___ at 7 o'clock.", ["wake up", "wakes up", "waking up"], "wakes up"),
            ("7. Does she ___ books in English?", ["reads", "read", "reading"], "read"),
            ("8. I ___ coffee in the evening.", ["do not drink", "does not drink", "not drinks"], "do not drink"),
            ("9. Present Simple is used for ___ actions.", ["regular", "only future", "only past"], "regular"),
            ("10. He, she, it usually takes the verb with ___.", ["-s or -es", "-ing", "will"], "-s or -es"),
        ]

        content, canvas = self.make_scrollable(main, bg=BG, padx=16, pady=10)

        outer = tk.Frame(content, bg=CARD, padx=14, pady=14, highlightbackground=BORDER, highlightthickness=1)
        outer.pack(fill="both", expand=True)

        self.label(outer, "Present Simple Quiz", FONT_H2).pack(anchor="w", pady=(0, 8))

        vars_ = []

        for q, options, answer in questions:
            block = tk.Frame(outer, bg=CARD_2, padx=10, pady=8, highlightbackground=BORDER, highlightthickness=1)
            block.pack(fill="x", pady=5)

            tk.Label(block, text=q, bg=CARD_2, fg=TEXT, font=("Segoe UI", 10, "bold"), justify="left", anchor="w", wraplength=800).pack(anchor="w")

            var = tk.StringVar(value="")
            vars_.append((var, answer))

            for option in options:
                rb = tk.Radiobutton(
                    block,
                    text=option,
                    variable=var,
                    value=option,
                    bg=CARD_2,
                    fg=TEXT,
                    selectcolor=INPUT,
                    activebackground=CARD_2,
                    activeforeground=ACCENT,
                    font=FONT_BODY
                )
                rb.pack(anchor="w")

        def submit():
            if any(not var.get() for var, ans in vars_):
                messagebox.showwarning("Unanswered questions", "Please answer all questions before submitting.")
                return

            score = sum(1 for var, ans in vars_ if var.get() == ans)
            set_quiz_completed(self.current_user_id, score)

            if score >= 8:
                msg = f"Excellent result: {score}/10"
            elif score >= 5:
                msg = f"Good attempt: {score}/10. Review the lecture and try to improve."
            else:
                msg = f"Result: {score}/10. You should review Present Simple again."

            self.safe_unbind_mousewheel(canvas)
            messagebox.showinfo("Quiz result", msg)
            self.show_profile()

        DarkButton(outer, "Submit quiz", submit).pack(anchor="w", pady=(12, 0))

    # ---------- AI assistant ----------

    def offline_ai_answer(self, question):
        q = question.lower()

        if "present simple" in q:
            return (
                "Present Simple is used for habits, facts and regular actions. "
                "Example: I study English every day. She studies English every day."
            )

        if "negative" in q:
            return (
                "In Present Simple negative sentences, use do not or does not. "
                "Example: I do not play tennis. She does not play tennis."
            )

        if "question" in q or "do" in q or "does" in q:
            return (
                "In Present Simple questions, use do or does. "
                "Example: Do you study English? Does she speak English?"
            )

        if "book" in q or "lesson" in q or "tutor" in q:
            return (
                "Open Tutor Search, choose an available tutor, open the tutor profile, "
                "write a message and book a lesson. After booking, the lecture becomes available."
            )

        if "quiz" in q or "test" in q:
            return "The quiz becomes available after you book a tutor and complete the lecture."

        if "study plan" in q or "plan" in q:
            return (
                "A simple study plan: grammar for 20 minutes, vocabulary for 15 minutes, "
                "and speaking practice for 10 minutes every day."
            )

        return "I can help with English grammar, Present Simple, tutor booking, quiz preparation and study planning."

    def generate_ai_answer(self, question):
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            return self.offline_ai_answer(question)

        if OpenAI is None:
            return self.offline_ai_answer(question)

        try:
            client = OpenAI(api_key=api_key)

            response = client.responses.create(
                model="gpt-4.1-mini",
                input=(
                    "You are an AI assistant inside an English tutoring desktop app. "
                    "Help students with English grammar, Present Simple, tutor booking, "
                    "quiz preparation and study plans. Answer briefly and clearly.\n\n"
                    f"User question: {question}"
                )
            )

            return response.output_text

        except Exception:
            return self.offline_ai_answer(question)

    def show_ai(self):
        main = self.page_base("AI Assistant", "Assistant for English learning, tutor booking and study planning.")

        c = self.card(main, expand=True)
        self.label(c, "Ask the AI Assistant", FONT_H2).pack(anchor="w", padx=14, pady=(14, 8))

        chat = tk.Text(
            c,
            bg=INPUT,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            height=18,
            wrap="word",
            font=FONT_BODY,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        chat.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        chat.insert("1.0", "AI Assistant: Hello. I can help you with English grammar, tutor booking and learning plans.\n\n")
        chat.config(state="disabled")

        entry = self.entry(c)
        entry.pack(fill="x", padx=14, pady=(0, 10), ipady=8)
        entry.insert(0, "Explain Present Simple")

        def send():
            q = entry.get().strip()

            if not q:
                return

            answer = self.generate_ai_answer(q)

            chat.config(state="normal")
            chat.insert("end", f"You: {q}\n")
            chat.insert("end", f"AI Assistant: {answer}\n\n")
            chat.see("end")
            chat.config(state="disabled")
            entry.delete(0, "end")

        btn_row = tk.Frame(c, bg=CARD)
        btn_row.pack(fill="x", padx=14, pady=(0, 14))

        DarkButton(btn_row, "Send", send).pack(side="left")
        DarkButton(btn_row, "Clear input", lambda: entry.delete(0, "end"), bg="#334155").pack(side="left", padx=8)

    def logout(self):
        self.current_user_id = None
        self.current_user_name = None
        self.show_login()


if __name__ == "__main__":
    app = App()
    app.mainloop()
