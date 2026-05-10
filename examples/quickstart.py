"""Quickstart: decode the sample capture and visualize."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from onfi_decoder import OnfiDecoder
from onfi_decoder.visualize import plot_timeline

dec = OnfiDecoder()
dec.decode_csv(os.path.join(os.path.dirname(__file__), 'sample_capture.csv'))
print(dec.report_text())
print("\nStats:", dec.stats())

plot_timeline(dec, os.path.join(os.path.dirname(__file__), 'timeline.png'))
