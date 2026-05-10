"""ONFI bus decoder — converts logic analyzer captures to command sequences."""

import csv
from dataclasses import dataclass, field
from typing import Optional, List
from .commands import lookup_command, parse_status, MANUFACTURER_IDS


@dataclass
class DecodedEvent:
    time_us: float
    kind: str           # CMD / ADDR / DATA / R/B / CE
    raw: dict = field(default_factory=dict)

    def format(self) -> str:
        t = f"[{self.time_us:9.3f} us]"
        k = self.kind
        r = self.raw

        if k == "CMD":
            return f"{t} CMD  : 0x{r['byte']:02X}  {r['name']:<25} -- {r['desc']}"

        if k == "ADDR":
            raw_hex = ' '.join(f'{b:02X}' for b in r['bytes'])
            return f"{t} ADDR : {r['parsed']}  (raw: {raw_hex})"

        if k == "DATA":
            preview = ' '.join(f'{b:02X}' for b in r['bytes'][:16])
            more = f" ... +{len(r['bytes'])-16}B" if len(r['bytes']) > 16 else ""
            arrow = '←' if r['direction'] == 'read' else '→'
            base = f"{t} DATA {arrow}: {preview}{more}  ({len(r['bytes'])} bytes)"

            extras = []
            if r['direction'] == 'read' and len(r['bytes']) == 5:
                b = r['bytes']
                vendor = MANUFACTURER_IDS.get(b[0], 'unknown')
                extras.append(f"           └─ Read ID: Mfr=0x{b[0]:02X} ({vendor}), "
                             f"Dev=0x{b[1]:02X}, Int=0x{b[2]:02X}, "
                             f"PageSize=0x{b[3]:02X}, MultiPlane=0x{b[4]:02X}")
            if r['direction'] == 'read' and len(r['bytes']) == 1:
                s = r['bytes'][0]
                active = [f.get('name') for f in parse_status(s) if f.get('value')]
                extras.append(f"           └─ Status=0x{s:02X}: " +
                             (', '.join(active) if active else '(no flag set)'))
            return '\n'.join([base] + extras)

        if k == "R/B":
            return f"{t} R/B# : {r['note']}"
        if k in ("CE_SELECT", "CE_RELEASE"):
            return f"{t} CE#  : {r['note']}"
        return f"{t} {k}: {r}"


class OnfiDecoder:
    """State-machine decoder for ONFI parallel interface (Async mode).

    Expected CSV columns (Saleae Logic 2 export format):
        Time[s], CE#, CLE, ALE, WE#, RE#, R/B#, IO[7:0]
    """

    def __init__(self):
        self.events: List[DecodedEvent] = []
        self.last_cmd: Optional[int] = None
        self.expected_addr_bytes = 0
        self.collected_addrs: List[int] = []
        self.collected_data: List[int] = []
        self.data_direction: Optional[str] = None

    # ─── Context rules ────────────────────────────────────────
    def _setup_after_cmd(self, cmd: int) -> None:
        if cmd in (0x90, 0xEC, 0xED, 0xEE):
            self.expected_addr_bytes = 1
        elif cmd in (0x70, 0x71, 0x78):
            self.expected_addr_bytes = 0
        elif cmd in (0x00, 0x80, 0x05):
            self.expected_addr_bytes = 5
        elif cmd == 0x60:
            self.expected_addr_bytes = 3
        else:
            self.expected_addr_bytes = 0

    def _parse_addr_seq(self, cmd: Optional[int], addrs: List[int]) -> str:
        if cmd in (0x90, 0xEC, 0xED) and len(addrs) >= 1:
            return f"addr=0x{addrs[0]:02X}"
        if cmd in (0x00, 0x80) and len(addrs) == 5:
            col = addrs[0] | (addrs[1] << 8)
            row = addrs[2] | (addrs[3] << 8) | (addrs[4] << 16)
            page = row & 0x3F
            block = row >> 6
            return f"COL=0x{col:04X}, ROW=0x{row:06X} (Block={block}, Page={page})"
        if cmd == 0x60 and len(addrs) == 3:
            row = addrs[0] | (addrs[1] << 8) | (addrs[2] << 16)
            return f"ROW=0x{row:06X} (full block erase)"
        return ' '.join(f'0x{a:02X}' for a in addrs)

    # ─── Buffer flushing ──────────────────────────────────────
    def _flush_addr(self, t_us: float):
        if self.collected_addrs:
            self.events.append(DecodedEvent(
                time_us=t_us, kind='ADDR',
                raw={
                    'bytes': list(self.collected_addrs),
                    'parsed': self._parse_addr_seq(self.last_cmd, self.collected_addrs),
                }
            ))
            self.collected_addrs = []
            self.expected_addr_bytes = 0

    def _flush_data(self, t_us: float):
        if self.collected_data:
            self.events.append(DecodedEvent(
                time_us=t_us, kind='DATA',
                raw={
                    'bytes': list(self.collected_data),
                    'direction': self.data_direction,
                }
            ))
            self.collected_data = []

    # ─── Main decoding loop ───────────────────────────────────
    def decode_csv(self, path: str) -> None:
        with open(path) as f:
            reader = csv.reader(f)
            header = next(reader)
            ix = {c.strip(): i for i, c in enumerate(header)}
            req = ['Time[s]', 'CE#', 'CLE', 'ALE', 'WE#', 'RE#', 'R/B#', 'IO[7:0]']
            for c in req:
                if c not in ix:
                    raise ValueError(f"CSV missing column: {c}. Found: {list(ix.keys())}")

            t_i = ix['Time[s]']; ce_i = ix['CE#']; cle_i = ix['CLE']; ale_i = ix['ALE']
            we_i = ix['WE#'];    re_i = ix['RE#']; rb_i = ix['R/B#']; io_i = ix['IO[7:0]']

            prev_we = prev_re = prev_rb = prev_ce = 1

            for row in reader:
                t_us = float(row[t_i]) * 1e6
                ce, cle, ale = int(row[ce_i]), int(row[cle_i]), int(row[ale_i])
                we, re_ = int(row[we_i]), int(row[re_i])
                rb = int(row[rb_i])
                io_str = row[io_i].strip().lstrip('0x').lstrip('0X')
                io_val = int(io_str, 16) if io_str else 0

                # CE# edges
                if prev_ce == 0 and ce == 1:
                    self.events.append(DecodedEvent(t_us, 'CE_RELEASE', {'note': 'CE# released'}))
                if prev_ce == 1 and ce == 0:
                    self.events.append(DecodedEvent(t_us, 'CE_SELECT', {'note': 'CE# asserted'}))

                # R/B# edges
                if prev_rb == 1 and rb == 0:
                    self._flush_data(t_us)
                    self.events.append(DecodedEvent(t_us, 'R/B', {'note': 'BUSY (chip processing)'}))
                if prev_rb == 0 and rb == 1:
                    self.events.append(DecodedEvent(t_us, 'R/B', {'note': 'READY'}))

                # WE# rising edge = latch (cmd / addr / data write)
                if prev_we == 0 and we == 1 and ce == 0:
                    if cle == 1 and ale == 0:
                        self._flush_addr(t_us); self._flush_data(t_us)
                        name, desc = lookup_command(io_val)
                        self.events.append(DecodedEvent(
                            t_us, 'CMD', {'byte': io_val, 'name': name, 'desc': desc}))
                        self.last_cmd = io_val
                        self._setup_after_cmd(io_val)
                    elif cle == 0 and ale == 1:
                        self.collected_addrs.append(io_val)
                        if self.expected_addr_bytes and len(self.collected_addrs) >= self.expected_addr_bytes:
                            self._flush_addr(t_us)
                    elif cle == 0 and ale == 0:
                        self.collected_data.append(io_val)
                        self.data_direction = 'write'

                # RE# falling edge = data read
                if prev_re == 1 and re_ == 0 and ce == 0 and cle == 0 and ale == 0:
                    self.collected_data.append(io_val)
                    self.data_direction = 'read'

                prev_we, prev_re, prev_rb, prev_ce = we, re_, rb, ce

            self._flush_addr(t_us); self._flush_data(t_us)

    # ─── Output ──────────────────────────────────────────────
    def report_text(self) -> str:
        lines = ["=" * 80, "ONFI Decode Report", "=" * 80]
        cmd_count = sum(1 for e in self.events if e.kind == 'CMD')
        data_total = sum(len(e.raw.get('bytes', [])) for e in self.events if e.kind == 'DATA')
        lines.append(f"Commands  : {cmd_count}")
        lines.append(f"Data bytes: {data_total}")
        lines.append("─" * 80)
        for e in self.events:
            lines.append(e.format())
        return '\n'.join(lines)

    def stats(self) -> dict:
        cmd_breakdown = {}
        for e in self.events:
            if e.kind == 'CMD':
                name = e.raw.get('name', 'UNKNOWN')
                cmd_breakdown[name] = cmd_breakdown.get(name, 0) + 1
        return {
            'total_events': len(self.events),
            'commands_total': sum(1 for e in self.events if e.kind == 'CMD'),
            'data_bytes_total': sum(len(e.raw.get('bytes', [])) for e in self.events if e.kind == 'DATA'),
            'duration_us': self.events[-1].time_us if self.events else 0,
            'commands_breakdown': cmd_breakdown,
        }
