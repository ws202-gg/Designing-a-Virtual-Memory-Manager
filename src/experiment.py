"""Туршилт: frame-ийн тоо ба replacement-ийг өөрчлөн page fault / TLB hit rate-ийг хэмжинэ.

Жишээ:
    python3 src/experiment.py examples/addresses_1000_locality.txt
    python3 src/experiment.py examples/addresses_1000_locality.txt --frames 8 16 32 64 128 --csv out.csv
    python3 src/experiment.py examples/ref_belady.txt --refs --frames 1 2 3 4 5 6 --tlb 16
"""
import argparse
import csv
import sys
from vmm import VMM, VMMError, parse_addresses


def run(addrs, frames, policy, tlb):
    m = VMM(frames, policy, tlb)
    for a in addrs:
        m.access(a)
    return m


def main(argv=None):
    p = argparse.ArgumentParser(description="FIFO vs LRU туршилт")
    p.add_argument("addresses")
    p.add_argument("--refs", action="store_true", help="тоо бүр page дугаар")
    p.add_argument("--frames", type=int, nargs="+", default=[8, 16, 32, 64, 128, 256])
    p.add_argument("--tlb", type=int, default=16)
    p.add_argument("--csv", help="үр дүнг CSV файлд хадгалах")
    a = p.parse_args(argv)
    try:
        with open(a.addresses, encoding="utf-8") as f:
            addrs, errors = parse_addresses(f.read(), refs=a.refs)
        if errors:
            raise VMMError("Хаягийн алдаа: " + "; ".join(errors[:5]))
        if not addrs:
            raise VMMError("Хаягийн файл хоосон байна")
        rows = []
        for fr in a.frames:
            for pol in ("FIFO", "LRU"):
                m = run(addrs, fr, pol, a.tlb)
                rows.append((fr, pol, m.total, m.faults, round(m.fault_rate, 4), m.tlb_hits, round(m.tlb_rate, 4)))
    except OSError as e:
        print(f"Алдаа: файлыг нээж чадсангүй ({e.strerror})", file=sys.stderr)
        return 2
    except VMMError as e:
        print("Алдаа:", e, file=sys.stderr)
        return 2
    head = ("frames", "policy", "total", "faults", "fault_rate", "tlb_hits", "tlb_rate")
    print("{:>6} {:>6} {:>6} {:>7} {:>10} {:>8} {:>8}".format(*head))
    for r in rows:
        print("{:>6} {:>6} {:>6} {:>7} {:>10.3f} {:>8} {:>8.3f}".format(*r))
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(head)
            w.writerows(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
