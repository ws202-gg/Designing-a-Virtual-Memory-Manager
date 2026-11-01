"""II-4-15 Virtual Memory Manager — tkinter interactive UI (page/frame animation)."""
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from vmm import VMM, VMMError, load_store, parse_addresses, PAGE_SIZE

DEFAULT = "16916 62493 30198 53683 40185 28781 24462 48399 64815 18295 16916 62493"
COL = {"free": "#e5e7eb", "used": "#22a06b", "new": "#d9534f", "idle": "#cfd8ea"}
CELL_W, CELL_H, PER_ROW = 47, 40, 16


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("II-4-15 Virtual Memory Manager")
        self.vmm, self.addrs, self.pos, self.store, self.running = None, [], 0, None, False
        left = ttk.Frame(self, padding=8)
        left.grid(row=0, column=0, sticky="ns")
        ttk.Label(left, text="Логик хаягууд (зай/таслал/мөр)").pack(anchor="w")
        self.txt = tk.Text(left, width=30, height=8)
        self.txt.insert("1.0", DEFAULT)
        self.txt.pack()
        self.refs_v = tk.BooleanVar(value=False)
        ttk.Checkbutton(left, text="Reference string (page дугаар 0–255)", variable=self.refs_v,
                        command=self.setup).pack(anchor="w")
        ttk.Button(left, text="addresses.txt нээх", command=self.open_addr).pack(fill="x", pady=2)
        ttk.Button(left, text="BACKING_STORE.bin нээх", command=self.open_store).pack(fill="x")
        self.store_lbl = ttk.Label(left, text="Өгөгдөл: жишиг")
        self.store_lbl.pack(anchor="w")
        # examples/book/BACKING_STORE.bin байвал (сурах бичгийн файл) автоматаар ачаална
        book_store = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples", "book", "BACKING_STORE.bin")
        if os.path.exists(book_store):
            try:
                self.store = load_store(book_store)
                self.store_lbl.config(text="Өгөгдөл: BACKING_STORE.bin (номын)")
            except VMMError:
                pass
        self.frames_v, self.tlb_v = tk.StringVar(value="128"), tk.StringVar(value="16")
        self.pol_v, self.speed = tk.StringVar(value="FIFO"), tk.IntVar(value=400)
        for label, w in (("Frame (1–256)", ttk.Spinbox(left, from_=1, to=256, textvariable=self.frames_v)),
                         ("TLB хэмжээ", ttk.Spinbox(left, from_=1, to=64, textvariable=self.tlb_v)),
                         ("Replacement", ttk.Combobox(left, values=["FIFO", "LRU"], textvariable=self.pol_v, state="readonly")),
                         ("Хурд (мс/алхам)", ttk.Scale(left, from_=50, to=1500, variable=self.speed))):
            ttk.Label(left, text=label).pack(anchor="w")
            w.pack(fill="x")
        for text, cmd in (("Алхам", self.step), ("Анимейшн эхлүүлэх/зогсоох", self.toggle), ("Reset (тохиргоо шинэчлэх)", self.setup)):
            ttk.Button(left, text=text, command=cmd).pack(fill="x", pady=2)
        self.stats = ttk.Label(left, text="—", justify="left")
        self.stats.pack(anchor="w", pady=6)

        right = ttk.Frame(self, padding=8)
        right.grid(row=0, column=1, sticky="nsew")
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        holder = ttk.Frame(right)
        holder.pack(fill="x")
        # 256 frame = 16 мөр × 40px > 330px тул scrollbar-тай canvas
        self.canvas = tk.Canvas(holder, width=760, height=330, bg="white", highlightthickness=1)
        sb = ttk.Scrollbar(holder, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side="left", fill="x", expand=True)
        sb.pack(side="right", fill="y")
        self.addr_lbl = ttk.Label(right, text="Хаягийн задлал: —", font=("TkFixedFont", 10))
        self.addr_lbl.pack(anchor="w", pady=(4, 0))
        self.tlb_lbl = ttk.Label(right, text="TLB: —", wraplength=740)
        self.tlb_lbl.pack(anchor="w")
        cols = ("#", "Логик", "Page", "Offset", "Frame", "Физик", "Утга", "TLB", "Үр дүн")
        self.tree = ttk.Treeview(right, columns=cols, show="headings", height=9)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=110 if c == "Үр дүн" else 70, anchor="e")
        self.tree.pack(fill="both", expand=True)
        self.setup()

    def open_addr(self):
        p = filedialog.askopenfilename(filetypes=[("Text", "*.txt"), ("All", "*")])
        if not p:
            return
        try:
            with open(p, encoding="utf-8") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError) as e:
            return messagebox.showerror("Алдаа", f"Файлыг уншиж чадсангүй:\n{e}")
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", text)
        self.setup()

    def open_store(self):
        p = filedialog.askopenfilename(filetypes=[("Binary", "*.bin"), ("All", "*")])
        if p:
            try:
                self.store = load_store(p)
            except VMMError as e:
                return messagebox.showerror("Алдаа", str(e))
            self.store_lbl.config(text="Өгөгдөл: " + os.path.basename(p))
            self.setup()

    def setup(self):
        self.running = False
        addrs, errors = parse_addresses(self.txt.get("1.0", "end"), refs=self.refs_v.get())
        try:
            if errors:
                raise VMMError("Хаягийн алдаа:\n" + "\n".join(errors[:5]))
            if not addrs:
                raise VMMError("Хаягийн жагсаалт хоосон байна")
            self.vmm = VMM(int(self.frames_v.get()), self.pol_v.get(), int(self.tlb_v.get()), self.store)
        except ValueError as e:  # VMMError ба int() хоёулаа ValueError
            msg = str(e) if isinstance(e, VMMError) else "Frame болон TLB нь бүхэл тоо байх ёстой"
            return messagebox.showerror("Алдаа", msg)
        self.addrs, self.pos = addrs, 0
        self.tree.delete(*self.tree.get_children())
        self.addr_lbl.config(text="Хаягийн задлал: —")
        self.draw(None)

    def draw(self, r):
        self.canvas.delete("all")
        for i, (page, _, _) in enumerate(self.vmm.frames):
            x, y = 6 + (i % PER_ROW) * CELL_W, 6 + (i // PER_ROW) * CELL_H
            kind = "free" if page < 0 else ("idle" if not r or r.frame != i else ("new" if r.fault else "used"))
            outline = "#e0a100" if r and r.evicted_page >= 0 and r.frame == i else "#888"
            self.canvas.create_rectangle(x, y, x + 44, y + 36, fill=COL[kind], outline=outline, width=3 if outline != "#888" else 1)
            self.canvas.create_text(x + 22, y + 18, text=f"F{i}\n" + ("—" if page < 0 else f"P{page}"), font=("TkDefaultFont", 8))
        rows = (len(self.vmm.frames) + PER_ROW - 1) // PER_ROW
        total_h = 12 + rows * CELL_H
        self.canvas.configure(scrollregion=(0, 0, 760, total_h))
        if r and total_h > 330:  # идэвхтэй frame харагдахаар гүйлгэнэ
            row_y = (r.frame // PER_ROW) * CELL_H
            self.canvas.yview_moveto(max(0, row_y - 140) / total_h)
        self.tlb_lbl.config(text="TLB: " + ("  ".join(f"P{e[0]}→F{e[1]}" for e in self.vmm.tlb) or "(хоосон)"))
        v = self.vmm
        self.stats.config(text=f"Хандалт: {v.total}/{len(self.addrs)}\nPage fault: {v.faults} ({v.fault_rate:.1%})\nTLB hit: {v.tlb_hits} ({v.tlb_rate:.1%})\n"
                               "Ногоон=hit, улаан=fault, шар хүрээ=солигдсон")

    def step(self):
        if self.pos >= len(self.addrs):
            self.running = False
            return messagebox.showinfo("Дууслаа", "Бүх хаяг боловсруулагдлаа. Reset дарна уу.")
        r = self.vmm.access(self.addrs[self.pos])
        self.pos += 1
        res = ("FAULT" + (f" (−P{r.evicted_page})" if r.evicted_page >= 0 else "")) if r.fault else "OK"
        iid = self.tree.insert("", "end", values=(self.pos, r.address, r.page, r.offset, r.frame, r.physical, r.value, "hit" if r.tlb_hit else "miss", res))
        self.tree.see(iid)
        src = "TLB hit" if r.tlb_hit else ("page fault" if r.fault else "page table")
        self.addr_lbl.config(text=f"Хаягийн задлал: {r.address} → page {r.page}, offset {r.offset} → [{src}] "
                                  f"frame {r.frame} → физик {r.frame}×{PAGE_SIZE}+{r.offset} = {r.physical}")
        self.draw(r)

    def toggle(self):
        self.running = not self.running
        if self.running:
            self.tick()

    def tick(self):
        if self.running and self.pos < len(self.addrs):
            self.step()
            self.after(int(self.speed.get()), self.tick)
        else:
            self.running = False


if __name__ == "__main__":
    App().mainloop()
