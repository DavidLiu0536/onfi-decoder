# ONFI Decoder

> Python decoder for Open NAND Flash Interface (ONFI) bus traffic captured by logic analyzers.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests passing](https://img.shields.io/badge/tests-passing-brightgreen)](#testing)

When debugging NAND flash controllers (e.g. for U-disk / SSD firmware development), engineers commonly hook a logic analyzer onto the parallel ONFI bus between the controller and the NAND die. The captured signals (`CE#`, `CLE`, `ALE`, `WE#`, `RE#`, `R/B#`, `IO[7:0]`) carry rich information — but they're nearly unreadable as raw waveforms. **Sigrok / PulseView and Saleae Logic 2 ship dozens of decoders, but ONFI is conspicuously absent.**

This package fills that gap. It parses CSV captures and produces a clean, command-level decode of every operation on the bus — including command name, decoded address (Block / Page / Column), data direction & bytes, status register flags, and busy/ready transitions.

---

## Features

- ✅ **Async ONFI 1.x — 4.x** command set (50+ opcodes) with operation descriptions
- ✅ **Address decoding** — column / row / block / page split for Page Read / Program / Erase
- ✅ **Status register parsing** — bit-level breakdown (RDY, ARDY, FAIL, WP, …)
- ✅ **Read ID interpretation** — manufacturer lookup (Micron / Hynix / Samsung / Toshiba / SanDisk / …)
- ✅ **Busy / Ready tracking** via R/B# transitions
- ✅ **CLI tool** (`onfi-decode`) + Python API
- ✅ **JSON / text output** for piping into other tools
- ✅ **Timeline visualization** (matplotlib)
- ✅ Handles Saleae Logic 2 CSV format out of the box; extensible to Kingst / PulseView

---

## Installation

```bash
git clone https://github.com/DavidLiu0536/onfi-decoder.git
cd onfi-decoder
pip install -e .
```

Requires Python 3.8+ and `matplotlib`.

---

## Quick Start

### 1. Generate a sample capture (if you don't have one yet)

```bash
python examples/gen_sample_capture.py
```

This creates `examples/sample_capture.csv` containing simulated traffic for:
Reset → Read ID → Page Read → Page Program → Block Erase → Read Status.

### 2. Decode it

```bash
onfi-decode examples/sample_capture.csv
```

Output:

```
================================================================================
ONFI Decode Report
================================================================================
Commands  : 10
Data bytes: 23
────────────────────────────────────────────────────────────────────────────────
[    0.050 us] CMD  : 0xFF  RESET                     -- Reset the entire device
[    0.075 us] R/B# : BUSY (chip processing)
[    2.075 us] R/B# : READY
[    2.225 us] CMD  : 0x90  READ_ID                   -- Read manufacturer/device ID
[    2.300 us] ADDR : addr=0x00  (raw: 00)
[    2.900 us] DATA ←: 2C DC 90 95 06  (5 bytes)
           └─ Read ID: Mfr=0x2C (Micron / Crucial), Dev=0xDC, Int=0x90, ...
[    2.900 us] CMD  : 0x00  READ_PAGE                 -- Page read (1st cycle)
[    3.275 us] ADDR : COL=0x0010, ROW=0x010080 (Block=1026, Page=0)
[    3.350 us] CMD  : 0x30  READ_PAGE_CONFIRM         -- Page read confirm
[    3.375 us] R/B# : BUSY (chip processing)
[   28.375 us] R/B# : READY
[   28.985 us] DATA ←: DE AD BE EF 12 34 56 78  (8 bytes)
[   29.795 us] CMD  : 0x80  PROGRAM_PAGE
[   29.360 us] ADDR : COL=0x0000, ROW=0x020100 (Block=2052, Page=0)
[   29.795 us] DATA →: CA FE BA BE F0 0D C0 DE  (8 bytes)
...
[ 2230.620 us] DATA ←: E0  (1 bytes)
           └─ Status=0xE0: WP, RDY, ARDY
```

### 3. Get a timeline

```python
from onfi_decoder import OnfiDecoder
from onfi_decoder.visualize import plot_timeline

dec = OnfiDecoder()
dec.decode_csv('examples/sample_capture.csv')
plot_timeline(dec, 'timeline.png')
```

![Timeline](docs/timeline_example.png)

---

## CSV Format

Default: Saleae Logic 2 CSV export. Required columns (case-sensitive):

```
Time[s], CE#, CLE, ALE, WE#, RE#, R/B#, IO[7:0]
```

Where:
- `Time[s]` — timestamp in seconds (float)
- Single-bit pins (`CE#`, `CLE`, …) — `0` or `1`
- `IO[7:0]` — hex string (`0xAB`) or decimal

Other formats (Kingst, PulseView .sr) can be supported by adding a parser to `onfi_decoder/parsers/` (PRs welcome).

---

## Programmatic API

```python
from onfi_decoder import OnfiDecoder

dec = OnfiDecoder()
dec.decode_csv('capture.csv')

print(dec.stats())
# {'total_events': 28, 'commands_total': 10, 'data_bytes_total': 23,
#  'duration_us': 2230.62,
#  'commands_breakdown': {'RESET': 1, 'READ_ID': 1, 'READ_PAGE': 1, ...}}

for event in dec.events:
    if event.kind == 'CMD':
        print(event.raw['name'], event.raw['byte'])
```

---

## CLI

```
onfi-decode <csv> [-f text|json] [-o output.txt] [--stats]

Options:
  -f, --format text|json      Output format (default: text)
  -o, --output FILE           Write to file instead of stdout
  --stats                     Print decode statistics only (JSON)
```

Examples:

```bash
# Plain decoded log
onfi-decode capture.csv

# JSON output for downstream processing
onfi-decode capture.csv -f json -o decoded.json

# Just summary stats
onfi-decode capture.csv --stats
```

---

## Supported Commands

| Opcode | Name | Description |
|---|---|---|
| 0xFF | RESET | Reset the entire device |
| 0xFC | SYNC_RESET | Synchronous reset |
| 0x90 | READ_ID | Read manufacturer/device ID (5 bytes) |
| 0xEC | READ_PARAMETER_PAGE | Read parameter page (256 bytes) |
| 0xED | READ_UNIQUE_ID | Read unique ID |
| 0x70 | READ_STATUS | Read status register |
| 0x71 | READ_STATUS_ENH | Read status enhanced (LUN-aware) |
| 0x00 / 0x30 | READ_PAGE / CONFIRM | Page read sequence |
| 0x05 / 0xE0 | RANDOM_DATA_READ / CONFIRM | Random data read (within page) |
| 0x80 / 0x10 | PROGRAM_PAGE / CONFIRM | Page program sequence |
| 0x85 | RANDOM_DATA_INPUT | Random data input |
| 0x60 / 0xD0 | BLOCK_ERASE / CONFIRM | Block erase sequence |
| 0xEE / 0xEF | GET / SET FEATURES | Feature register access |
| 0x31 / 0x32 / 0x35 / 0x3F | READ_CACHE_* | Cache read variants |
| 0x15 / 0x11 / 0xD1 | Multi-plane / cache program & erase | |

See `onfi_decoder/commands.py` for the full table.

---

## Testing

```bash
python -m unittest discover tests/
```

```
test_known_opcodes ........................ ok
test_parse_status_fail .................... ok
test_parse_status_ready ................... ok
test_unknown_opcode ....................... ok
test_decode_runs_without_error ............ ok
test_expected_commands_detected ........... ok
test_read_id_data_count ................... ok

Ran 7 tests in 0.016s, OK.
```

---

## Use Cases

This decoder is designed for engineers and researchers working on:

- **NAND flash controller firmware** — verify correct command sequencing in ASIC/FPGA emulation
- **U-disk / SSD bring-up** — debug bus timing issues during board bring-up
- **Failure analysis** — reconstruct command history before a flash failure
- **Reverse engineering** — analyze proprietary controller behavior
- **Education** — teach NAND flash interface concepts with concrete examples

---

## Roadmap

- [ ] Parse Saleae `.sal` binary export directly (no CSV intermediate)
- [ ] Sigrok / PulseView Python decoder plugin
- [ ] NV-DDR (Source-Synchronous) interface support
- [ ] Parameter Page (256-byte) field-level decode (manufacturer string, page size, ECC, …)
- [ ] Multi-LUN / Multi-die transaction tracking
- [ ] Timing analysis (tWB, tR, tPROG, tBERS measurement)

---

## Contributing

PRs welcome. Particularly interested in:

- Real captures from various controllers / NAND chips (please scrub any proprietary data)
- Additional CSV format parsers
- Edge cases & ONFI 4.x extension commands

---

## License

MIT — see [LICENSE](LICENSE).

---

## Author

If this project saved you a debugging session, consider giving it a star ⭐ — it's the only feedback open-source authors get!

For commercial support / custom NAND protocol work / firmware consulting, please open a [GitHub issue](https://github.com/DavidLiu0536/onfi-decoder/issues) tagged `commercial` and we'll follow up via private channel.
