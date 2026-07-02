"""
Saving Group Loan Management System
School project — built with AI assistance
"""

import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
import sqlite3
import datetime

from db import DB_PATH, DATA_DIR, get_db, close_db, init_db, log_action, ensure_first_login_bootstrap
from services import (
    QUARTERLY_SAVING,
    calc_interest,
    parse_iso_date,
    parse_positive_amount,
    hash_pw_pbkdf2,
    verify_password,
)
from ui_tables import make_tree, EditableTreeview
from views_statement import build_statement_view

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

def install_tk_bgerror_handler(root):
    """
    Ignore known harmless Tk background callback errors fired during shutdown.
    """
    root.tk.eval(
        """
        proc bgerror {msg} {
            if {[string match "invalid command name *" $msg] ||
                [string match "*check_dpi_scaling*" $msg] ||
                [string match "*update*" $msg] ||
                [string match "*_click_animation*" $msg]} {
                return
            }
            puts stderr $msg
        }
        """
    )

# ─── Login Window ──────────────────────────────────────────────────────────────

class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        install_tk_bgerror_handler(self)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.title("Saving Group — Login")
        self.geometry("400x480")
        self.resizable(False, False)
        self.current_user = None

        frame = ctk.CTkFrame(self, corner_radius=16)
        frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.85)

        ctk.CTkLabel(frame, text="💰", font=("Arial", 48)).pack(pady=(28, 4))
        ctk.CTkLabel(frame, text="Saving Group", font=ctk.CTkFont(size=22, weight="bold")).pack()
        ctk.CTkLabel(frame, text="Loan Management System", text_color="gray").pack(pady=(2, 20))

        ctk.CTkLabel(frame, text="Username").pack(anchor="w", padx=28)
        self.user_entry = ctk.CTkEntry(frame, width=260, placeholder_text="Enter username")
        self.user_entry.pack(padx=28, pady=(4, 12))
        self.user_entry.insert(0, "admin")

        ctk.CTkLabel(frame, text="Password").pack(anchor="w", padx=28)
        self.pw_entry = ctk.CTkEntry(frame, width=260, show="●", placeholder_text="Enter password")
        self.pw_entry.pack(padx=28, pady=(4, 20))
        self.pw_entry.bind("<Return>", lambda e: self.do_login())

        self.err_label = ctk.CTkLabel(frame, text="", text_color="red")
        self.err_label.pack()

        ctk.CTkButton(frame, text="Login", width=260, height=40, command=self.do_login).pack(padx=28, pady=(4, 28))

        ctk.CTkLabel(self, text="Default: admin / admin123", text_color="gray", font=ctk.CTkFont(size=11)).pack(side="bottom", pady=8)

    def _on_close(self):
        # Stop event processing cleanly before destroying the window.
        try:
            self.quit()
        except tk.TclError:
            pass
        close_db()
        self.destroy()

    def do_login(self):
        u = self.user_entry.get().strip()
        p = self.pw_entry.get()
        with get_db() as conn:
            row = conn.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
        if row:
            if verify_password(p, row["password_hash"], row["password_salt"]):
                if not row["password_salt"]:
                    new_hash, salt = hash_pw_pbkdf2(p)
                    with get_db() as conn:
                        conn.execute(
                            "UPDATE users SET password_hash=?, password_salt=? WHERE id=?",
                            (new_hash, salt, row["id"]),
                        )
                ensure_first_login_bootstrap(u)
                self.current_user = u
                self.destroy()
                return
        self.err_label.configure(text="Invalid username or password")
        self.pw_entry.delete(0, "end")

# ─── Main App ──────────────────────────────────────────────────────────────────

class MainApp(ctk.CTk):
    def __init__(self, username):
        super().__init__()
        install_tk_bgerror_handler(self)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.username = username
        self.title(f"Saving Group — Loan Management  ({username})")
        self.geometry("1200x720")
        self.minsize(900, 600)

        self._build_sidebar()
        self._build_content()
        self.show_dashboard()

    def _on_close(self):
        try:
            self.quit()
        except tk.TclError:
            pass
        close_db()
        self.destroy()

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        ctk.CTkLabel(self.sidebar, text="💰 Saving Group",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(24, 4))
        ctk.CTkLabel(self.sidebar, text=f"Developed by: Jr.Er Aayush Bhandari",
                     text_color="gray", font=ctk.CTkFont(size=10)).pack(pady=(0, 2))
        ctk.CTkLabel(self.sidebar, text=f"Logged in: {self.username}",
                     text_color="gray", font=ctk.CTkFont(size=11)).pack(pady=(0, 20))

        nav = [
            ("🏠  Dashboard", self.show_dashboard),
            ("👥  Members", self.show_members),
            ("💳  Loans", self.show_loans),
            ("💵  Savings", self.show_savings),
            ("🧾  Statement", self.show_statement),
            ("📊  Reports", self.show_reports),
            ("📋  Audit Log", self.show_audit),
            ("⚙️  Settings", self.show_settings),
        ]
        self.nav_buttons = []
        for label, cmd in nav:
            b = ctk.CTkButton(self.sidebar, text=label, anchor="w", height=42,
                              fg_color="transparent", text_color=("black", "white"),
                              hover_color=("gray85", "gray25"), command=cmd)
            b.pack(fill="x", padx=8, pady=2)
            self.nav_buttons.append((b, cmd))

        ctk.CTkButton(self.sidebar, text="🚪  Logout", anchor="w", height=42,
                      fg_color="transparent", text_color="red",
                      hover_color=("gray85", "gray25"), command=self.logout).pack(
            fill="x", padx=8, pady=2, side="bottom")

    def _build_content(self):
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray95", "gray10"))
        self.content.pack(side="right", fill="both", expand=True)

    def _clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def _header(self, title, subtitle=""):
        h = ctk.CTkFrame(self.content, fg_color="transparent")
        h.pack(fill="x", padx=24, pady=(20, 4))
        ctk.CTkLabel(h, text=title, font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")
        if subtitle:
            ctk.CTkLabel(h, text=subtitle, text_color="gray").pack(side="left", padx=12)
        return h

    # ── Dashboard ──────────────────────────────────────────────────────────────

    def show_dashboard(self):
        self._clear_content()
        self._header("Dashboard", "Quick overview")

        # Add custom date selector for interest calculations
        date_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        date_frame.pack(fill="x", padx=24, pady=(0, 8))
        
        ctk.CTkLabel(date_frame, text="Calculate interest as of:", 
                     font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 10))
        
        self.calc_date_var = ctk.StringVar(value=datetime.date.today().isoformat())
        self.calc_date_entry = ctk.CTkEntry(date_frame, textvariable=self.calc_date_var, 
                                           width=150, placeholder_text="YYYY-MM-DD")
        self.calc_date_entry.pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(date_frame, text="Use Today", width=80,
                     command=lambda: self.calc_date_var.set(datetime.date.today().isoformat())).pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(date_frame, text="Recalculate", width=100,
                     command=self._load_dashboard_data).pack(side="left")

        with get_db() as conn:
            members = conn.execute("SELECT COUNT(*) FROM members WHERE is_active=1").fetchone()[0]
            active_loans = conn.execute("SELECT COUNT(*) FROM loans WHERE status='active'").fetchone()[0]
            total_loan_amount = conn.execute("SELECT COALESCE(SUM(principal),0) FROM loans WHERE status='active'").fetchone()[0]
            total_savings = conn.execute("SELECT COALESCE(SUM(amount),0) FROM savings").fetchone()[0]
            loans_data = conn.execute(
                "SELECT l.id, m.name, l.principal, l.interest_rate, l.issue_date, l.notes FROM loans l "
                "JOIN members m ON l.member_id=m.id WHERE l.status='active' ORDER BY l.issue_date").fetchall()
            
            # Get custom calculation date
            try:
                calc_date = datetime.date.fromisoformat(self.calc_date_var.get())
            except (ValueError, AttributeError):
                calc_date = datetime.date.today()
            
            # Calculate total outstanding balance after repayments
            total_outstanding = 0
            for loan in loans_data:
                waive_interest = loan["notes"] and "INTEREST WAIVED" in loan["notes"].upper()
                interest_rate = loan["interest_rate"] if loan["interest_rate"] is not None else 10.0
                interest, _ = calc_interest(loan["principal"], loan["issue_date"], as_of=calc_date, waive_interest=waive_interest, interest_rate=interest_rate)
                
                # Calculate current principal after reductions
                principal_paid_result = conn.execute(
                    "SELECT COALESCE(SUM(principal_paid), 0) as principal_paid FROM repayments WHERE loan_id=?",
                    (loan["id"],)
                ).fetchone()
                principal_paid = principal_paid_result["principal_paid"] if principal_paid_result else 0
                current_principal = loan["principal"] - principal_paid
                
                total_due = current_principal + interest
                # Calculate interest paid so far
                interest_paid_result = conn.execute(
                    "SELECT COALESCE(SUM(interest_paid), 0) as interest_paid FROM repayments WHERE loan_id=?",
                    (loan["id"],)
                ).fetchone()
                interest_paid = interest_paid_result["interest_paid"] if interest_paid_result else 0
                # Remaining balance = current principal + remaining interest
                remaining_interest = max(0, interest - interest_paid)
                remaining = current_principal + remaining_interest
                total_outstanding += remaining

        total_interest = sum(
            calc_interest(r["principal"], r["issue_date"], as_of=calc_date, waive_interest=(r["notes"] and "INTEREST WAIVED" in r["notes"].upper()), interest_rate=r["interest_rate"] if r["interest_rate"] is not None else 10.0)[0] 
            for r in loans_data
        )

        cards = ctk.CTkFrame(self.content, fg_color="transparent")
        cards.pack(fill="x", padx=24, pady=10)

        def stat_card(parent, label, value, color):
            f = ctk.CTkFrame(parent, corner_radius=12)
            f.pack(side="left", expand=True, fill="both", padx=6, pady=4)
            ctk.CTkLabel(f, text=label, text_color="gray", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=16, pady=(14, 2))
            ctk.CTkLabel(f, text=value, font=ctk.CTkFont(size=22, weight="bold"),
                         text_color=color).pack(anchor="w", padx=16, pady=(0, 14))

        stat_card(cards, "Active Members", str(members), "#1a7abf")
        stat_card(cards, "Active Loans", str(active_loans), "#d97706")
        stat_card(cards, "Total Principal", f"Rs {total_loan_amount:,.0f}", "#dc2626")
        stat_card(cards, "Outstanding Balance", f"Rs {total_outstanding:,.0f}", "#ea580c")
        stat_card(cards, "Total Savings", f"Rs {total_savings:,.0f}", "#059669")

        # Loan table
        ctk.CTkLabel(self.content, text="Active Loans — Interest Summary",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=28, pady=(16, 4))

        cols = ("Member", "Current Principal (Rs)", "Original Principal (Rs)", "Interest Rate (%)", "Days", "Interest (Rs)", "Total Due (Rs)", "Paid (Rs)", "Balance (Rs)")
        tree_frame = ctk.CTkFrame(self.content)
        tree_frame.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        tree = self._make_tree(tree_frame, cols)

        for r in loans_data:
            waive_interest = r["notes"] and "INTEREST WAIVED" in r["notes"].upper()
            # Use loan's own interest rate if set, otherwise default to 10%
            interest_rate = r["interest_rate"] if r["interest_rate"] is not None else 10.0
            interest, days = calc_interest(r["principal"], r["issue_date"], as_of=calc_date, waive_interest=waive_interest, interest_rate=interest_rate)
            
            # Calculate current principal after reductions
            with get_db() as conn:
                principal_paid_result = conn.execute(
                    "SELECT COALESCE(SUM(principal_paid), 0) as principal_paid FROM repayments WHERE loan_id=?",
                    (r["id"],)
                ).fetchone()
                principal_paid = principal_paid_result["principal_paid"] if principal_paid_result else 0
                current_principal = r["principal"] - principal_paid
                
                # Get total paid amount for this loan
                paid_result = conn.execute(
                    "SELECT COALESCE(SUM(amount), 0) as total_paid FROM repayments WHERE loan_id=?",
                    (r["id"],)
                ).fetchone()
                total_paid = paid_result["total_paid"] if paid_result else 0
            
            total_due = current_principal + interest
            # Calculate interest paid so far
            interest_paid_result = conn.execute(
                "SELECT COALESCE(SUM(interest_paid), 0) as interest_paid FROM repayments WHERE loan_id=?",
                (r["id"],)
            ).fetchone()
            interest_paid = interest_paid_result["interest_paid"] if interest_paid_result else 0
            # Remaining balance = current principal + remaining interest
            remaining_interest = max(0, interest - interest_paid)
            remaining = current_principal + remaining_interest
            tree.insert("", "end", values=(
                r["name"], f"{current_principal:,.0f}", f"{r['principal']:,.0f}", f"{interest_rate:.2f}", days,
                f"{interest:,.2f}", f"{total_due:,.2f}", f"{total_paid:,.2f}", f"{remaining:,.2f}"))

        tree.pack(fill="both", expand=True, padx=4, pady=4)

    def _load_dashboard_data(self):
        """Reload dashboard data with custom date calculations"""
        self.show_dashboard()

    # ── Members ────────────────────────────────────────────────────────────────

    def show_members(self):
        self._clear_content()
        hrow = self._header("Members", "All registered members")

        btn_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        btn_frame.pack(fill="x", padx=24, pady=(0, 8))
        ctk.CTkButton(btn_frame, text="+ Add Member", width=140, command=self.add_member_dialog).pack(side="left")
        ctk.CTkButton(btn_frame, text="Delete Selected", width=140, command=self.delete_selected_member, fg_color="red").pack(side="left", padx=8)

        self.member_search = ctk.CTkEntry(btn_frame, placeholder_text="Search name...", width=220)
        self.member_search.pack(side="left", padx=10)
        self.member_search.bind("<KeyRelease>", lambda e: self._load_members())

        cols = ("ID", "Name", "Phone", "Address", "Joined", "Active Loans", "Total Savings")
        tf = ctk.CTkFrame(self.content)
        tf.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        self.member_tree = self._make_tree(tf, cols)
        self.member_tree.pack(fill="both", expand=True, padx=4, pady=4)
        self.member_tree.bind("<Return>", self.member_detail)

        self.member_editor = EditableTreeview(
            app=self,
            tree=self.member_tree,
            editable_cols={"Name", "Phone", "Address", "Joined"},
            validators={
                "Name": lambda v: v.strip() or (_ for _ in ()).throw(ValueError("Name required")),
                "Phone": lambda v: v.strip() if v.strip() == "" or v.strip().isdigit() else (_ for _ in ()).throw(ValueError("Phone must contain only numbers")),
                "Address": lambda v: v.strip(),
                "Joined": lambda v: parse_iso_date(v, "Joined date").isoformat(),
            },
            on_save=self._save_member_cell,
        )

        self._load_members()

    def _load_members(self):
        q = self.member_search.get() if hasattr(self, "member_search") else ""
        self.member_tree.delete(*self.member_tree.get_children())
        with get_db() as conn:
            rows = conn.execute(
                "SELECT m.id, m.name, m.phone, m.address, m.joined_date, m.is_active,"
                " (SELECT COUNT(*) FROM loans l WHERE l.member_id=m.id AND l.status='active') as loans,"
                " (SELECT COALESCE(SUM(s.amount),0) FROM savings s WHERE s.member_id=m.id) as savings"
                " FROM members m WHERE m.name LIKE ? ORDER BY m.name",
                (f"%{q}%",)).fetchall()
        for r in rows:
            self.member_tree.insert("", "end", iid=r["id"], values=(
                r["id"], r["name"], r["phone"] or "", r["address"] or "",
                r["joined_date"], r["loans"], f"Rs {r['savings']:,.0f}"))

    def add_member_dialog(self, member=None):
        d = ctk.CTkToplevel(self)
        d.title("Add Member" if not member else "Edit Member")
        d.geometry("420x360")
        d.grab_set()

        ctk.CTkLabel(d, text="Member Name *").pack(anchor="w", padx=24, pady=(20, 2))
        name_e = ctk.CTkEntry(d, width=360)
        name_e.pack(padx=24)

        ctk.CTkLabel(d, text="Phone (Numbers only)").pack(anchor="w", padx=24, pady=(10, 2))
        phone_e = ctk.CTkEntry(d, width=360)
        phone_e.pack(padx=24)
        
        # Phone number validation - only allow numbers
        def validate_phone_input(new_value):
            if new_value == "":  # Allow empty
                return True
            return new_value.isdigit()  # Only allow digits
        
        phone_vcmd = (d.register(validate_phone_input), '%P')
        phone_e.configure(validate="key", validatecommand=phone_vcmd)

        ctk.CTkLabel(d, text="Address").pack(anchor="w", padx=24, pady=(10, 2))
        addr_e = ctk.CTkEntry(d, width=360)
        addr_e.pack(padx=24)

        ctk.CTkLabel(d, text="Joined Date (YYYY-MM-DD)").pack(anchor="w", padx=24, pady=(10, 2))
        date_e = ctk.CTkEntry(d, width=360)
        date_e.insert(0, str(datetime.date.today()))
        date_e.pack(padx=24)

        if member:
            name_e.insert(0, member["name"])
            phone_e.insert(0, member["phone"] or "")
            addr_e.insert(0, member["address"] or "")
            date_e.delete(0, "end")
            date_e.insert(0, member["joined_date"])

        def save():
            save_btn.configure(state="disabled")
            name = name_e.get().strip()
            if not name:
                messagebox.showerror("Error", "Name is required", parent=d)
                save_btn.configure(state="normal")
                return
            try:
                joined_date = parse_iso_date(date_e.get(), "Joined date").isoformat()
            except ValueError:
                messagebox.showerror("Error", "Invalid date format", parent=d)
                save_btn.configure(state="normal")
                return
            try:
                with get_db() as conn:
                    if member:
                        conn.execute("UPDATE members SET name=?,phone=?,address=?,joined_date=? WHERE id=?",
                                     (name, phone_e.get().strip(), addr_e.get().strip(), joined_date, member["id"]))
                        log_action(self.username, "UPDATE", "members", member["id"], f"Updated {name}", conn=conn)
                    else:
                        cur = conn.execute("INSERT INTO members (name,phone,address,joined_date) VALUES (?,?,?,?)",
                                           (name, phone_e.get().strip(), addr_e.get().strip(), joined_date))
                        log_action(self.username, "INSERT", "members", cur.lastrowid, f"Added {name}", conn=conn)
            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"Could not save member.\n{e}", parent=d)
                save_btn.configure(state="normal")
                return
            d.destroy()
            self._load_members()

        save_btn = ctk.CTkButton(d, text="Save Member", command=save)
        save_btn.pack(pady=20)

    def member_detail(self, event):
        sel = self.member_tree.selection()
        if not sel: return
        mid = int(sel[0])
        with get_db() as conn:
            m = conn.execute("SELECT * FROM members WHERE id=?", (mid,)).fetchone()
        if not m: return

        d = ctk.CTkToplevel(self)
        d.title(f"Member: {m['name']}")
        d.geometry("620x500")
        d.grab_set()

        ctk.CTkLabel(d, text=m["name"], font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(16, 4))

        tabs = ctk.CTkTabview(d)
        tabs.pack(fill="both", expand=True, padx=16, pady=8)
        tabs.add("Loans")
        tabs.add("Savings")
        tabs.add("Edit")

        # Loans tab
        with get_db() as conn:
            loans = conn.execute(
                "SELECT * FROM loans WHERE member_id=? ORDER BY issue_date DESC", (mid,)).fetchall()
            sav = conn.execute(
                "SELECT * FROM savings WHERE member_id=? ORDER BY paid_date DESC", (mid,)).fetchall()

        lt = tabs.tab("Loans")
        lf = ctk.CTkFrame(lt)
        lf.pack(fill="both", expand=True)
        l_tree = self._make_tree(lf, ("Loan ID", "Principal", "Issue Date", "Status", "Interest", "Outstanding"))
        for loan in loans:
            interest_rate = loan["interest_rate"] if loan["interest_rate"] is not None else 10.0
            interest, _ = calc_interest(loan["principal"], loan["issue_date"], interest_rate=interest_rate)
            l_tree.insert("", "end", values=(
                loan["id"], f"Rs {loan['principal']:,.0f}", loan["issue_date"],
                loan["status"], f"Rs {interest:,.2f}", f"Rs {loan['principal']+interest:,.2f}"))
        l_tree.pack(fill="both", expand=True)

        # Savings tab
        st = tabs.tab("Savings")
        sf = ctk.CTkFrame(st)
        sf.pack(fill="both", expand=True)
        s_tree = self._make_tree(sf, ("ID", "Quarter", "Amount", "Date"))
        for s in sav:
            s_tree.insert("", "end", values=(s["id"], s["quarter"], f"Rs {s['amount']:,.0f}", s["paid_date"]))
        s_tree.pack(fill="both", expand=True)

        # Edit tab
        et = tabs.tab("Edit")
        ctk.CTkButton(et, text="Edit Member Info",
                      command=lambda: [d.destroy(), self.add_member_dialog(dict(m))]).pack(pady=20)
        ctk.CTkButton(et, text="Deactivate Member", fg_color="orange",
                      command=lambda: self._deactivate_member(mid, d)).pack(pady=5)
        ctk.CTkButton(et, text="Delete Member Permanently", fg_color="red",
                      command=lambda: self.delete_member_from_detail(mid, d)).pack(pady=5)

    def delete_member_from_detail(self, member_id, parent_dialog):
        # Get member info and check for dependencies
        with get_db() as conn:
            member = conn.execute("SELECT name FROM members WHERE id=?", (member_id,)).fetchone()
            if not member:
                messagebox.showerror("Error", "Member not found.", parent=parent_dialog)
                return
            
            # Check for active loans
            active_loans = conn.execute(
                "SELECT COUNT(*) FROM loans WHERE member_id=? AND status='active'", 
                (member_id,)
            ).fetchone()[0]
            
            # Check for any loans (including paid ones)
            total_loans = conn.execute(
                "SELECT COUNT(*) FROM loans WHERE member_id=?", 
                (member_id,)
            ).fetchone()[0]
            
            # Check for savings
            savings_count = conn.execute(
                "SELECT COUNT(*) FROM savings WHERE member_id=?", 
                (member_id,)
            ).fetchone()[0]
            
            # Check for repayments
            repayments_count = conn.execute(
                "SELECT COUNT(*) FROM repayments r JOIN loans l ON r.loan_id=l.id WHERE l.member_id=?", 
                (member_id,)
            ).fetchone()[0]
        
        # Build warning message
        warning_msg = f"Are you sure you want to permanently delete member '{member['name']}'?\n\n"
        warning_msg += "This will permanently remove all member data including:\n"
        
        if active_loans > 0:
            warning_msg += f"  - {active_loans} active loan(s)\n"
        if total_loans > 0:
            warning_msg += f"  - {total_loans} loan record(s)\n"
        if savings_count > 0:
            warning_msg += f"  - {savings_count} savings record(s)\n"
        if repayments_count > 0:
            warning_msg += f"  - {repayments_count} repayment record(s)\n"
        
        if active_loans > 0:
            warning_msg += "\n\nWARNING: This member has active loans! Deleting will remove all loan data."
        else:
            warning_msg += "\n\nThis action cannot be undone."
        
        if not messagebox.askyesno("Confirm Permanent Deletion", warning_msg, parent=parent_dialog):
            return
        
        # Perform deletion
        try:
            with get_db() as conn:
                # Delete related records in order due to foreign key constraints
                conn.execute("DELETE FROM repayments WHERE loan_id IN (SELECT id FROM loans WHERE member_id=?)", (member_id,))
                conn.execute("DELETE FROM loans WHERE member_id=?", (member_id,))
                conn.execute("DELETE FROM savings WHERE member_id=?", (member_id,))
                conn.execute("DELETE FROM members WHERE id=?", (member_id,))
                
                log_action(self.username, "DELETE_MEMBER", "members", member_id, 
                          f"Deleted member '{member['name']}' and all related data", conn=conn)
            
            parent_dialog.destroy()
            self._load_members()
            messagebox.showinfo("Success", f"Member '{member['name']}' and all related data have been permanently deleted.")
            
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Could not delete member.\n{e}", parent=parent_dialog)

    def delete_selected_member(self):
        sel = self.member_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a member to delete.")
            return
        
        member_id = int(sel[0])
        
        # Get member info and check for dependencies
        with get_db() as conn:
            member = conn.execute("SELECT name FROM members WHERE id=?", (member_id,)).fetchone()
            if not member:
                messagebox.showerror("Error", "Member not found.")
                return
            
            # Check for active loans
            active_loans = conn.execute(
                "SELECT COUNT(*) FROM loans WHERE member_id=? AND status='active'", 
                (member_id,)
            ).fetchone()[0]
            
            # Check for any loans (including paid ones)
            total_loans = conn.execute(
                "SELECT COUNT(*) FROM loans WHERE member_id=?", 
                (member_id,)
            ).fetchone()[0]
            
            # Check for savings
            savings_count = conn.execute(
                "SELECT COUNT(*) FROM savings WHERE member_id=?", 
                (member_id,)
            ).fetchone()[0]
            
            # Check for repayments (as a proxy for loan history)
            repayments_count = conn.execute(
                "SELECT COUNT(*) FROM repayments r JOIN loans l ON r.loan_id=l.id WHERE l.member_id=?", 
                (member_id,)
            ).fetchone()[0]
        
        # Build warning message
        warning_msg = f"Are you sure you want to delete member '{member['name']}'?\n\n"
        warning_msg += "This will permanently remove all member data including:\n"
        
        if active_loans > 0:
            warning_msg += f"  - {active_loans} active loan(s)\n"
        if total_loans > 0:
            warning_msg += f"  - {total_loans} loan record(s)\n"
        if savings_count > 0:
            warning_msg += f"  - {savings_count} savings record(s)\n"
        if repayments_count > 0:
            warning_msg += f"  - {repayments_count} repayment record(s)\n"
        
        if active_loans > 0:
            warning_msg += "\n\nWARNING: This member has active loans! Deleting will remove all loan data."
        else:
            warning_msg += "\n\nThis action cannot be undone."
        
        if not messagebox.askyesno("Confirm Permanent Deletion", warning_msg):
            return
        
        # Perform deletion with foreign key handling
        try:
            with get_db() as conn:
                # Delete related records in order due to foreign key constraints
                conn.execute("DELETE FROM repayments WHERE loan_id IN (SELECT id FROM loans WHERE member_id=?)", (member_id,))
                conn.execute("DELETE FROM loans WHERE member_id=?", (member_id,))
                conn.execute("DELETE FROM savings WHERE member_id=?", (member_id,))
                conn.execute("DELETE FROM members WHERE id=?", (member_id,))
                
                log_action(self.username, "DELETE_MEMBER", "members", member_id, 
                          f"Deleted member '{member['name']}' and all related data", conn=conn)
            
            self._load_members()
            messagebox.showinfo("Success", f"Member '{member['name']}' and all related data have been permanently deleted.")
            
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Could not delete member.\n{e}")

    def _deactivate_member(self, mid, parent):
        if messagebox.askyesno("Confirm", "Deactivate this member?", parent=parent):
            with get_db() as conn:
                conn.execute("UPDATE members SET is_active=0 WHERE id=?", (mid,))
                log_action(self.username, "DEACTIVATE", "members", mid, conn=conn)
            parent.destroy()
            self._load_members()

    # ── Loans ──────────────────────────────────────────────────────────────────

    def show_loans(self):
        self._clear_content()
        self._header("Loans", "All loan records")

        btn_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        btn_frame.pack(fill="x", padx=24, pady=(0, 8))
        ctk.CTkButton(btn_frame, text="+ Issue Loan", width=140, command=self.issue_loan_dialog).pack(side="left")
        ctk.CTkButton(btn_frame, text="💵 Record Repayment", width=180, command=self.repayment_dialog).pack(side="left", padx=8)

        self.loan_filter = ctk.CTkOptionMenu(btn_frame, values=["All", "Active", "Paid"], command=lambda _: self._load_loans())
        self.loan_filter.pack(side="left", padx=8)
        self.loan_filter.set("Active")
        
        # Add custom date selector for loan interest calculations
        ctk.CTkLabel(btn_frame, text="Calculate as of:", 
                     font=ctk.CTkFont(size=11)).pack(side="left", padx=(20, 5))
        
        self.loan_calc_date_var = ctk.StringVar(value=datetime.date.today().isoformat())
        self.loan_calc_date_entry = ctk.CTkEntry(btn_frame, textvariable=self.loan_calc_date_var, 
                                                 width=120, placeholder_text="YYYY-MM-DD")
        self.loan_calc_date_entry.pack(side="left", padx=(0, 5))
        
        ctk.CTkButton(btn_frame, text="Use Today", width=70,
                     command=lambda: self.loan_calc_date_var.set(datetime.date.today().isoformat())).pack(side="left", padx=(0, 5))
        
        ctk.CTkButton(btn_frame, text="Recalculate", width=80,
                     command=self._load_loans).pack(side="left")

        cols = ("Loan ID", "Member", "Loan #", "Current Principal (Rs)", "Original Principal (Rs)", "Interest Rate (%)", "Issue Date", "Days", "Interest (Rs)", "Total Due (Rs)", "Paid (Rs)", "Balance (Rs)", "Status")
        tf = ctk.CTkFrame(self.content)
        tf.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        self.loan_tree = self._make_tree(tf, cols)
        self.loan_tree.pack(fill="both", expand=True, padx=4, pady=4)
        self.loan_tree.bind("<Return>", self.loan_detail)

        self.loan_editor = EditableTreeview(
            app=self,
            tree=self.loan_tree,
            editable_cols={"Principal (Rs)", "Original Principal (Rs)", "Interest Rate (%)", "Issue Date", "Status"},
            validators={
                "Principal (Rs)": lambda v: f"{parse_positive_amount(v, 'Principal'):.0f}",
                "Original Principal (Rs)": lambda v: f"{parse_positive_amount(v, 'Original Principal'):.0f}",
                "Interest Rate (%)": lambda v: f"{float(v):.2f}" if v and v.replace('.', '', 1).isdigit() and float(v) >= 0 and float(v) <= 100 else (_ for _ in ()).throw(ValueError("Interest rate must be between 0 and 100")),
                "Issue Date": lambda v: parse_iso_date(v, "Issue date").isoformat(),
                "Status": lambda v: v.lower() if v.lower() in {"active", "paid"} else (_ for _ in ()).throw(ValueError("Status")),
            },
            on_save=self._save_loan_cell,
        )
        self._load_loans()

    def _load_loans(self):
        self.loan_tree.delete(*self.loan_tree.get_children())
        flt = getattr(self, "loan_filter", None)
        status_filter = flt.get() if flt else "Active"

        where = ""
        if status_filter == "Active": where = "AND l.status='active'"
        elif status_filter == "Paid": where = "AND l.status='paid'"

        # Get custom calculation date
        try:
            calc_date = datetime.date.fromisoformat(self.loan_calc_date_var.get())
        except (ValueError, AttributeError):
            calc_date = datetime.date.today()

        with get_db() as conn:
            rows = conn.execute(
                f"SELECT l.*, m.name FROM loans l JOIN members m ON l.member_id=m.id WHERE 1=1 {where} ORDER BY m.name, l.issue_date DESC"
            ).fetchall()

        # Track loan sequence numbers per member
        member_loan_count = {}
        for r in rows:
            member_id = r["member_id"]
            member_loan_count[member_id] = member_loan_count.get(member_id, 0) + 1
            
            waive_interest = r["notes"] and "INTEREST WAIVED" in r["notes"].upper()
            # Use loan's own interest rate if set, otherwise default to 10%
            interest_rate = r["interest_rate"] if r["interest_rate"] is not None else 10.0
            interest, days = calc_interest(r["principal"], r["issue_date"], as_of=calc_date, waive_interest=waive_interest, interest_rate=interest_rate)
            
            # Calculate current principal after reductions
            with get_db() as conn:
                principal_paid_result = conn.execute(
                    "SELECT COALESCE(SUM(principal_paid), 0) as principal_paid FROM repayments WHERE loan_id=?",
                    (r["id"],)
                ).fetchone()
                principal_paid = principal_paid_result["principal_paid"] if principal_paid_result else 0
                current_principal = r["principal"] - principal_paid
                
                # Calculate total paid amount for this loan
                paid_result = conn.execute(
                    "SELECT COALESCE(SUM(amount), 0) as total_paid FROM repayments WHERE loan_id=?",
                    (r["id"],)
                ).fetchone()
                total_paid = paid_result["total_paid"] if paid_result else 0
            
            total = current_principal + interest
            # Calculate interest paid so far
            interest_paid_result = conn.execute(
                "SELECT COALESCE(SUM(interest_paid), 0) as interest_paid FROM repayments WHERE loan_id=?",
                (r["id"],)
            ).fetchone()
            interest_paid = interest_paid_result["interest_paid"] if interest_paid_result else 0
            # Remaining balance = current principal + remaining interest
            remaining_interest = max(0, interest - interest_paid)
            remaining_balance = current_principal + remaining_interest
            tag = "paid" if r["status"] == "paid" else ("overdue" if days > 90 else "")
            self.loan_tree.insert("", "end", iid=r["id"], tags=(tag,), values=(
                r["id"], r["name"], f"#{member_loan_count[member_id]}", f"{current_principal:,.0f}", f"{r['principal']:,.0f}", f"{interest_rate:,.2f}", r["issue_date"],
                days, f"{interest:,.2f}", f"{total:,.2f}", f"{total_paid:,.2f}", 
                f"{remaining_balance:,.2f}", r["status"].upper()))

        self.loan_tree.tag_configure("paid", background="#d1fae5")
        self.loan_tree.tag_configure("overdue", background="#fee2e2")

    def issue_loan_dialog(self):
        d = ctk.CTkToplevel(self)
        d.title("Issue New Loan")
        d.geometry("440x400")
        d.grab_set()

        ctk.CTkLabel(d, text="Member *").pack(anchor="w", padx=24, pady=(20, 2))
        with get_db() as conn:
            members = conn.execute("SELECT id,name FROM members WHERE is_active=1 ORDER BY name").fetchall()
        member_names = [f"{m['id']} — {m['name']}" for m in members]
        if not member_names:
            messagebox.showwarning("No Members", "Please add an active member before issuing a loan.")
            d.destroy()
            return
        member_var = ctk.CTkOptionMenu(d, values=member_names, width=380)
        member_var.pack(padx=24)
        if member_names: member_var.set(member_names[0])

        ctk.CTkLabel(d, text="Loan Amount (Rs) *").pack(anchor="w", padx=24, pady=(12, 2))
        amount_e = ctk.CTkEntry(d, width=380)
        amount_e.pack(padx=24)
        amount_e.focus()

        ctk.CTkLabel(d, text="Interest Rate (%) *").pack(anchor="w", padx=24, pady=(12, 2))
        rate_e = ctk.CTkEntry(d, width=380)
        rate_e.insert(0, "10.0")
        rate_e.pack(padx=24)

        ctk.CTkLabel(d, text="Issue Date (YYYY-MM-DD) *").pack(anchor="w", padx=24, pady=(12, 2))
        date_e = ctk.CTkEntry(d, width=380)
        date_e.insert(0, str(datetime.date.today()))
        date_e.pack(padx=24)

        ctk.CTkLabel(d, text="Notes").pack(anchor="w", padx=24, pady=(12, 2))
        notes_e = ctk.CTkEntry(d, width=380)
        notes_e.pack(padx=24)

        waive_interest_var = ctk.CTkCheckBox(d, text="Waive Interest (Special Case)")
        waive_interest_var.pack(pady=4)

        def save():
            try:
                amount = parse_positive_amount(amount_e.get(), "Loan amount")
                issue_date = parse_iso_date(date_e.get(), "Issue date").isoformat()
                mid = int(member_var.get().split("—")[0].strip())
            except (ValueError, IndexError):
                messagebox.showerror("Error", "Check member, amount, and date values.", parent=d)
                return
            try:
                with get_db() as conn:
                    notes = notes_e.get().strip()
                    if waive_interest_var.get():
                        notes += " [INTEREST WAIVED]"
                    cur = conn.execute(
                        "INSERT INTO loans (member_id,principal,interest_rate,issue_date,notes) VALUES (?,?,?,?,?)",
                        (mid, amount, float(rate_e.get()), issue_date, notes))
                    log_action(self.username, "ISSUE_LOAN", "loans", cur.lastrowid,
                               f"Rs {amount} to member {mid}" + (" (Interest Waived)" if waive_interest_var.get() else ""), conn=conn)
            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"Could not issue loan.\n{e}", parent=d)
                return
            d.destroy()
            self._load_loans()
            messagebox.showinfo("Success", f"Loan of Rs {amount:,.0f} issued successfully.")

        ctk.CTkButton(d, text="Issue Loan", command=save).pack(pady=20)

    def repayment_dialog(self):
        sel = self.loan_tree.selection()
        loan_id = None
        if sel:
            loan_id = int(sel[0])

        d = ctk.CTkToplevel(self)
        d.title("Record Repayment")
        d.geometry("440x420")
        d.grab_set()

        ctk.CTkLabel(d, text="Loan ID *").pack(anchor="w", padx=24, pady=(20, 2))
        lid_e = ctk.CTkEntry(d, width=380)
        lid_e.pack(padx=24)
        if loan_id: lid_e.insert(0, str(loan_id))

        info_lbl = ctk.CTkLabel(d, text="", text_color="gray")
        info_lbl.pack(pady=4)

        principal_info_lbl = ctk.CTkLabel(d, text="", text_color="blue")
        principal_info_lbl.pack(pady=2)

        def load_info(*a):
            try:
                lid = int(lid_e.get().strip())
            except ValueError:
                info_lbl.configure(text="")
                principal_info_lbl.configure(text="")
                return
            try:
                with get_db() as conn:
                    loan = conn.execute(
                        "SELECT l.*,m.name FROM loans l JOIN members m ON l.member_id=m.id WHERE l.id=?",
                        (lid,)).fetchone()
            except sqlite3.Error:
                info_lbl.configure(text="Unable to load loan info right now.")
                principal_info_lbl.configure(text="")
                return
            if loan:
                waive_interest = loan["notes"] and "INTEREST WAIVED" in loan["notes"].upper()
                interest_rate = loan["interest_rate"] if loan["interest_rate"] is not None else 10.0
                interest, days = calc_interest(loan["principal"], loan["issue_date"], waive_interest=waive_interest, interest_rate=interest_rate)
                total_due = loan["principal"] + interest
                # Get total paid amount
                paid_result = conn.execute(
                    "SELECT COALESCE(SUM(amount), 0) as total_paid FROM repayments WHERE loan_id=?",
                    (lid,)
                ).fetchone()
                total_paid = paid_result["total_paid"] if paid_result else 0
                remaining = total_due - total_paid
                
                # Calculate principal paid so far
                principal_paid_result = conn.execute(
                    "SELECT COALESCE(SUM(principal_paid), 0) as principal_paid FROM repayments WHERE loan_id=?",
                    (lid,)
                ).fetchone()
                principal_paid = principal_paid_result["principal_paid"] if principal_paid_result else 0
                current_principal = loan["principal"] - principal_paid
                
                info_lbl.configure(text=f"{loan['name']} | Principal: Rs {loan['principal']:,.0f} | Interest: Rs {interest:,.2f} | Total Due: Rs {total_due:,.2f} | Already Paid: Rs {total_paid:,.2f} | Remaining: Rs {remaining:,.2f}")
                
                if principal_paid > 0:
                    principal_info_lbl.configure(text=f"Principal Reduction: Rs {principal_paid:,.2f} paid | Current Principal: Rs {current_principal:,.0f}")
                else:
                    principal_info_lbl.configure(text="No principal reduction yet - payments applied to interest first")
            else:
                info_lbl.configure(text="Loan ID not found.")
                principal_info_lbl.configure(text="")

        lid_e.bind("<FocusOut>", load_info)
        load_info()

        ctk.CTkLabel(d, text="Payment Amount (Rs) *").pack(anchor="w", padx=24, pady=(8, 2))
        amt_e = ctk.CTkEntry(d, width=380)
        amt_e.pack(padx=24)

        ctk.CTkLabel(d, text="Payment Date").pack(anchor="w", padx=24, pady=(8, 2))
        pdate_e = ctk.CTkEntry(d, width=380)
        pdate_e.insert(0, str(datetime.date.today()))
        pdate_e.pack(padx=24)

        ctk.CTkLabel(d, text="Notes").pack(anchor="w", padx=24, pady=(8, 2))
        notes_e = ctk.CTkEntry(d, width=380)
        notes_e.pack(padx=24)

        mark_paid_var = ctk.CTkCheckBox(d, text="Mark loan as fully PAID after this repayment")
        mark_paid_var.pack(pady=8)

        transfer_to_savings_var = ctk.CTkCheckBox(d, text="Add payment amount to member's savings")
        transfer_to_savings_var.pack(pady=4)

        def save():
            try:
                lid = int(lid_e.get().strip())
                amt = parse_positive_amount(amt_e.get(), "Payment amount")
                paid_date = parse_iso_date(pdate_e.get(), "Payment date").isoformat()
            except ValueError:
                messagebox.showerror("Error", "Check loan ID and amount", parent=d)
                return

            try:
                with get_db() as conn:
                    # Get loan details with member information
                    loan_info = conn.execute(
                        "SELECT l.principal, l.issue_date, l.status, l.member_id, m.name FROM loans l "
                        "JOIN members m ON l.member_id=m.id WHERE l.id=?", (lid,)
                    ).fetchone()
                    if not loan_info:
                        messagebox.showerror("Error", "Loan ID does not exist.", parent=d)
                        return
                    if loan_info["status"] == "paid":
                        messagebox.showerror("Error", "This loan is already marked as PAID.", parent=d)
                        return

                    waive_interest = False  # Check if loan has waived interest
                    loan_notes = conn.execute("SELECT notes FROM loans WHERE id=?", (lid,)).fetchone()
                    if loan_notes and loan_notes["notes"]:
                        waive_interest = "INTEREST WAIVED" in loan_notes["notes"].upper()
                    
                    # Get loan's interest rate
                    loan_rate_result = conn.execute("SELECT interest_rate FROM loans WHERE id=?", (lid,)).fetchone()
                    interest_rate = loan_rate_result["interest_rate"] if loan_rate_result else 10.0
                    interest, _ = calc_interest(loan_info["principal"], loan_info["issue_date"], waive_interest=waive_interest, interest_rate=interest_rate)
                    total_due = loan_info["principal"] + interest
                    total_paid = conn.execute(
                        "SELECT COALESCE(SUM(amount), 0) FROM repayments WHERE loan_id=?",
                        (lid,)
                    ).fetchone()[0]
                    remaining = round(total_due - total_paid, 2)
                    if amt > remaining:
                        messagebox.showerror(
                            "Payment Error",
                            f"Payment amount (Rs {amt:,.2f}) exceeds remaining balance (Rs {remaining:,.2f}).\n\nPlease enter an amount less than or equal to the remaining balance.",
                            parent=d
                        )
                        return

                    # Calculate principal reduction (payment amount minus interest portion)
                    if remaining > 0:
                        interest_portion = min(amt, interest)
                        principal_reduction = amt - interest_portion
                    else:
                        principal_reduction = 0

                    # Record the repayment
                    repayment_notes = notes_e.get().strip()
                    if transfer_to_savings_var.get():
                        repayment_notes += " [TRANSFERRED TO SAVINGS]"
                    
                    cur = conn.execute(
                        "INSERT INTO repayments (loan_id,amount,paid_date,principal_paid,interest_paid,notes) VALUES (?,?,?,?,?,?)",
                        (lid, amt, paid_date, principal_reduction, amt - principal_reduction, repayment_notes))
                    
                    # Do NOT update original principal in database - keep it constant
                    # Original principal remains Rs 50,000, only current_principal is calculated for display
                    # If principal is fully paid, mark loan as paid
                    if mark_paid_var.get() or abs(amt - remaining) < 0.005:
                        conn.execute("UPDATE loans SET status='paid' WHERE id=?", (lid,))

                    # Transfer payment amount to member's savings if requested
                    if transfer_to_savings_var.get():
                        quarter_code = f"{datetime.date.today().year}-Q{(datetime.date.today().month-1)//3+1}"
                        conn.execute(
                            "INSERT INTO savings (member_id, amount, quarter, paid_date, notes) VALUES (?,?,?,?,?)",
                            (loan_info["member_id"], amt, quarter_code, paid_date, f"Automatic transfer from loan repayment")
                        )
                        log_action(self.username, "AUTO_SAVINGS", "savings", 0, 
                                   f"Rs {amt} transferred to {loan_info['name']}'s savings from loan {lid}", conn=conn)

                    log_action(self.username, "REPAYMENT", "repayments", cur.lastrowid,
                               f"Rs {amt} for loan {lid}" + (f" (Principal reduced: Rs {principal_reduction:.2f})" if principal_reduction > 0 else ""), conn=conn)
            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"Could not record repayment.\n{e}", parent=d)
                return
            d.destroy()
            self._load_loans()
            messagebox.showinfo("Success", "Repayment recorded.")

        ctk.CTkButton(d, text="Record Repayment", command=save).pack(pady=14)

    def loan_detail(self, event):
        sel = self.loan_tree.selection()
        if not sel: return
        lid = int(sel[0])
        with get_db() as conn:
            loan = conn.execute(
                "SELECT l.*,m.name FROM loans l JOIN members m ON l.member_id=m.id WHERE l.id=?",
                (lid,)).fetchone()
            reps = conn.execute(
                "SELECT * FROM repayments WHERE loan_id=? ORDER BY paid_date", (lid,)).fetchall()
        if not loan: return

        waive_interest = loan["notes"] and "INTEREST WAIVED" in loan["notes"].upper()
        interest_rate = loan["interest_rate"] if loan["interest_rate"] is not None else 10.0
        interest, days = calc_interest(loan["principal"], loan["issue_date"], waive_interest=waive_interest, interest_rate=interest_rate)
        total_paid = sum(r["amount"] for r in reps)

        d = ctk.CTkToplevel(self)
        d.title(f"Loan #{lid} — {loan['name']}")
        d.geometry("560x480")
        d.grab_set()

        ctk.CTkLabel(d, text=f"Loan #{lid} — {loan['name']}",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(16, 8))

        info = ctk.CTkFrame(d)
        info.pack(fill="x", padx=20, pady=4)
        total_due = loan['principal']+interest
        remaining_balance = total_due - total_paid
        for label, val in [
            ("Principal:", f"Rs {loan['principal']:,.0f}"),
            ("Issue Date:", loan["issue_date"]),
            ("Days:", str(days)),
            ("Interest Rate (%):", f"{loan.get('interest_rate', 10.0):.2f}"),
            ("Total Due:", f"Rs {total_due:,.2f}"),
            ("Total Repaid:", f"Rs {total_paid:,.2f}"),
            ("Remaining Balance:", f"Rs {remaining_balance:,.2f}"),
            ("Status:", loan["status"].upper()),
        ]:
            r = ctk.CTkFrame(info, fg_color="transparent")
            r.pack(fill="x", pady=1)
            ctk.CTkLabel(r, text=label, width=180, anchor="w", text_color="gray").pack(side="left")
            ctk.CTkLabel(r, text=val, anchor="w").pack(side="left")

        ctk.CTkLabel(d, text="Repayment History", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(12, 4))
        rf = ctk.CTkFrame(d)
        rf.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        rt = self._make_tree(rf, ("Date", "Amount (Rs)", "Notes"))
        for rep in reps:
            rt.insert("", "end", values=(rep["paid_date"], f"{rep['amount']:,.0f}", rep["notes"] or ""))
        rt.pack(fill="both", expand=True)

    # ── Savings ────────────────────────────────────────────────────────────────

    def show_savings(self):
        self._clear_content()
        self._header("Savings", "Quarterly savings records")

        btn_f = ctk.CTkFrame(self.content, fg_color="transparent")
        btn_f.pack(fill="x", padx=24, pady=(0, 8))
        ctk.CTkButton(btn_f, text="+ Record Saving", command=self.record_saving_dialog).pack(side="left")
        ctk.CTkButton(btn_f, text="⚡ Quick Entry — All Members", width=220,
                      command=self.bulk_saving_dialog).pack(side="left", padx=8)

        cols = ("ID", "Member", "Quarter", "Amount (Rs)", "Date", "Notes")
        tf = ctk.CTkFrame(self.content)
        tf.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        self.sav_tree = self._make_tree(tf, cols)
        self.sav_tree.pack(fill="both", expand=True, padx=4, pady=4)
        self.savings_editor = EditableTreeview(
            app=self,
            tree=self.sav_tree,
            editable_cols={"Quarter", "Amount (Rs)", "Date", "Notes"},
            validators={
                "Quarter": lambda v: v.strip() or (_ for _ in ()).throw(ValueError("Quarter required")),
                "Amount (Rs)": lambda v: f"{parse_positive_amount(v, 'Saving amount'):.0f}",
                "Date": lambda v: parse_iso_date(v, "Saving date").isoformat(),
                "Notes": lambda v: v.strip(),
            },
            on_save=self._save_saving_cell,
        )
        self._load_savings()

    def _load_savings(self):
        self.sav_tree.delete(*self.sav_tree.get_children())
        with get_db() as conn:
            rows = conn.execute(
                "SELECT s.*,m.name FROM savings s JOIN members m ON s.member_id=m.id ORDER BY s.paid_date DESC"
            ).fetchall()
        for r in rows:
            self.sav_tree.insert("", "end", values=(r["id"], r["name"], r["quarter"],
                                                     f"{r['amount']:,.0f}", r["paid_date"], r["notes"] or ""))

    def record_saving_dialog(self):
        d = ctk.CTkToplevel(self)
        d.title("Record Saving")
        d.geometry("420x380")
        d.grab_set()

        ctk.CTkLabel(d, text="Member *").pack(anchor="w", padx=24, pady=(20, 2))
        with get_db() as conn:
            members = conn.execute("SELECT id,name FROM members WHERE is_active=1 ORDER BY name").fetchall()
        mnames = [f"{m['id']} — {m['name']}" for m in members]
        if not mnames:
            messagebox.showwarning("No Members", "Please add an active member before recording savings.")
            d.destroy()
            return
        mvar = ctk.CTkOptionMenu(d, values=mnames, width=370)
        mvar.pack(padx=24)

        ctk.CTkLabel(d, text="Quarter (e.g. 2082-Q1)").pack(anchor="w", padx=24, pady=(12, 2))
        q_e = ctk.CTkEntry(d, width=370)
        today = datetime.date.today()
        q_e.insert(0, f"{today.year}-Q{(today.month-1)//3+1}")
        q_e.pack(padx=24)

        ctk.CTkLabel(d, text="Amount (Rs)").pack(anchor="w", padx=24, pady=(12, 2))
        amt_e = ctk.CTkEntry(d, width=370)
        amt_e.insert(0, str(QUARTERLY_SAVING))
        amt_e.pack(padx=24)

        ctk.CTkLabel(d, text="Date").pack(anchor="w", padx=24, pady=(12, 2))
        date_e = ctk.CTkEntry(d, width=370)
        date_e.insert(0, str(today))
        date_e.pack(padx=24)

        def save():
            try:
                amt = parse_positive_amount(amt_e.get(), "Saving amount")
                paid_date = parse_iso_date(date_e.get(), "Saving date").isoformat()
                quarter = q_e.get().strip()
                if not quarter:
                    raise ValueError("Quarter is required")
                mid = int(mvar.get().split("—")[0].strip())
            except (ValueError, IndexError):
                messagebox.showerror("Error", "Check member, quarter, amount, and date.", parent=d)
                return
            try:
                with get_db() as conn:
                    cur = conn.execute(
                        "INSERT INTO savings (member_id,amount,quarter,paid_date) VALUES (?,?,?,?)",
                        (mid, amt, quarter, paid_date))
                    log_action(self.username, "SAVING", "savings", cur.lastrowid, conn=conn)
            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"Could not save record.\n{e}", parent=d)
                return
            d.destroy()
            self._load_savings()

        ctk.CTkButton(d, text="Save", command=save).pack(pady=20)

    def bulk_saving_dialog(self):
        d = ctk.CTkToplevel(self)
        d.title("Quick Entry — Record Savings for All Members")
        d.geometry("500x600")
        d.grab_set()

        today = datetime.date.today()
        ctk.CTkLabel(d, text="Quarter", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=16, pady=(16, 4), sticky="w")
        q_e = ctk.CTkEntry(d, width=150)
        q_e.insert(0, f"{today.year}-Q{(today.month-1)//3+1}")
        q_e.grid(row=0, column=1, padx=8, pady=(16, 4))

        ctk.CTkLabel(d, text="Date").grid(row=1, column=0, padx=16, pady=4, sticky="w")
        date_e = ctk.CTkEntry(d, width=150)
        date_e.insert(0, str(today))
        date_e.grid(row=1, column=1, padx=8, pady=4)

        ctk.CTkLabel(d, text="Default Amount").grid(row=2, column=0, padx=16, pady=4, sticky="w")
        def_amt = ctk.CTkEntry(d, width=150)
        def_amt.insert(0, str(QUARTERLY_SAVING))
        def_amt.grid(row=2, column=1, padx=8, pady=4)

        ctk.CTkLabel(d, text="Select members to record saving:", font=ctk.CTkFont(weight="bold")).grid(
            row=3, column=0, columnspan=2, padx=16, pady=(12, 4), sticky="w")

        with get_db() as conn:
            members = conn.execute("SELECT id,name FROM members WHERE is_active=1 ORDER BY name").fetchall()

        scrollframe = ctk.CTkScrollableFrame(d, height=280)
        scrollframe.grid(row=4, column=0, columnspan=2, padx=16, pady=4, sticky="nsew")

        checks = {}
        for m in members:
            var = ctk.CTkCheckBox(scrollframe, text=m["name"])
            var.pack(anchor="w", pady=2)
            checks[m["id"]] = var

        select_all_var = [False]
        def toggle_all():
            v = not select_all_var[0]
            select_all_var[0] = v
            for cb in checks.values():
                cb.select() if v else cb.deselect()
        ctk.CTkButton(d, text="Select / Deselect All", command=toggle_all).grid(row=5, column=0, padx=16, pady=8)

        def save():
            quarter = q_e.get().strip()
            try:
                if not quarter:
                    raise ValueError("Quarter is required")
                paid_date = parse_iso_date(date_e.get(), "Saving date").isoformat()
                amt = parse_positive_amount(def_amt.get(), "Default amount")
            except ValueError:
                messagebox.showerror("Error", "Check quarter, date, and amount values.", parent=d)
                return
            selected_ids = [mid for mid, cb in checks.items() if cb.get()]
            if not selected_ids:
                messagebox.showwarning("No Selection", "Select at least one member.", parent=d)
                return
            saved = 0
            try:
                with get_db() as conn:
                    for mid in selected_ids:
                        conn.execute("INSERT INTO savings (member_id,amount,quarter,paid_date) VALUES (?,?,?,?)",
                                     (mid, amt, quarter, paid_date))
                        saved += 1
                    log_action(self.username, "BULK_SAVING", "savings", 0, f"{saved} members, quarter {quarter}", conn=conn)
            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"Bulk saving failed.\n{e}", parent=d)
                return
            d.destroy()
            self._load_savings()
            messagebox.showinfo("Done", f"Saved Rs {amt:,.0f} for {saved} members.")

        ctk.CTkButton(d, text=f"✅ Record Saving for Selected", command=save).grid(row=5, column=1, padx=8, pady=8)
        d.grid_rowconfigure(4, weight=1)

    # ── Statement ──────────────────────────────────────────────────────────────

    def show_statement(self):
        build_statement_view(self)

    # ── Reports ────────────────────────────────────────────────────────────────

    def show_reports(self):
        self._clear_content()
        self._header("Reports", "Export and summaries")

        cards = ctk.CTkFrame(self.content, fg_color="transparent")
        cards.pack(fill="x", padx=24, pady=20)

        def rpt_card(title, desc, cmd, color="#1a7abf"):
            f = ctk.CTkFrame(cards, corner_radius=12)
            f.pack(side="left", expand=True, fill="both", padx=6)
            ctk.CTkLabel(f, text=title, font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=16, pady=(14, 4))
            ctk.CTkLabel(f, text=desc, text_color="gray", wraplength=160).pack(anchor="w", padx=16)
            ctk.CTkButton(f, text="Generate →", command=cmd, fg_color=color).pack(pady=14, padx=16, anchor="w")

        rpt_card("Active Loans Summary", "Excel report of all active loans with interest", self.export_active_loans)
        rpt_card("High-Value Borrowers", "Top borrowers by loan amount with balances", self.export_high_value_borrowers, "#dc2626")
        rpt_card("Member Savings Report", "Quarterly savings by member", self.export_savings_report, "#059669")
        rpt_card("Quarterly Statement", "Full quarter statement — loans + savings + totals", self.export_quarterly, "#7c3aed")

    def export_active_loans(self):
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment
        except:
            messagebox.showerror("Error", "openpyxl not installed")
            return

        path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                             filetypes=[("Excel", "*.xlsx")],
                                             initialfile="Active_Loans_Report.xlsx")
        if not path: return

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Active Loans"

        headers = ["Loan ID", "Member Name", "Principal (Rs)", "Issue Date", "Days", "Interest (Rs)", "Total Due (Rs)"]
        header_fill = PatternFill("solid", fgColor="1a7abf")
        header_font = Font(bold=True, color="FFFFFF")

        for c, h in enumerate(headers, 1):
            cell = ws.cell(1, c, h)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")

        with get_db() as conn:
            rows = conn.execute(
                "SELECT l.*,m.name FROM loans l JOIN members m ON l.member_id=m.id WHERE l.status='active' ORDER BY m.name"
            ).fetchall()

        for i, r in enumerate(rows, 2):
            interest_rate = r["interest_rate"] if r["interest_rate"] is not None else 10.0
            interest, days = calc_interest(r["principal"], r["issue_date"], interest_rate=interest_rate)
            ws.append([r["id"], r["name"], r["principal"], r["issue_date"], days, interest, r["principal"]+interest])

        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = max(len(str(col[0].value or "")) + 4, 14)

        wb.save(path)
        messagebox.showinfo("Exported", f"Saved to {path}")
        log_action(self.username, "EXPORT", "loans", 0, f"Active loans to {path}")

    def export_high_value_borrowers(self):
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment
        except:
            messagebox.showerror("Error", "openpyxl not installed")
            return

        path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                             filetypes=[("Excel", "*.xlsx")],
                                             initialfile="High_Value_Borrowers.xlsx")
        if not path: return

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "High-Value Borrowers"

        headers = ["Member Name", "Total Loans", "Total Principal (Rs)", "Total Interest (Rs)", "Total Due (Rs)", "Total Paid (Rs)", "Balance (Rs)", "Loan Details"]
        header_fill = PatternFill("solid", fgColor="dc2626")
        header_font = Font(bold=True, color="FFFFFF")

        for c, h in enumerate(headers, 1):
            cell = ws.cell(1, c, h)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")

        with get_db() as conn:
            # Get all loans with member info
            loans_data = conn.execute(
                """
                SELECT l.*, m.name 
                FROM loans l 
                JOIN members m ON l.member_id=m.id 
                WHERE l.status='active' 
                ORDER BY m.name, l.issue_date DESC
                """
            ).fetchall()

        # Group by member and calculate totals
        member_summary = {}
        for loan in loans_data:
            member_name = loan["name"]
            waive_interest = loan["notes"] and "INTEREST WAIVED" in loan["notes"].upper()
            interest_rate = loan["interest_rate"] if loan["interest_rate"] is not None else 10.0
            interest, days = calc_interest(loan["principal"], loan["issue_date"], waive_interest=waive_interest, interest_rate=interest_rate)
            total_due = loan["principal"] + interest
            
            # Get paid amount for this loan
            paid_result = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) as total_paid FROM repayments WHERE loan_id=?",
                (loan["id"],)
            ).fetchone()
            total_paid = paid_result["total_paid"] if paid_result else 0
            remaining = total_due - total_paid
            
            if member_name not in member_summary:
                member_summary[member_name] = {
                    "loan_count": 0,
                    "total_principal": 0,
                    "total_interest": 0,
                    "total_due": 0,
                    "total_paid": 0,
                    "balance": 0,
                    "loan_details": []
                }
            
            member_summary[member_name]["loan_count"] += 1
            member_summary[member_name]["total_principal"] += loan["principal"]
            member_summary[member_name]["total_interest"] += interest
            member_summary[member_name]["total_due"] += total_due
            member_summary[member_name]["total_paid"] += total_paid
            member_summary[member_name]["balance"] += remaining
            member_summary[member_name]["loan_details"].append(f"#{loan['id']}: Rs {loan['principal']:,.0f} ({loan['issue_date']})")

        # Sort by total principal descending
        sorted_members = sorted(member_summary.items(), key=lambda x: x[1]["total_principal"], reverse=True)

        # Write data
        for i, (member_name, data) in enumerate(sorted_members, 2):
            loan_details = " | ".join(data["loan_details"][:3])  # Show first 3 loans
            if len(data["loan_details"]) > 3:
                loan_details += f" (+{len(data['loan_details'])-3} more)"
            
            ws.append([
                member_name,
                data["loan_count"],
                data["total_principal"],
                data["total_interest"],
                data["total_due"],
                data["total_paid"],
                data["balance"],
                loan_details
            ])

        # Auto-adjust column widths
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = max(len(str(col[0].value or "")) + 4, 15)

        wb.save(path)
        messagebox.showinfo("Exported", f"Saved to {path}")
        log_action(self.username, "EXPORT", "loans", 0, f"High-value borrowers to {path}")

    def export_savings_report(self):
        try: import openpyxl
        except: messagebox.showerror("Error", "openpyxl not installed"); return

        path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                             filetypes=[("Excel", "*.xlsx")],
                                             initialfile="Savings_Report.xlsx")
        if not path: return
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Savings"
        ws.append(["Member", "Quarter", "Amount (Rs)", "Date"])
        with get_db() as conn:
            rows = conn.execute(
                "SELECT m.name, s.quarter, s.amount, s.paid_date FROM savings s JOIN members m ON s.member_id=m.id ORDER BY m.name, s.quarter"
            ).fetchall()
        for r in rows:
            ws.append([r["name"], r["quarter"], r["amount"], r["paid_date"]])
        wb.save(path)
        messagebox.showinfo("Exported", f"Saved to {path}")

    def export_quarterly(self):
        try: import openpyxl
        except: messagebox.showerror("Error", "openpyxl not installed"); return

        path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                             filetypes=[("Excel", "*.xlsx")],
                                             initialfile="Quarterly_Statement.xlsx")
        if not path: return
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Statement"
        ws.append(["S.N", "Name", "Principal", "Loan", "Days", "Interest", "3-Month Saving", "Total to Pay"])

        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT m.id, m.name,
                       l.principal,
                       l.issue_date,
                       COALESCE(s.total_savings, 0) AS total_savings
                FROM members m
                LEFT JOIN (
                    SELECT l1.member_id, l1.principal, l1.issue_date
                    FROM loans l1
                    WHERE l1.status = 'active'
                    AND l1.id = (
                        SELECT l2.id
                        FROM loans l2
                        WHERE l2.member_id = l1.member_id AND l2.status = 'active'
                        ORDER BY l2.issue_date, l2.id
                        LIMIT 1
                    )
                ) l ON l.member_id = m.id
                LEFT JOIN (
                    SELECT member_id, SUM(amount) AS total_savings
                    FROM savings
                    GROUP BY member_id
                ) s ON s.member_id = m.id
                WHERE m.is_active = 1
                ORDER BY m.name
                """
            ).fetchall()

        for i, r in enumerate(rows, 1):
            principal = r["principal"] or 0
            if r["issue_date"]:
                interest_rate = r["interest_rate"] if r["interest_rate"] is not None else 10.0
                interest, days = calc_interest(principal, r["issue_date"], interest_rate=interest_rate)
            else:
                interest, days = 0, 0
            ws.append([i, r["name"], principal, principal, days, interest, QUARTERLY_SAVING,
                       principal + interest + QUARTERLY_SAVING])

        wb.save(path)
        messagebox.showinfo("Exported", f"Saved to {path}")

    # ── Audit Log ──────────────────────────────────────────────────────────────

    def show_audit(self):
        self._clear_content()
        self._header("Audit Log", "All system actions recorded")

        cols = ("Timestamp", "User", "Action", "Table", "Record ID", "Details")
        tf = ctk.CTkFrame(self.content)
        tf.pack(fill="both", expand=True, padx=24, pady=(8, 20))
        tree = self._make_tree(tf, cols)
        tree.pack(fill="both", expand=True, padx=4, pady=4)

        with get_db() as conn:
            rows = conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 500").fetchall()
        for r in rows:
            tree.insert("", "end", values=(r["timestamp"], r["user"], r["action"],
                                           r["table_name"], r["record_id"], r["details"] or ""))

    # ── Settings ───────────────────────────────────────────────────────────────

    def show_settings(self):
        self._clear_content()
        self._header("Settings", "System configuration")

        f = ctk.CTkFrame(self.content, corner_radius=12)
        f.pack(padx=24, pady=16, fill="x")

        ctk.CTkLabel(f, text="Change Password", font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=20, pady=(16, 8))
        ctk.CTkLabel(f, text="Current password").pack(anchor="w", padx=20)
        cur_e = ctk.CTkEntry(f, show="●", width=300)
        cur_e.pack(anchor="w", padx=20, pady=(4, 8))
        ctk.CTkLabel(f, text="New password").pack(anchor="w", padx=20)
        new_e = ctk.CTkEntry(f, show="●", width=300)
        new_e.pack(anchor="w", padx=20, pady=(4, 8))
        ctk.CTkLabel(f, text="Confirm new password").pack(anchor="w", padx=20)
        conf_e = ctk.CTkEntry(f, show="●", width=300)
        conf_e.pack(anchor="w", padx=20, pady=(4, 12))

        msg_l = ctk.CTkLabel(f, text="", text_color="red")
        msg_l.pack(anchor="w", padx=20)

        def change_pw():
            with get_db() as conn:
                row = conn.execute("SELECT * FROM users WHERE username=?", (self.username,)).fetchone()
            if not row:
                msg_l.configure(text="User not found", text_color="red")
                return
            if not verify_password(cur_e.get(), row["password_hash"], row["password_salt"]):
                msg_l.configure(text="Current password is wrong", text_color="red")
                return
            if new_e.get() != conf_e.get():
                msg_l.configure(text="New passwords don't match", text_color="red")
                return
            if len(new_e.get()) < 6:
                msg_l.configure(text="Password must be at least 6 characters", text_color="red")
                return
            new_hash, new_salt = hash_pw_pbkdf2(new_e.get())
            with get_db() as conn:
                conn.execute(
                    "UPDATE users SET password_hash=?, password_salt=? WHERE username=?",
                    (new_hash, new_salt, self.username),
                )
                log_action(self.username, "CHANGE_PASSWORD", "users", 0, conn=conn)
            msg_l.configure(text="Password changed successfully!", text_color="green")

        ctk.CTkButton(f, text="Change Password", command=change_pw).pack(anchor="w", padx=20, pady=(8, 20))

        # Import from Excel
        f2 = ctk.CTkFrame(self.content, corner_radius=12)
        f2.pack(padx=24, pady=8, fill="x")
        ctk.CTkLabel(f2, text="Import Members from Excel", font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=20, pady=(16, 8))
        ctk.CTkLabel(f2, text="Excel must have a column called 'NAME OF MREMBER' or 'name'", text_color="gray").pack(anchor="w", padx=20)
        ctk.CTkButton(f2, text="📂 Import Excel Members", command=self.import_excel_members).pack(anchor="w", padx=20, pady=12)

        f3 = ctk.CTkFrame(self.content, corner_radius=12)
        f3.pack(padx=24, pady=8, fill="x")
        ctk.CTkLabel(f3, text="Database Backup / Restore", font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=20, pady=(16, 8))
        ctk.CTkLabel(f3, text=f"Storage path: {DB_PATH}", text_color="gray").pack(anchor="w", padx=20, pady=(0, 8))
        ctk.CTkButton(f3, text="Backup Database", command=self.backup_database).pack(anchor="w", padx=20, pady=(0, 8))
        ctk.CTkButton(f3, text="Restore Database", command=self.restore_database).pack(anchor="w", padx=20, pady=(0, 12))

        f4 = ctk.CTkFrame(self.content, corner_radius=12)
        f4.pack(padx=24, pady=8, fill="x")
        ctk.CTkLabel(f4, text="Excel Data Import", font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=20, pady=(16, 8))
        ctk.CTkLabel(f4, text="Import loan data from Excel files", text_color="gray").pack(anchor="w", padx=20)
        ctk.CTkButton(f4, text="Import Excel Loans", command=self.import_excel_loans).pack(anchor="w", padx=20, pady=12)

    def import_excel_members(self):
        path = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx *.xls")])
        if not path: return
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))

            header_row = None
            name_col_idx = None
            for i, row in enumerate(rows):
                for j, val in enumerate(row):
                    if isinstance(val, str) and ("NAME" in val.upper() or "MEMBER" in val.upper()):
                        header_row = i
                        name_col_idx = j
                        break
                if header_row is not None:
                    break

            if header_row is None or name_col_idx is None:
                messagebox.showerror("Error", "Could not find member name column")
                return

            names = []
            for row in rows[header_row + 1 :]:
                if name_col_idx >= len(row):
                    continue
                val = row[name_col_idx]
                if val is None:
                    continue
                n = str(val).strip()
                if n and not n.startswith("S.") and len(n) > 2:
                    names.append(n)

            added = 0
            with get_db() as conn:
                for name in names:
                    try:
                        conn.execute("INSERT INTO members (name) VALUES (?)", (name,))
                        added += 1
                    except: pass

                log_action(self.username, "IMPORT_EXCEL", "members", 0, f"{added} members imported", conn=conn)
            messagebox.showinfo("Done", f"Imported {added} members from Excel")
            if hasattr(self, "member_tree"): self._load_members()
        except Exception as e:
            messagebox.showerror("Import Error", str(e))

    def import_excel_loans(self):
        path = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx *.xls")])
        if not path: return
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            
            # Try to find the best sheet for loan data
            sheet_names = wb.sheetnames
            target_sheet = None
            
            # Look for sheets with loan data patterns
            for sheet_name in sheet_names:
                ws = wb[sheet_name]
                # Check first few rows for loan-related headers
                for row in ws.iter_rows(max_row=5, values_only=True):
                    if row and any(cell and ('LOAN' in str(cell).upper() or 'PRINCIPAL' in str(cell).upper() or 'NAME' in str(cell).upper()) for cell in row):
                        target_sheet = sheet_name
                        break
                if target_sheet:
                    break
            
            if not target_sheet:
                messagebox.showwarning("No Loan Data", "Could not find loan data in Excel file.")
                return
            
            ws = wb[target_sheet]
            rows = list(ws.iter_rows(values_only=True))
            
            # Find header row
            header_row = None
            name_col = principal_col = loan_col = interest_col = days_col = None
            
            for i, row in enumerate(rows):
                if not row: continue
                for j, cell in enumerate(row):
                    if cell and isinstance(cell, str):
                        cell_upper = cell.upper()
                        if 'NAME' in cell_upper and name_col is None:
                            name_col = j
                        elif 'PRINCIPAL' in cell_upper and principal_col is None:
                            principal_col = j
                        elif 'LOAN' in cell_upper and loan_col is None:
                            loan_col = j
                        elif 'INTEREST' in cell_upper or 'INTREST' in cell_upper:
                            interest_col = j
                        elif 'DAYS' in cell_upper:
                            days_col = j
                
                if name_col is not None and (principal_col is not None or loan_col is not None):
                    header_row = i
                    break
            
            if header_row is None:
                messagebox.showerror("Format Error", "Could not find loan data headers.")
                return
            
            # Process loan data
            imported_loans = []
            for row in rows[header_row + 1:]:
                if not row or not any(row):
                    continue
                
                name = row[name_col] if name_col < len(row) else ""
                principal = row[principal_col] if principal_col is not None and principal_col < len(row) else None
                loan_amount = row[loan_col] if loan_col is not None and loan_col < len(row) else None
                
                # Use whichever column has data
                amount = principal if principal and str(principal).strip() and str(principal) != '0' else loan_amount
                
                if name and amount:
                    try:
                        amount_val = float(str(amount).replace(',', '').strip())
                        if amount_val > 0:
                            imported_loans.append((name.strip(), amount_val))
                    except:
                        continue
            
            if not imported_loans:
                messagebox.showwarning("No Data", "No valid loan records found.")
                return
            
            # Show preview and confirm import
            preview_text = f"Found {len(imported_loans)} loan records:\n\n"
            preview_text += "Top 10 records:\n"
            for name, amount in imported_loans[:10]:
                preview_text += f"  {name}: Rs {amount:,.0f}\n"
            
            if len(imported_loans) > 10:
                preview_text += f"... and {len(imported_loans) - 10} more\n"
            
            if not messagebox.askyesno("Confirm Import", f"{preview_text}\n\nProceed with import?"):
                return
            
            # Import to database
            imported_count = 0
            with get_db() as conn:
                for name, amount in imported_loans:
                    # Find or create member
                    member = conn.execute("SELECT id FROM members WHERE name=?", (name,)).fetchone()
                    if not member:
                        # Create new member
                        cur = conn.execute("INSERT INTO members (name) VALUES (?)", (name,))
                        member_id = cur.lastrowid
                    else:
                        member_id = member["id"]
                    
                    # Create loan record
                    try:
                        conn.execute(
                            "INSERT INTO loans (member_id, principal, issue_date, status, notes) VALUES (?, ?, ?, ?, ?)",
                            (member_id, amount, datetime.date.today().isoformat(), 'active', 'Imported from Excel')
                        )
                        imported_count += 1
                    except sqlite3.IntegrityError:
                        # Skip duplicates
                        continue
                
                log_action(self.username, "IMPORT_EXCEL_LOANS", "loans", 0, f"{imported_count} loans imported", conn=conn)
            
            messagebox.showinfo("Import Complete", f"Successfully imported {imported_count} loan records.")
            if hasattr(self, '_load_loans'):
                self._load_loans()
                
        except Exception as e:
            messagebox.showerror("Import Error", str(e))

    # ── Helpers ────────────────────────────────────────────────────────────────

    def backup_database(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("SQLite DB", "*.db"), ("All Files", "*.*")],
            initialfile="saving_group_backup.db",
            initialdir=str(DATA_DIR),
        )
        if not path:
            return
        try:
            with get_db() as conn:
                bck = sqlite3.connect(path)
                with bck:
                    conn.backup(bck)
                bck.close()
                log_action(self.username, "BACKUP_DB", "app_meta", 0, path, conn=conn)
            messagebox.showinfo("Backup", f"Database backed up to:\n{path}")
        except sqlite3.Error as exc:
            messagebox.showerror("Backup Error", str(exc))

    def restore_database(self):
        source = filedialog.askopenfilename(filetypes=[("SQLite DB", "*.db"), ("All Files", "*.*")])
        if not source:
            return
        if not messagebox.askyesno("Confirm Restore", "Restore will overwrite current database data. Continue?"):
            return
        try:
            close_db()
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            target = sqlite3.connect(str(DB_PATH))
            src = sqlite3.connect(source)
            with target:
                src.backup(target)
            src.close()
            target.close()
            init_db()
            with get_db() as conn:
                log_action(self.username, "RESTORE_DB", "app_meta", 0, source, conn=conn)
            messagebox.showinfo("Restore", "Database restored successfully.")
        except sqlite3.Error as exc:
            messagebox.showerror("Restore Error", str(exc))

    def _save_member_cell(self, row_id, col_name, value):
        field_map = {
            "Name": "name",
            "Phone": "phone",
            "Address": "address",
            "Joined": "joined_date",
        }
        db_field = field_map.get(col_name)
        if not db_field:
            return False
        try:
            with get_db() as conn:
                conn.execute(f"UPDATE members SET {db_field}=? WHERE id=?", (value, int(row_id)))
                log_action(self.username, "INLINE_EDIT", "members", int(row_id), f"{db_field}={value}", conn=conn)
            self._load_members()
            return True
        except sqlite3.Error as exc:
            messagebox.showerror("Database Error", str(exc))
            return False

    def _save_loan_cell(self, row_id, col_name, value):
        field_map = {
            "Principal (Rs)": "principal",
            "Original Principal (Rs)": "principal",
            "Interest Rate (%)": "interest_rate",
            "Issue Date": "issue_date",
            "Status": "status",
        }
        db_field = field_map.get(col_name)
        if not db_field:
            return False
        try:
            if db_field == "principal" and col_name == "Principal (Rs)":
                save_val = float(value)
            elif db_field == "principal" and col_name == "Original Principal (Rs)":
                save_val = float(value)
            elif db_field == "interest_rate":
                save_val = float(value)
            else:
                save_val = value
            with get_db() as conn:
                conn.execute(f"UPDATE loans SET {db_field}=? WHERE id=?", (save_val, int(row_id)))
                log_action(self.username, "INLINE_EDIT", "loans", int(row_id), f"{db_field}={value}", conn=conn)
            self._load_loans()
            return True
        except sqlite3.Error as exc:
            messagebox.showerror("Database Error", str(exc))
            return False

    def _save_saving_cell(self, row_id, col_name, value):
        field_map = {
            "Quarter": "quarter",
            "Amount (Rs)": "amount",
            "Date": "paid_date",
            "Notes": "notes",
        }
        db_field = field_map.get(col_name)
        if not db_field:
            return False
        try:
            save_val = float(value) if db_field == "amount" else value
            with get_db() as conn:
                conn.execute(f"UPDATE savings SET {db_field}=? WHERE id=?", (save_val, int(row_id)))
                log_action(self.username, "INLINE_EDIT", "savings", int(row_id), f"{db_field}={value}", conn=conn)
            self._load_savings()
            return True
        except sqlite3.Error as exc:
            messagebox.showerror("Database Error", str(exc))
            return False

    def _make_tree(self, parent, cols):
        return make_tree(parent, cols, self._sort_tree)

    def _sort_tree(self, tree, col):
        data = [(tree.set(k, col), k) for k in tree.get_children("")]
        reverse = getattr(self, "_sort_reverse", {}).get((str(tree), col), False)
        try:
            data.sort(key=lambda x: float(x[0].replace(",", "").replace("Rs ", "")), reverse=reverse)
        except ValueError:
            try:
                data.sort(key=lambda x: datetime.date.fromisoformat(x[0]), reverse=reverse)
            except ValueError:
                data.sort(key=lambda x: x[0].lower(), reverse=reverse)
        if not hasattr(self, "_sort_reverse"):
            self._sort_reverse = {}
        self._sort_reverse[(str(tree), col)] = not reverse
        for i, (_, k) in enumerate(data):
            tree.move(k, "", i)

    def logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            close_db()
            self.destroy()
            start()

# ─── Entry Point ───────────────────────────────────────────────────────────────

def start():
    try:
        try:
            init_db()
        except sqlite3.DatabaseError as exc:
            messagebox.showerror(
                "Database Error",
                f"Could not open database safely.\nPath: {DB_PATH}\n\n{exc}\n\nUse Restore in Settings if needed.",
            )
            return
        login = LoginWindow()
        login.mainloop()
        if login.current_user:
            app = MainApp(login.current_user)
            app.mainloop()
    finally:
        close_db()

if __name__ == "__main__":
    start()
