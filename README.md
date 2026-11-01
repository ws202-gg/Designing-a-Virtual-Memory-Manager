# II-4-15 — Designing a Virtual Memory Manager

**F.CSM302 Үйлдлийн систем • Бие даалт 1 • Хуваарилалтын код: II-4-15**
Silberschatz, *Operating System Concepts* 10th ed., Бүлэг 10 — Programming Project.

## Зорилго
Логик хаягийг TLB (16) болон page table ашиглан физик хаяг руу хөрвүүлэх, page fault гарвал demand paging хийх (backing store-оос 256 байтыг физик санах ойн frame руу хуулах), санах ой дүүрэхэд FIFO/LRU-гаар page солих. Ажиллагааг **page/frame animation** бүхий interactive UI-гаар алхамчлан харуулна.

## Quick Start
```bash
git clone https://github.com/ws202-gg/Designing-a-Virtual-Memory-Manager.git
cd Designing-a-Virtual-Memory-Manager
python3 src/gui.py                                   # interactive UI (номын BACKING_STORE.bin автоматаар ачаалагдана)
python3 tools/check_correct.py                       # → 1000/1000 мөр correct.txt-тэй таарсан
python3 src/cli.py examples/book/addresses.txt --store examples/book/BACKING_STORE.bin --frames 128 --policy LRU
python3 src/cli.py examples/ref_textbook.txt --refs --frames 3 --policy FIFO --summary   # → Page Faults = 15
python3 src/experiment.py examples/addresses_1000_locality.txt                             # FIFO vs LRU хүснэгт
python3 -m unittest discover tests -v                                                      # 24 тест
```
Шаардлага: Python 3.10+, tkinter (Linux: `sudo apt install python3-tk`). Өөр dependency байхгүй.

## Боломжууд
- Хаяг эсвэл **reference string** (page дугаар 0–255) оролт, файлаас ачаалах
- Frame 1–256, TLB хэмжээ, FIFO/LRU, `BACKING_STORE.bin` сонгох; Reset
- Frame grid (hit = ногоон, fault = улаан, солилт = шар хүрээ), TLB-ийн төлөв, хаягийн задлал, хандалтын хүснэгт, статистик
- Буруу/захын оролтод ойлгомжтой алдааны мессеж (CLI exit code 2)

## Бүтэц
| Зам | Агуулга |
|---|---|
| `src/vmm.py` | Цөм: `VMM` (TLB, page table, физик санах ой, FIFO/LRU), `parse_addresses`, `load_store` |
| `src/cli.py` | Консол (номын гаралтын формат) |
| `src/gui.py` | tkinter page/frame animation |
| `src/experiment.py` | Frame × policy туршилт, CSV |
| `tests/test_vmm.py` | 24 unit test (номын `correct.txt`-тэй харьцуулах тестийг оруулаад) |
| `tools/check_correct.py` | Гаралтыг номын `correct.txt`-тэй мөр бүрээр харьцуулна |
| `tools/gen_examples.py` | Өөрсдийн туршилтын өгөгдлийг seed=2026-аар дахин үүсгэнэ |
| `examples/book/` | Сурах бичгийн албан ёсны `addresses.txt`, `BACKING_STORE.bin`, `correct.txt` |
| `examples/` | addresses (10), locality-тэй 1000 хаяг, номын reference string, Belady, boundary, bad input, empty |
| `docs/` | `II-4-15_BD1_Report.pdf`, `II-4-15_Manual.pdf`, `img/`, `results/*.csv`, `latex/` |

## Гол үр дүн
| Туршилт | FIFO | LRU |
|---|---|---|
| Номын `addresses.txt`, 256 frame | `correct.txt`-тэй 1000/1000 ✔ (244 fault, 54 TLB hit) | 1000/1000 ✔ (244 fault, 55 TLB hit) |
| Номын `addresses.txt`, 128 frame | утга 1000/1000 ✔, 538 fault | утга 1000/1000 ✔, 539 fault |
| Номын reference string, 3 frame | 15 fault | 12 fault ✔ номтой таарсан |
| Belady (1 2 3 4 1 2 5 1 2 3 4 5), 3 → 4 frame | 9 → 10 | 10 → 8 |
| 1000 хаяг (locality), 16 frame | 27.7% | 22.6% |

## Гишүүд
Шалгасан багш: Г.Ганбат /F.CS10/

| Гишүүн | Оюутны код |
|---|---|
| Э.Мөнх-Оргил | B242270130 |
| Д.Ундармаа | B242270044 |
| В.Хүсэлбилэг | B241910007 |
| С.Сүхбат | B241940044 |
| М.Хатансайхан | B231940049 |

## Бэлэн код, сан, AI ашиглалт
- Зөвхөн Python стандарт сан ашигласан. Тайлангийн графикийг `docs/results/*.csv`-ээс LaTeX (pgfplots)-оор зурсан.
- `examples/book/` дахь `addresses.txt`, `BACKING_STORE.bin`, `correct.txt` нь сурах бичгийн албан ёсны файлууд: <https://github.com/greggagne/osc10e> (`ch10`).
- Код засвар, нэмэлт тест, туршилтын скрипт, тайлан болон Manual-ын ноорог бэлдэхэд **Claude (Anthropic) AI туслах** ашигласан. Бүх үр дүнг баг өөрөө ажиллуулж шалгасан.
- CLI-д `--store` өгөхгүй бол програм жишиг өгөгдөл (`make_store`) ашиглана.
