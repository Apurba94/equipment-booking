"""JSON-backed booking calendar with per-instrument rules (max duration, cleaning buffer, opening hours)."""
import datetime as dt
import json
import os
import uuid


def parse_dt(s):
    s = s.strip().replace("T", " ")
    for f in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s, f)
        except ValueError:
            pass
    raise ValueError("bad date/time %r (use YYYY-MM-DD HH:MM)" % s)


class BookingBook:
    """Store: {"equipment": {name: rules}, "bookings": [...]}. Rules: max_hours, buffer_minutes, open, close."""

    def __init__(self, path="bookings.json"):
        self.path = path
        self.data = {"equipment": {}, "bookings": []}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                self.data = json.load(fh)

    def save(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, indent=1)

    def add_equipment(self, name, max_hours=None, buffer_minutes=0, open_hour=None, close_hour=None, location=""):
        self.data["equipment"][name] = {"max_hours": max_hours, "buffer_minutes": buffer_minutes,
                                        "open": open_hour, "close": close_hour, "location": location}
        self.save()

    def _bookings(self, equipment=None, include_cancelled=False):
        return [b for b in self.data["bookings"] if (equipment is None or b["equipment"] == equipment)
                and (include_cancelled or not b.get("cancelled"))]

    def conflicts(self, equipment, start, end, ignore_id=None):
        rules = self.data["equipment"].get(equipment, {})
        buf = dt.timedelta(minutes=rules.get("buffer_minutes") or 0)
        out = []
        for b in self._bookings(equipment):
            if b["id"] == ignore_id:
                continue
            bs, be = parse_dt(b["start"]), parse_dt(b["end"])
            if start < be + buf and bs < end + buf:
                out.append(b)
        return out

    def book(self, equipment, user, start, end, purpose=""):
        if equipment not in self.data["equipment"]:
            raise KeyError("unknown equipment %r" % equipment)
        start, end = (parse_dt(x) if isinstance(x, str) else x for x in (start, end))
        if end <= start:
            raise ValueError("end must be after start")
        r = self.data["equipment"][equipment]
        hours = (end - start).total_seconds() / 3600
        if r.get("max_hours") and hours > r["max_hours"]:
            raise ValueError("%s can be booked for at most %g h (requested %.2g h)" % (equipment, r["max_hours"], hours))
        if r.get("open") is not None and (start.hour < r["open"] or start.date() != end.date()
                                          or end.hour + end.minute / 60 > r["close"]):
            raise ValueError("%s is only bookable between %02d:00 and %02d:00 on one day" % (equipment, r["open"], r["close"]))
        clash = self.conflicts(equipment, start, end)
        if clash:
            c = clash[0]
            raise ValueError("conflicts with %s's booking %s to %s" % (c["user"], c["start"], c["end"]))
        b = {"id": uuid.uuid4().hex[:8], "equipment": equipment, "user": user, "start": start.strftime("%Y-%m-%d %H:%M"),
             "end": end.strftime("%Y-%m-%d %H:%M"), "purpose": purpose}
        self.data["bookings"].append(b)
        self.save()
        return b

    def cancel(self, booking_id, user=None):
        for b in self.data["bookings"]:
            if b["id"] == booking_id and not b.get("cancelled"):
                if user and b["user"] != user:
                    raise PermissionError("booking belongs to %s" % b["user"])
                b["cancelled"] = True
                self.save()
                return b
        raise KeyError(booking_id)

    def agenda(self, day=None, equipment=None, user=None):
        out = []
        for b in self._bookings(equipment):
            if user and b["user"] != user:
                continue
            if day and not (b["start"][:10] <= day <= b["end"][:10]):
                continue
            out.append(b)
        return sorted(out, key=lambda b: (b["start"], b["equipment"]))

    def free_slots(self, equipment, day, min_minutes=60, start_hour=8, end_hour=18):
        d0 = parse_dt(day).replace(hour=start_hour)
        d1 = d0.replace(hour=end_hour)
        busy = sorted((parse_dt(b["start"]), parse_dt(b["end"])) for b in self._bookings(equipment)
                      if parse_dt(b["start"]) < d1 and parse_dt(b["end"]) > d0)
        slots, cur = [], d0
        buf = dt.timedelta(minutes=self.data["equipment"].get(equipment, {}).get("buffer_minutes") or 0)
        for s, e in busy:
            if (s - buf - cur).total_seconds() >= min_minutes * 60:
                slots.append((cur, s - buf))
            cur = max(cur, e + buf)
        if (d1 - cur).total_seconds() >= min_minutes * 60:
            slots.append((cur, d1))
        return slots

    def usage(self):
        hours = {}
        for b in self._bookings():
            h = (parse_dt(b["end"]) - parse_dt(b["start"])).total_seconds() / 3600
            hours.setdefault(b["equipment"], {}).setdefault(b["user"], 0)
            hours[b["equipment"]][b["user"]] += h
        return hours


def _ics_escape(s):
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def to_ics(bookings, calendar_name="Lab equipment"):
    stamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ") if hasattr(dt.datetime, "utcnow") else "19700101T000000Z"
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//research-toolkit//equipment-booking//EN",
             "X-WR-CALNAME:%s" % _ics_escape(calendar_name)]
    for b in bookings:
        lines += ["BEGIN:VEVENT", "UID:%s@equipment-booking" % b["id"], "DTSTAMP:%s" % stamp,
                  "DTSTART:%s" % parse_dt(b["start"]).strftime("%Y%m%dT%H%M%S"),
                  "DTEND:%s" % parse_dt(b["end"]).strftime("%Y%m%dT%H%M%S"),
                  "SUMMARY:%s" % _ics_escape("%s - %s" % (b["equipment"], b["user"])),
                  "DESCRIPTION:%s" % _ics_escape(b.get("purpose", "")), "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
