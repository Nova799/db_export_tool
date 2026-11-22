"""Sortable Treeview helper."""

def enable_sorting(tree, columns):
    """Make treeview columns sortable by clicking on headers."""
    sort_state = {c: False for c in columns}

    def sort_by(col):
        try:
            data = [(tree.set(k, col), k) for k in tree.get_children("")]
        except Exception:
            return
        def key(item):
            v = item[0]
            if v is None:
                return (2, "")
            try:
                return (0, float(v))
            except (ValueError, TypeError):
                return (1, str(v).lower())
        data.sort(key=key, reverse=sort_state[col])
        for idx, (_, k) in enumerate(data):
            tree.move(k, "", idx)
        sort_state[col] = not sort_state[col]
        for c in columns:
            arrow = ""
            if c == col:
                arrow = " ▼" if sort_state[col] else " ▲"
            tree.heading(c, text=str(c) + arrow)

    for col in columns:
        tree.heading(col, command=lambda c=col: sort_by(c))
        tree.heading(col, text=str(col))


def center_window(win, parent=None):
    """Center a Toplevel window on its parent (or screen)."""
    win.update_idletasks()
    if parent is None:
        parent = win.master
    try:
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
    except Exception:
        px, py, pw, ph = 0, 0, win.winfo_screenwidth(), win.winfo_screenheight()
    w = win.winfo_width()
    h = win.winfo_height()
    x = px + (pw - w) // 2
    y = py + (ph - h) // 2
    win.geometry(f"+{max(0,x)}+{max(0,y)}")
