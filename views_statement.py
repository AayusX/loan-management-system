import datetime
from tkinter import messagebox

import customtkinter as ctk

from db import get_db, log_action
from services import calc_interest, parse_iso_date, parse_positive_amount, quarter_code_for_date
from ui_tables import EditableTreeview

STATEMENT_COLS = (
    "क्रस",
    "कर्मचारीको नामथर",
    "जम्मा ऋण",
    "कुल ऋण",
    "दिन",
    "यस त्रैमासिक मा बुझाउने किस्ता",
    "यस त्रैमासिकमा बुझाउन पर्ने ब्याज",
    "किस्ता + ब्याज",
    "बाँकी रहने ऋण",
    "यस त्रैमासिकमा बुझाउन पर्ने रकम",
)


def _to_float(value):
    return float(str(value).replace(",", "").replace("Rs", "").strip() or 0)


def _safe_positive(value):
    return f"{parse_positive_amount(value, 'Value'):.2f}"


def ensure_period(period_code, as_of_date):
    with get_db() as conn:
        row = conn.execute("SELECT id FROM statement_periods WHERE period_code=?", (period_code,)).fetchone()
        if row:
            return row["id"]
        cur = conn.execute(
            "INSERT INTO statement_periods (period_code, title, as_of_date) VALUES (?,?,?)",
            (period_code, f"Statement {period_code}", as_of_date),
        )
        return cur.lastrowid


def recompute_statement_rows(period_id, as_of_date):
    as_of = parse_iso_date(as_of_date, "As of date")
    with get_db() as conn:
        members = conn.execute(
            "SELECT id, name FROM members WHERE is_active=1 ORDER BY name"
        ).fetchall()
        conn.execute("DELETE FROM statement_rows WHERE period_id=?", (period_id,))
        for idx, m in enumerate(members, start=1):
            loans = conn.execute(
                "SELECT id, principal, interest_rate, issue_date FROM loans WHERE member_id=? AND status='active' ORDER BY issue_date",
                (m["id"],),
            ).fetchall()
            total_loan_issued = sum(float(r["principal"]) for r in loans)
            if loans:
                earliest = min(datetime.date.fromisoformat(r["issue_date"]) for r in loans)
                days = max((as_of - earliest).days, 0)
            else:
                days = 0
            interest_due = sum(calc_interest(float(r["principal"]), r["issue_date"], as_of=as_of, interest_rate=r["interest_rate"] if r["interest_rate"] is not None else 10.0)[0] for r in loans)
            installment = sum(
                conn.execute(
                    "SELECT COALESCE(SUM(amount), 0) FROM repayments WHERE loan_id=? AND paid_date<=?",
                    (r["id"], as_of.isoformat()),
                ).fetchone()[0]
                for r in loans
            )
            total_loan = max(total_loan_issued, 0.0)
            installment_plus_interest = installment + interest_due
            remaining_loan = max(total_loan_issued - installment, 0.0)
            amount_payable = installment_plus_interest
            conn.execute(
                """
                INSERT INTO statement_rows (
                    period_id, member_id, sn, member_name, total_loan_issued, total_loan,
                    days, installment_this_quarter, interest_due_this_quarter,
                    installment_plus_interest, remaining_loan, amount_payable_this_quarter, remarks
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    period_id,
                    m["id"],
                    idx,
                    m["name"],
                    round(total_loan_issued, 2),
                    round(total_loan, 2),
                    days,
                    round(installment, 2),
                    round(interest_due, 2),
                    round(installment_plus_interest, 2),
                    round(remaining_loan, 2),
                    round(amount_payable, 2),
                    "",
                ),
            )


def build_statement_view(app):
    app._clear_content()
    app._header("Statement", "मूल ढाँचाअनुसार ऋण हिसाब")

    top = ctk.CTkFrame(app.content, fg_color="transparent")
    top.pack(fill="x", padx=24, pady=(0, 8))

    ctk.CTkLabel(top, text="हिसाब मिति (YYYY-MM-DD)").pack(side="left")
    app.statement_date = ctk.CTkEntry(top, width=130)
    app.statement_date.insert(0, str(datetime.date.today()))
    app.statement_date.pack(side="left", padx=8)

    def regenerate():
        try:
            as_of_date = parse_iso_date(app.statement_date.get(), "As of date").isoformat()
            period_code = quarter_code_for_date(datetime.date.fromisoformat(as_of_date))
            period_id = ensure_period(period_code, as_of_date)
            recompute_statement_rows(period_id, as_of_date)
            app._current_statement_period_id = period_id
            _load_statement_rows(app)
            with get_db() as conn:
                log_action(app.username, "REGENERATE_STATEMENT", "statement_rows", period_id, period_code, conn=conn)
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    ctk.CTkButton(top, text="पुनः गणना", command=regenerate).pack(side="left", padx=8)

    tf = ctk.CTkFrame(app.content)
    tf.pack(fill="both", expand=True, padx=24, pady=(0, 20))
    app.statement_tree = app._make_tree(tf, STATEMENT_COLS)
    app.statement_tree.pack(fill="both", expand=True, padx=4, pady=4)

    app.statement_editor = EditableTreeview(
        app=app,
        tree=app.statement_tree,
        editable_cols={
            "यस त्रैमासिक मा बुझाउने किस्ता",
            "यस त्रैमासिकमा बुझाउन पर्ने ब्याज",
        },
        validators={
            "यस त्रैमासिक मा बुझाउने किस्ता": _safe_positive,
            "यस त्रैमासिकमा बुझाउन पर्ने ब्याज": _safe_positive,
        },
        on_save=lambda row_id, col, val: _save_statement_cell(app, row_id, col, val),
    )
    regenerate()


def _save_statement_cell(app, row_id, col_name, value):
    period_id = getattr(app, "_current_statement_period_id", None)
    if not period_id:
        return False
    col_map = {
        "यस त्रैमासिक मा बुझाउने किस्ता": "installment_this_quarter",
        "यस त्रैमासिकमा बुझाउन पर्ने ब्याज": "interest_due_this_quarter",
    }
    db_col = col_map.get(col_name)
    if not db_col:
        return False
    try:
        with get_db() as conn:
            conn.execute(f"UPDATE statement_rows SET {db_col}=?, updated_at=datetime('now') WHERE id=?", (value, int(row_id)))
            if db_col in {"installment_this_quarter", "interest_due_this_quarter"}:
                row = conn.execute(
                    "SELECT installment_this_quarter, interest_due_this_quarter FROM statement_rows WHERE id=?",
                    (int(row_id),),
                ).fetchone()
                total = float(row["installment_this_quarter"]) + float(row["interest_due_this_quarter"])
                conn.execute(
                    "UPDATE statement_rows SET installment_plus_interest=?, amount_payable_this_quarter=?, remaining_loan=max(total_loan-?,0) WHERE id=?",
                    (total, total, float(row["installment_this_quarter"]), int(row_id)),
                )
            log_action(app.username, "EDIT_STATEMENT_CELL", "statement_rows", int(row_id), f"{col_name}={value}", conn=conn)
        _load_statement_rows(app)
        return True
    except Exception as exc:
        messagebox.showerror("Error", str(exc))
        return False


def _load_statement_rows(app):
    app.statement_tree.delete(*app.statement_tree.get_children())
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, sn, member_name, total_loan_issued, total_loan, days,
                   installment_this_quarter, interest_due_this_quarter,
                   installment_plus_interest, remaining_loan, amount_payable_this_quarter
            FROM statement_rows
            WHERE period_id=?
            ORDER BY sn
            """,
            (app._current_statement_period_id,),
        ).fetchall()
    for r in rows:
        app.statement_tree.insert(
            "",
            "end",
            iid=r["id"],
            values=(
                r["sn"],
                r["member_name"],
                f"{r['total_loan_issued']:.2f}",
                f"{r['total_loan']:.2f}",
                r["days"],
                f"{r['installment_this_quarter']:.2f}",
                f"{r['interest_due_this_quarter']:.2f}",
                f"{r['installment_plus_interest']:.2f}",
                f"{r['remaining_loan']:.2f}",
                f"{r['amount_payable_this_quarter']:.2f}",
            ),
        )
