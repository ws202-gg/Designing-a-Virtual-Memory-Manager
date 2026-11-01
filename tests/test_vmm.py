import os, sys, tempfile, unittest, io
from contextlib import redirect_stdout, redirect_stderr
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from vmm import VMM, VMMError, parse_addresses, load_store
import cli


def wfile(path, data):
    mode = "wb" if isinstance(data, bytes) else "w"
    with open(path, mode) as f:
        f.write(data)


def faults(policy, frames, pages):
    m = VMM(frames, policy)
    for p in pages:
        m.access(p * 256)
    return m.faults


class T(unittest.TestCase):
    def test_translation(self):
        r = VMM().access(16916)
        self.assertEqual((r.page, r.offset, r.physical, r.fault), (66, 20, 20, True))

    def test_upper_bits_ignored(self):
        self.assertEqual(VMM().access(0xABCD0000 | 16916).page, 66)

    def test_tlb_hit(self):
        m = VMM(); m.access(16916)
        self.assertTrue(m.access(16916).tlb_hit)

    def test_fifo_vs_lru(self):
        self.assertEqual(faults("FIFO", 2, [0, 1, 0, 2, 1]), 3)
        self.assertEqual(faults("LRU", 2, [0, 1, 0, 2, 1]), 4)

    def test_single_frame(self):
        self.assertEqual(faults("LRU", 1, [0, 1, 0, 1]), 4)

    def test_same_page_repeated(self):
        self.assertEqual(faults("FIFO", 4, [5] * 10), 1)

    def test_eviction_clears_tlb(self):
        m = VMM(1, "FIFO"); m.access(0); m.access(256)
        self.assertFalse(m.access(0).tlb_hit)

    def test_signed_byte(self):
        s = bytearray(65536); s[5] = 200
        self.assertEqual(VMM(store=bytes(s)).access(5).value, -56)

    def test_bad_input(self):
        self.assertEqual(len(parse_addresses("1 abc 99999999999")[1]), 2)
        for kw in ({"frames": 0}, {"frames": 300}, {"policy": "X"}, {"tlb_size": 0}, {"store": b"x"}):
            with self.assertRaises(VMMError):
                VMM(**kw)

    def test_cli(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "a.txt")
        wfile(p, "16916 62493 16916")
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main([p, "--frames", "128"]), 0)
        self.assertIn("Page Faults = 2", out.getvalue())
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main([p + "x"]), 2)

    # ---- нэмэлт тестүүд ----
    def test_textbook_reference_string(self):
        # Silberschatz 10.4: 3 frame, FIFO=15, LRU=12 page fault
        ref = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1]
        self.assertEqual(faults("FIFO", 3, ref), 15)
        self.assertEqual(faults("LRU", 3, ref), 12)

    def test_belady_anomaly(self):
        ref = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
        self.assertEqual(faults("FIFO", 3, ref), 9)
        self.assertEqual(faults("FIFO", 4, ref), 10)   # frame нэмэхэд fault өсөв
        self.assertLessEqual(faults("LRU", 4, ref), faults("LRU", 3, ref))  # LRU-д аномали байхгүй

    def test_boundary_addresses(self):
        m = VMM()
        self.assertEqual((m.access(0).page, m.access(0).offset), (0, 0))
        r = m.access(65535)
        self.assertEqual((r.page, r.offset), (255, 255))
        self.assertEqual(m.access(65536).page, 0)          # 16 битээс дээш хасагдана
        self.assertEqual(m.access(0xFFFFFFFF).page, 255)

    def test_refs_mode(self):
        addrs, err = parse_addresses("0 5 255", refs=True)
        self.assertEqual((addrs, err), ([0, 1280, 65280], []))
        self.assertEqual(len(parse_addresses("256", refs=True)[1]), 1)

    def test_non_ascii_digits_rejected(self):
        addrs, err = parse_addresses("12 ² ٣")
        self.assertEqual((addrs, len(err)), ([12], 2))

    def test_no_free_frame_until_full(self):
        m = VMM(4, "LRU")
        for p in range(4):
            self.assertEqual(m.access(p * 256).evicted_page, -1)
        self.assertEqual(m.access(4 * 256).evicted_page, 0)

    def test_physical_address_in_range(self):
        m = VMM(16, "LRU")
        for a in range(0, 65536, 97):
            r = m.access(a)
            self.assertTrue(0 <= r.physical < 16 * 256)
            self.assertEqual(r.physical, r.frame * 256 + r.offset)

    def test_store_matches_physical_read(self):
        s = bytes(i % 128 for i in range(65536))
        m = VMM(8, "FIFO", store=s)
        for a in (16916, 62493, 30198):
            self.assertEqual(m.access(a).value, s[a & 0xFFFF])

    def test_cli_bad_and_empty_files(self):
        d = tempfile.mkdtemp()
        for name, body in (("bad.txt", "1 abc -5"), ("empty.txt", ""), ("bin.txt", None)):
            p = os.path.join(d, name)
            if body is None:
                wfile(p, b"\xff\xfe\x00")
            else:
                wfile(p, body)
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(cli.main([p]), 2)

    def test_physical_memory_holds_loaded_page(self):
        s = bytes((i * 7) & 255 for i in range(65536))
        m = VMM(2, "FIFO", store=s)
        for addr in (0x1234, 0x5678, 0x9ABC):          # 3 дахь нь P0x12-ийг гаргана
            r = m.access(addr)
            fr, pg = r.frame, r.page
            self.assertEqual(bytes(m.memory[fr * 256:(fr + 1) * 256]), s[pg * 256:(pg + 1) * 256])

    # ---- сурах бичгийн албан ёсны өгөгдөл (examples/book/) ----
    def test_book_how_to_begin(self):
        # Сурах бичгийн "How to begin" хэсэгт өгсөн 7 тоо
        for addr, page, off in ((1, 0, 1), (256, 1, 0), (32768, 128, 0), (32769, 128, 1),
                                (128, 0, 128), (65534, 255, 254), (33153, 129, 129)):
            r = VMM().access(addr)
            self.assertEqual((r.page, r.offset), (page, off), addr)

    def _book(self):
        b = os.path.join(os.path.dirname(__file__), "..", "examples", "book")
        paths = [os.path.join(b, n) for n in ("addresses.txt", "BACKING_STORE.bin", "correct.txt")]
        if not all(os.path.exists(p) for p in paths):
            self.skipTest("examples/book/ дахь номын файлууд алга")
        with open(paths[0]) as f:
            addrs = parse_addresses(f.read())[0]
        with open(paths[2]) as f:
            correct = f.read().splitlines()
        return addrs, load_store(paths[1]), correct

    def test_book_correct_txt_256_frames(self):
        addrs, store, correct = self._book()
        m = VMM(256, "FIFO", 16, store)
        out = []
        for a in addrs:
            r = m.access(a)
            out.append(f"Virtual address: {r.address} Physical address: {r.physical} Value: {r.value}")
        self.assertEqual(out, correct)                  # 1000/1000 мөр яг таарна
        self.assertEqual((m.faults, m.tlb_hits), (244, 54))

    def test_book_128_frames_values(self):
        addrs, store, correct = self._book()
        values = [int(line.split()[-1]) for line in correct]
        for policy, faults in (("FIFO", 538), ("LRU", 539)):
            m = VMM(128, policy, 16, store)
            self.assertEqual([m.access(a).value for a in addrs], values, policy)
            self.assertEqual(m.faults, faults)

    def test_cli_refs_flag(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "r.txt")
        wfile(p, "7 0 1 2 0 3 0 4 2 3 0 3 2 1 2 0 1 7 0 1")
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main([p, "--refs", "--frames", "3", "--policy", "LRU", "--summary"]), 0)
        self.assertIn("Page Faults = 12", out.getvalue())


if __name__ == "__main__":
    unittest.main()
