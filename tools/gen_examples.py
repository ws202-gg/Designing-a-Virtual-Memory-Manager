"""examples/ доторх өөрсдийн туршилтын өгөгдлийг дахин үүсгэх скрипт (seed тогтмол тул үр дүн давтагдана).
examples/book/ дахь addresses.txt, BACKING_STORE.bin, correct.txt нь сурах бичгийн
албан ёсны файлууд (github.com/greggagne/osc10e, ch10) тул энэ скрипт тэдгээрт хүрэхгүй.

    python3 tools/gen_examples.py
"""
import os
import random

OUT = os.path.join(os.path.dirname(__file__), "..", "examples")


def write(name, nums, per_line=10):
    lines = [" ".join(str(n) for n in nums[i:i + per_line]) for i in range(0, len(nums), per_line)]
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def locality_addrs(n=1000, seed=2026):
    """Locality-тэй хаягууд: ажлын олонлог (working set) үе шаттай солигдоно.
    Үе бүрт ~12 page сонгож, хандалтын 90%-ийг тэдгээрт, 10%-ийг санамсаргүй page-д хийнэ."""
    rnd = random.Random(seed)
    out = []
    while len(out) < n:
        base = rnd.randrange(0, 256)
        ws = [(base + k * rnd.choice((1, 2, 3))) % 256 for k in range(12)]
        for _ in range(rnd.randint(60, 120)):
            page = rnd.choice(ws) if rnd.random() < 0.9 else rnd.randrange(256)
            out.append(page * 256 + rnd.randrange(256))
    return out[:n]


if __name__ == "__main__":
    write("addresses_1000_locality.txt", locality_addrs())
    # Сурах бичгийн 10.4-р хэсгийн reference string (3 frame: FIFO=15, LRU=12 fault)
    write("ref_textbook.txt", [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1], 20)
    # Belady-ийн аномали (FIFO: 3 frame=9, 4 frame=10 fault)
    write("ref_belady.txt", [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5], 20)
    # Захын утгууд: 0, хамгийн их 16 бит, 16 битээс дээш (зөвхөн доод 16 бит хэрэглэгдэнэ), 32 битийн max
    write("boundary.txt", [0, 255, 256, 65535, 65536, 65791, 4294967295], 20)
    with open(os.path.join(OUT, "bad_input.txt"), "w", encoding="utf-8") as f:
        f.write("16916 abc -5 3.14 99999999999 0x1F ²\n")
    open(os.path.join(OUT, "empty.txt"), "w").close()
    print("examples/ шинэчлэгдлээ")
