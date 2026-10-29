import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from equipment_booking.cli import main
from equipment_booking.core import BookingBook, to_ics


class BookingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.bb = BookingBook(os.path.join(self.tmp.name, "b.json"))
        self.bb.add_equipment("Confocal", max_hours=4, buffer_minutes=15, open_hour=8, close_hour=20)
        self.bb.add_equipment("PCR-1")

    def tearDown(self):
        self.tmp.cleanup()

    def test_book_and_conflict(self):
        self.bb.book("Confocal", "ana", "2026-05-04 09:00", "2026-05-04 11:00")
        with self.assertRaises(ValueError):
            self.bb.book("Confocal", "bo", "2026-05-04 10:30", "2026-05-04 12:00")
        with self.assertRaises(ValueError):                      # inside the 15 min cleaning buffer
            self.bb.book("Confocal", "bo", "2026-05-04 11:10", "2026-05-04 12:00")
        self.bb.book("Confocal", "bo", "2026-05-04 11:15", "2026-05-04 12:00")
        self.bb.book("PCR-1", "bo", "2026-05-04 10:00", "2026-05-04 11:00")   # other instrument is fine

    def test_rules(self):
        with self.assertRaises(ValueError):
            self.bb.book("Confocal", "ana", "2026-05-04 09:00", "2026-05-04 14:00")    # > 4 h
        with self.assertRaises(ValueError):
            self.bb.book("Confocal", "ana", "2026-05-04 06:00", "2026-05-04 07:00")    # before opening
        with self.assertRaises(ValueError):
            self.bb.book("PCR-1", "ana", "2026-05-04 10:00", "2026-05-04 09:00")
        with self.assertRaises(KeyError):
            self.bb.book("Laser", "ana", "2026-05-04 10:00", "2026-05-04 11:00")

    def test_cancel_and_persistence(self):
        b = self.bb.book("PCR-1", "ana", "2026-05-04 10:00", "2026-05-04 11:00")
        with self.assertRaises(PermissionError):
            self.bb.cancel(b["id"], user="bo")
        self.bb.cancel(b["id"], user="ana")
        again = BookingBook(self.bb.path)
        again.book("PCR-1", "bo", "2026-05-04 10:00", "2026-05-04 11:00")
        self.assertEqual(len(again.agenda(day="2026-05-04")), 1)

    def test_free_slots_and_usage(self):
        self.bb.book("Confocal", "ana", "2026-05-04 09:00", "2026-05-04 11:00")
        self.bb.book("Confocal", "bo", "2026-05-04 13:00", "2026-05-04 15:00")
        slots = [(s.strftime("%H:%M"), e.strftime("%H:%M")) for s, e in self.bb.free_slots("Confocal", "2026-05-04")]
        self.assertEqual(slots, [("11:15", "12:45"), ("15:15", "18:00")])
        self.assertEqual(self.bb.usage()["Confocal"], {"ana": 2.0, "bo": 2.0})

    def test_ics_and_cli(self):
        b = self.bb.book("PCR-1", "ana", "2026-05-04 10:00", "2026-05-04 11:00", "qPCR, run 2")
        ics = to_ics([b])
        self.assertIn("DTSTART:20260504T100000", ics)
        self.assertIn("DESCRIPTION:qPCR\\, run 2", ics)
        with redirect_stdout(io.StringIO()) as buf:
            self.assertEqual(main(["--file", self.bb.path, "book", "PCR-1", "2026-05-04 10:30", "2026-05-04 11:30",
                                   "--user", "bo"]), 1)
            main(["--file", self.bb.path, "agenda", "--day", "2026-05-04"])
        self.assertIn("conflicts with ana", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
