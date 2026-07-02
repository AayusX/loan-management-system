from tkinter import ttk


def make_tree(parent, cols, sort_callback):
    style = ttk.Style()
    style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
    style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    tree = ttk.Treeview(parent, columns=cols, show="headings", selectmode="browse")
    vsb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    vsb.pack(side="right", fill="y")
    hsb.pack(side="bottom", fill="x")

    for col in cols:
        tree.heading(col, text=col, command=lambda c=col: sort_callback(tree, c))
        tree.column(col, width=max(len(col) * 9, 80), anchor="center")
    return tree


class EditableTreeview:
    def __init__(self, app, tree, editable_cols, on_save, validators=None):
        self.app = app
        self.tree = tree
        self.editable_cols = set(editable_cols)
        self.on_save = on_save
        self.validators = validators or {}
        self.editor = None
        self.current = None
        tree.bind("<Double-1>", self._begin_edit, add="+")

    def _begin_edit(self, event):
        if self.editor is not None:
            self._cancel()
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        row_id = self.tree.identify_row(event.y)
        col_ref = self.tree.identify_column(event.x)
        if not row_id or not col_ref:
            return
        col_idx = int(col_ref[1:]) - 1
        col_name = self.tree["columns"][col_idx]
        if col_name not in self.editable_cols:
            return
        x, y, w, h = self.tree.bbox(row_id, col_ref)
        value = self.tree.set(row_id, col_name)
        self.editor = ttk.Entry(self.tree)
        self.editor.insert(0, value)
        self.editor.place(x=x, y=y, width=w, height=h)
        self.editor.focus_set()
        self.current = (row_id, col_name, value)
        self.editor.bind("<Return>", self._save)
        self.editor.bind("<Escape>", lambda _e: self._cancel())
        self.editor.bind("<FocusOut>", lambda _e: self._save())

    def _save(self, _event=None):
        if not self.editor or not self.current:
            return
        row_id, col_name, old_value = self.current
        new_value = self.editor.get().strip()
        if new_value == old_value:
            self._cancel()
            return
        validator = self.validators.get(col_name)
        if validator:
            try:
                new_value = validator(new_value)
            except ValueError as exc:
                self.app.bell()
                self._cancel()
                self.app.after(30, lambda: self.app.focus_force())
                return
        ok = self.on_save(row_id, col_name, new_value)
        if ok:
            self.tree.set(row_id, col_name, new_value)
        self._cancel()

    def _cancel(self):
        if self.editor is not None:
            self.editor.destroy()
        self.editor = None
        self.current = None
