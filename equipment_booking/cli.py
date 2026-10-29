"""Command-line interface for equipment-booking."""
import argparse
import getpass

from .core import BookingBook, to_ics


def main(argv=None):
    ap = argparse.ArgumentParser(prog="equipment-booking", description="Book shared lab equipment.")
    ap.add_argument("--file", default="bookings.json", help="shared booking file (e.g. on a network drive)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("add-equipment")
    e.add_argument("name")
    e.add_argument("--max-hours", type=float)
    e.add_argument("--buffer", type=int, default=0, help="cleaning/cool-down minutes between bookings")
    e.add_argument("--open", type=int, help="earliest hour")
    e.add_argument("--close", type=int, help="latest hour")
    e.add_argument("--location", default="")
    b = sub.add_parser("book")
    b.add_argument("equipment")
    b.add_argument("start", help="YYYY-MM-DD HH:MM")
    b.add_argument("end")
    b.add_argument("--user", default=getpass.getuser())
    b.add_argument("--purpose", default="")
    c = sub.add_parser("cancel")
    c.add_argument("id")
    c.add_argument("--user")
    ag = sub.add_parser("agenda")
    ag.add_argument("--day")
    ag.add_argument("--equipment")
    ag.add_argument("--user")
    f = sub.add_parser("free")
    f.add_argument("equipment")
    f.add_argument("day")
    f.add_argument("--min", type=int, default=60)
    i = sub.add_parser("ics")
    i.add_argument("-o", "--output", default="bookings.ics")
    i.add_argument("--equipment")
    sub.add_parser("usage")
    args = ap.parse_args(argv)
    bb = BookingBook(args.file)
    try:
        if args.cmd == "add-equipment":
            bb.add_equipment(args.name, args.max_hours, args.buffer, args.open, args.close, args.location)
        elif args.cmd == "book":
            r = bb.book(args.equipment, args.user, args.start, args.end, args.purpose)
            print("booked %s (id %s)" % (r["equipment"], r["id"]))
        elif args.cmd == "cancel":
            bb.cancel(args.id, args.user)
            print("cancelled %s" % args.id)
        elif args.cmd == "agenda":
            for r in bb.agenda(args.day, args.equipment, args.user):
                print("%s  %s-%s  %-20s %-12s %s" % (r["id"], r["start"], r["end"][11:], r["equipment"], r["user"], r["purpose"]))
        elif args.cmd == "free":
            for s, e2 in bb.free_slots(args.equipment, args.day, args.min):
                print("%s - %s" % (s.strftime("%H:%M"), e2.strftime("%H:%M")))
        elif args.cmd == "ics":
            with open(args.output, "w", encoding="utf-8", newline="") as fh:
                fh.write(to_ics(bb.agenda(equipment=args.equipment)))
            print("wrote %s" % args.output)
        elif args.cmd == "usage":
            for eq, users in bb.usage().items():
                print(eq + ": " + ", ".join("%s %.1f h" % kv for kv in sorted(users.items(), key=lambda kv: -kv[1])))
    except (KeyError, ValueError, PermissionError) as exc:
        print("error: %s" % exc)
        return 1
    return 0
