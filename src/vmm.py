from dataclasses import dataclass
import re

PAGE_SIZE = NUM_PAGES = MAX_FRAMES = 256


class VMMError(ValueError):
    """Хэрэглэгчид ойлгомжтой мэдээлэх алдаа."""


def parse_addresses(text, refs=False):
    """Текстээс хаягуудыг уншина.

    refs=False: тоо бүр 32 битийн логик хаяг (0..4294967295).
    refs=True : тоо бүр page-ийн дугаар (0..255) — reference string;
                хаяг = page * 256 болгон хөрвүүлнэ.
    Буцаах утга: (хаягууд, алдааны мессежүүд)
    """
    addrs, errors = [], []
    limit = NUM_PAGES - 1 if refs else 0xFFFFFFFF
    what = "page дугаар 0..255 байх ёстой" if refs else "32 битийн хязгаар 0..4294967295-аас хэтэрсэн"
    for i, tok in enumerate(t for t in re.split(r"[\s,]+", text) if t):
        # isascii(): "²", "٣" зэрэг тэмдэгт isdigit()-д True өгдөг тул шүүнэ
        if not (tok.isascii() and tok.isdigit()):
            errors.append(f'#{i + 1} "{tok}" сөрөг биш бүхэл тоо биш')
        elif int(tok) > limit:
            errors.append(f'#{i + 1} "{tok}" {what}')
        else:
            addrs.append(int(tok) * PAGE_SIZE if refs else int(tok))
    return addrs, errors


def make_store(seed=7):
    """BACKING_STORE.bin байхгүй үед ашиглах жишиг өгөгдөл."""
    return bytes((i * 31 + seed) & 255 for i in range(NUM_PAGES * PAGE_SIZE))


def load_store(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as e:
        raise VMMError(f"{path} файлыг уншиж чадсангүй: {e.strerror}")
    if len(data) != NUM_PAGES * PAGE_SIZE:
        raise VMMError(f"BACKING_STORE {NUM_PAGES * PAGE_SIZE} байт байх ёстой, одоо {len(data)}")
    return data


@dataclass
class Result:
    address: int
    page: int
    offset: int
    frame: int
    physical: int
    value: int
    tlb_hit: bool
    fault: bool
    evicted_page: int = -1


class VMM:
    def __init__(self, frames=256, policy="FIFO", tlb_size=16, store=None):
        if not isinstance(frames, int) or not 1 <= frames <= MAX_FRAMES:
            raise VMMError(f"Frame-ийн тоо 1..{MAX_FRAMES} хоорондох бүхэл тоо байх ёстой")
        if policy not in ("FIFO", "LRU"):
            raise VMMError("Replacement нь FIFO эсвэл LRU байх ёстой")
        if not isinstance(tlb_size, int) or tlb_size < 1:
            raise VMMError("TLB-ийн хэмжээ 1-ээс бага байж болохгүй")
        if store is not None and len(store) != NUM_PAGES * PAGE_SIZE:
            raise VMMError(f"BACKING_STORE {NUM_PAGES * PAGE_SIZE} байт байх ёстой")
        self.policy, self.tlb_size = policy, tlb_size
        self.store = store if store is not None else make_store()
        self.page_table = [-1] * NUM_PAGES
        self.memory = bytearray(frames * PAGE_SIZE)        # физик санах ой
        self.frames = [[-1, 0, 0] for _ in range(frames)]  # [page, loaded, used]
        self.tlb = []                                      # [page, frame, loaded, used]
        self.clock = self.total = self.faults = self.tlb_hits = 0

    def _victim(self, entries, loaded, used):
        key = loaded if self.policy == "FIFO" else used
        return min(range(len(entries)), key=lambda i: entries[i][key])

    def access(self, address):
        self.clock += 1
        t = self.clock
        a = address & 0xFFFF                      # баруун 16 бит
        page, offset = a >> 8, a & 0xFF
        tlb_hit = fault = False
        evicted = -1
        i = next((k for k, e in enumerate(self.tlb) if e[0] == page), -1)
        if i >= 0:
            tlb_hit, frame = True, self.tlb[i][1]
            self.tlb[i][3] = t
        else:
            frame = self.page_table[page]
            if frame < 0:                          # page fault
                fault = True
                frame = next((k for k, f in enumerate(self.frames) if f[0] < 0), -1)
                if frame < 0:
                    frame = self._victim(self.frames, 1, 2)
                    evicted = self.frames[frame][0]
                    self.page_table[evicted] = -1
                    self.tlb = [e for e in self.tlb if e[0] != evicted]
                # demand paging: backing store-оос 256 байтыг frame руу хуулна
                src, dst = page * PAGE_SIZE, frame * PAGE_SIZE
                self.memory[dst:dst + PAGE_SIZE] = self.store[src:src + PAGE_SIZE]
                self.frames[frame] = [page, t, t]
                self.page_table[page] = frame
            if len(self.tlb) >= self.tlb_size:
                self.tlb.pop(self._victim(self.tlb, 2, 3))
            self.tlb.append([page, frame, t, t])
        self.frames[frame][2] = t
        physical = frame * PAGE_SIZE + offset
        b = self.memory[physical]                  # утгыг физик санах ойгоос уншина
        self.total += 1
        self.faults += fault
        self.tlb_hits += tlb_hit
        return Result(address, page, offset, frame, physical,
                      b - 256 if b > 127 else b, tlb_hit, fault, evicted)

    @property
    def fault_rate(self):
        return self.faults / self.total if self.total else 0.0

    @property
    def tlb_rate(self):
        return self.tlb_hits / self.total if self.total else 0.0
