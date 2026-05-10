"""
ONFI Decoder - Open NAND Flash Interface protocol decoder.

Parses logic analyzer captures (CSV) of ONFI bus traffic and produces
human-readable command sequences with full address/data/status decoding.
"""
from .decoder import OnfiDecoder, DecodedEvent
from .commands import ONFI_COMMANDS, STATUS_BITS

__version__ = "0.1.0"
__all__ = ["OnfiDecoder", "DecodedEvent", "ONFI_COMMANDS", "STATUS_BITS"]
