"""Generate a synthetic logic-analyzer CSV simulating typical ONFI traffic."""

import csv
import os

HEADER = ['Time[s]', 'CE#', 'CLE', 'ALE', 'WE#', 'RE#', 'R/B#', 'IO[7:0]']
DT = 50e-9


def cycle(t, cle, ale, we_low_at_half, re_low_at_half, byte, dt=DT):
    """Generic cycle helper. Returns rows + new t."""
    if we_low_at_half:
        return [
            [t,       0, cle, ale, 1, 1, 1, f'0x{byte:02X}'],
            [t+dt/2,  0, cle, ale, 0, 1, 1, f'0x{byte:02X}'],
            [t+dt,    0, cle, ale, 1, 1, 1, f'0x{byte:02X}'],
        ], t + dt + dt/2
    if re_low_at_half:
        return [
            [t,       0, cle, ale, 1, 1, 1, '0xFF'],
            [t+dt/2,  0, cle, ale, 1, 0, 1, f'0x{byte:02X}'],
            [t+dt,    0, cle, ale, 1, 1, 1, f'0x{byte:02X}'],
        ], t + dt + dt/2


def cycle_cmd(t, b):  return cycle(t, 1, 0, True, False, b)
def cycle_addr(t, b): return cycle(t, 0, 1, True, False, b)
def cycle_dwr(t, b):  return cycle(t, 0, 0, True, False, b, dt=30e-9)
def cycle_drd(t, b):  return cycle(t, 0, 0, False, True, b, dt=30e-9)


def busy(t, us=5):
    return [
        [t, 0, 0, 0, 1, 1, 0, '0xFF'],
        [t + us*1e-6, 0, 0, 0, 1, 1, 1, '0xFF'],
    ], t + us*1e-6


def main():
    rows = []; t = 0.0

    # Reset
    r, t = cycle_cmd(t, 0xFF); rows += r
    r, t = busy(t, 2);          rows += r
    t += 100e-9

    # Read ID -> Micron 5-byte ID
    r, t = cycle_cmd(t, 0x90);  rows += r
    r, t = cycle_addr(t, 0x00); rows += r
    t += 100e-9
    for b in [0x2C, 0xDC, 0x90, 0x95, 0x06]:
        r, t = cycle_drd(t, b); rows += r
    t += 200e-9

    # Page Read Block 1, Page 128
    r, t = cycle_cmd(t, 0x00); rows += r
    for b in [0x10, 0x00, 0x80, 0x00, 0x01]:
        r, t = cycle_addr(t, b); rows += r
    r, t = cycle_cmd(t, 0x30); rows += r
    r, t = busy(t, 25); rows += r
    for b in [0xDE, 0xAD, 0xBE, 0xEF, 0x12, 0x34, 0x56, 0x78]:
        r, t = cycle_drd(t, b); rows += r
    t += 200e-9

    # Page Program Block 2, Page 256
    r, t = cycle_cmd(t, 0x80); rows += r
    for b in [0x00, 0x00, 0x00, 0x01, 0x02]:
        r, t = cycle_addr(t, b); rows += r
    for b in [0xCA, 0xFE, 0xBA, 0xBE, 0xF0, 0x0D, 0xC0, 0xDE]:
        r, t = cycle_dwr(t, b); rows += r
    r, t = cycle_cmd(t, 0x10); rows += r
    r, t = busy(t, 200); rows += r
    r, t = cycle_cmd(t, 0x70); rows += r
    r, t = cycle_drd(t, 0xE0); rows += r
    t += 200e-9

    # Block Erase Block 64
    r, t = cycle_cmd(t, 0x60); rows += r
    for b in [0x40, 0x00, 0x00]:
        r, t = cycle_addr(t, b); rows += r
    r, t = cycle_cmd(t, 0xD0); rows += r
    r, t = busy(t, 2000); rows += r
    r, t = cycle_cmd(t, 0x70); rows += r
    r, t = cycle_drd(t, 0xE0); rows += r

    out = os.path.join(os.path.dirname(__file__), 'sample_capture.csv')
    with open(out, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for row in rows:
            row[0] = f'{row[0]:.9f}'
            w.writerow(row)

    print(f"Generated: {out}  ({len(rows)} rows, {rows[-1][0]} seconds)")


if __name__ == '__main__':
    main()
