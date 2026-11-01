"""II-4-15 Virtual Memory Manager — консол хувилбар.

Жишээ:
    python3 src/cli.py examples/addresses.txt
    python3 src/cli.py examples/addresses_1000.txt --frames 128 --policy LRU
    python3 src/cli.py examples/ref_textbook.txt --refs --frames 3 --policy FIFO
"""
import argparse
import sys
from vmm import VMM, VMMError, load_store, parse_addresses


def main(argv=None):
    p = argparse.ArgumentParser(description="Virtual Memory Manager (II-4-15)")
    p.add_argument("addresses", help="логик хаяг (эсвэл --refs үед page дугаар) агуулсан файл")
    p.add_argument("--store", help="BACKING_STORE.bin (байхгүй бол жишиг өгөгдөл)")
    p.add_argument("--frames", type=int, default=256, help="физик frame-ийн тоо 1..256 (анхдагч 256)")
    p.add_argument("--policy", choices=["FIFO", "LRU"], default="FIFO", help="page replacement (анхдагч FIFO)")
    p.add_argument("--tlb", type=int, default=16, help="TLB-ийн хэмжээ (анхдагч 16)")
    p.add_argument("--refs", action="store_true", help="файлын тоо бүрийг page дугаар гэж үзэх (reference string)")
    p.add_argument("--summary", action="store_true", help="зөвхөн статистик хэвлэх")
    a = p.parse_args(argv)
    try:
        with open(a.addresses, encoding="utf-8") as f:
            text = f.read()
        addrs, errors = parse_addresses(text, refs=a.refs)
        if errors:
            more = f" (+{len(errors) - 5} бусад)" if len(errors) > 5 else ""
            raise VMMError("Хаягийн алдаа: " + "; ".join(errors[:5]) + more)
        if not addrs:
            raise VMMError("Хаягийн файл хоосон байна")
        store = load_store(a.store) if a.store else None
        vmm = VMM(a.frames, a.policy, a.tlb, store)
        if store is None:
            print("Анхааруулга: BACKING_STORE өгөөгүй тул жишиг өгөгдөл ашиглав", file=sys.stderr)
    except OSError as e:
        print(f"Алдаа: {a.addresses} файлыг нээж чадсангүй ({e.strerror})", file=sys.stderr)
        return 2
    except UnicodeDecodeError:
        print(f"Алдаа: {a.addresses} текст (UTF-8) файл биш байна", file=sys.stderr)
        return 2
    except VMMError as e:
        print("Алдаа:", e, file=sys.stderr)
        return 2
    for ad in addrs:
        r = vmm.access(ad)
        if not a.summary:
            print(f"Virtual address: {r.address} Physical address: {r.physical} Value: {r.value}")
    print(f"Number of Translated Addresses = {vmm.total}")
    print(f"Page Faults = {vmm.faults}")
    print(f"Page Fault Rate = {vmm.fault_rate:.3f}")
    print(f"TLB Hits = {vmm.tlb_hits}")
    print(f"TLB Hit Rate = {vmm.tlb_rate:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
