# -*- coding: utf-8 -*-

"""Simple Stopwatch

This simple module was created as a debugging tool and for the calibration
of the progressbar. It contains a single class that can create a object which
can time different segments and present the data as a table.
"""

import time
import tabulate as tbl


class SegmentTimer():
    """Class to time segments for debugging and the progressbar

    Attributes:
        start (float): Reference starting point for each lap
        dic (dictionary): Dictionary of segment times
    """

    def __init__(self):
        self.ref = 0.
        self.list = []

    def start(self):
        """Sets initial reference time"""

        self.ref = time.perf_counter()

    def seg(self, seg):
        """Adds segment with time to list"""

        stop = time.perf_counter()
        self.list.append([seg, stop - self.ref])
        self.ref = stop

    def present(self, nelm):
        """Presents segment results"""

        total = sum(row[1] for row in self.list)
        [row.append(row[1]/total*100) for row in self.list]

        table = tbl.tabulate(
            self.list,
            headers=["Segement", "seconds", "%"],
            numalign="center",
            tablefmt="simple",
            floatfmt=".2f"
        )
        print(f"\n  Number of elements {nelm}")
        print(table + "\n")
