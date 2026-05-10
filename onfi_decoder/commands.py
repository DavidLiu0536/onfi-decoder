"""ONFI command opcodes and status bit definitions (ONFI 4.x compatible)."""

# Reference: ONFI 4.0 Specification, Table 132 (Command Set)
ONFI_COMMANDS = {
    # Reset
    0xFF: ("RESET",                   "Reset the entire device"),
    0xFC: ("SYNC_RESET",              "Synchronous reset"),
    0xFA: ("RESET_LUN",               "Reset specified LUN"),

    # Identification
    0x90: ("READ_ID",                 "Read manufacturer/device ID (5 bytes)"),
    0xEC: ("READ_PARAMETER_PAGE",     "Read parameter page (256 bytes)"),
    0xED: ("READ_UNIQUE_ID",          "Read unique ID"),

    # Status
    0x70: ("READ_STATUS",             "Read status register"),
    0x71: ("READ_STATUS_ENH",         "Read status enhanced (LUN-aware)"),
    0x78: ("READ_STATUS_ENH_LUN",     "Read status enhanced for LUN"),

    # Page Read
    0x00: ("READ_PAGE",               "Page read (1st cycle, needs 0x30)"),
    0x30: ("READ_PAGE_CONFIRM",       "Page read confirm"),
    0x05: ("RANDOM_DATA_READ",        "Random data read (1st cycle, needs 0xE0)"),
    0xE0: ("RANDOM_DATA_READ_CONFIRM", "Random data read confirm"),
    0x06: ("CHANGE_READ_COLUMN_ENH",  "Change read column enhanced"),

    # Cache Read
    0x31: ("READ_CACHE_SEQ",          "Read cache sequential"),
    0x35: ("READ_CACHE_RANDOM",       "Read cache random"),
    0x3F: ("READ_CACHE_END",          "Read cache end"),

    # Page Program
    0x80: ("PROGRAM_PAGE",            "Page program (1st cycle, needs 0x10)"),
    0x10: ("PROGRAM_CONFIRM",         "Page program confirm"),
    0x85: ("RANDOM_DATA_INPUT",       "Random data input"),
    0x11: ("PROGRAM_PAGE_MULTI",      "Multi-plane page program"),
    0x15: ("CACHE_PROGRAM",           "Cache program"),

    # Block Erase
    0x60: ("BLOCK_ERASE",             "Block erase (1st cycle, needs 0xD0)"),
    0xD0: ("ERASE_CONFIRM",           "Block erase confirm"),
    0xD1: ("ERASE_MULTI",             "Multi-plane block erase"),

    # Features
    0xEE: ("GET_FEATURES",            "Get features"),
    0xEF: ("SET_FEATURES",            "Set features"),
    0xFD: ("SET_FEATURES_LUN",        "Set features for LUN"),
    0xFE: ("GET_FEATURES_LUN",        "Get features for LUN"),

    # ZQ calibration / interface change
    0xF9: ("ZQ_CALIBRATION_LONG",     "ZQ calibration long"),
    0xD9: ("ZQ_CALIBRATION_SHORT",    "ZQ calibration short"),
}

# Status register bit definitions (Table 28, ONFI 4.0)
STATUS_BITS = {
    7: ("WP",       "Write Protect (0=protected, 1=writable)"),
    6: ("RDY",      "Ready (1=ready, 0=busy)"),
    5: ("ARDY",     "Array Ready (1=array operations done)"),
    4: ("VSP",      "VPP unsuccessful"),
    3: ("PROG_FAIL_N", "Program fail (n-1 cache)"),
    2: ("PROG_FAIL", "Program/erase fail (last)"),
    1: ("FAIL_N",   "Fail (n-1 op)"),
    0: ("FAIL",     "Fail (current op: 0=ok, 1=fail)"),
}

# Known manufacturer IDs (1st byte of Read ID)
MANUFACTURER_IDS = {
    0x2C: "Micron / Crucial",
    0xAD: "Hynix",
    0xEC: "Samsung",
    0x98: "Toshiba / Kioxia",
    0x45: "SanDisk / Western Digital",
    0x92: "ESMT",
    0xC8: "GigaDevice",
    0x01: "AMD / Spansion / Cypress",
    0xC2: "Macronix",
}


def lookup_command(opcode: int) -> tuple:
    """Return (name, description) for a given opcode, or UNKNOWN."""
    return ONFI_COMMANDS.get(opcode, ("UNKNOWN", f"Unrecognized opcode 0x{opcode:02X}"))


def parse_status(status: int) -> list:
    """Decode status register byte into a list of active flags."""
    flags = []
    for bit in range(7, -1, -1):
        name, desc = STATUS_BITS[bit]
        flags.append({
            "bit": bit,
            "name": name,
            "value": (status >> bit) & 1,
            "desc": desc,
        })
    return flags
