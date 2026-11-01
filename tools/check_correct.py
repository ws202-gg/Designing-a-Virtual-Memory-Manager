"""Програмын гаралтыг сурах бичгийн correct.txt-тэй мөр мөрөөр харьцуулна.

    python3 tools/check_correct.py                 # 256 frame (номын үндсэн тохиргоо)
    python3 tools/check_correct.py --frames 128 --policy LRU   # зөвхөн утгыг харьцуулна

256 frame үед "Virtual address / Physical address / Value" мөр бүрэн таарах ёстой.
Frame цөөн үед солилтоос болж физик хаяг өөр байх тул зөвхөн Value-г харьцуулна.
"""
import argparse
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
from vmm import VMM, VMMError, load_store, parse_addresses  # noqa: E402

BOOK = os.path.join(ROOT, "examples", "book")


def main(argv=None):
    p = argparse.ArgumentParser(description="correct.txt-тэй харьцуулах")
    p.add_argument("--frames", type=int, default=256)
    p.add_argument("--policy", choices=["FIFO", "LRU"], default="FIFO")
    p.add_argument("--tlb", type=int, default=16)
    a = p.parse_args(argv)
    try:
        with open(os.path.join(BOOK, "addresses.txt"), encoding="utf-8") as f:
            addrs = parse_addresses(f.read())[0]
        with open(os.path.join(BOOK, "correct.txt"), encoding="utf-8") as f:
            correct = f.read().splitlines()
        vmm = VMM(a.frames, a.policy, a.tlb, load_store(os.path.join(BOOK, "BACKING_STORE.bin")))
    except (OSError, VMMError) as e:
        print("Алдаа:", e, file=sys.stderr)
        return 2
    full = a.frames == 256
    bad = 0
    for i, (ad, exp) in enumerate(zip(addrs, correct), 1):
        r = vmm.access(ad)
        got = f"Virtual address: {r.address} Physical address: {r.physical} Value: {r.value}"
        ok = got == exp if full else got.split()[-1] == exp.split()[-1]
        if not ok:
            bad += 1
            if bad <= 5:
                print(f"#{i}: хүлээгдсэн «{exp}», гарсан «{got}»")
    what = "мөр" if full else "утга (Value)"
    print(f"{len(correct) - bad}/{len(correct)} {what} таарсан  "
          f"[frames={a.frames}, {a.policy}, TLB={a.tlb}]  "
          f"Page Faults = {vmm.faults}, TLB Hits = {vmm.tlb_hits}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
