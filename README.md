# equipment-booking

**Book shared instruments (confocal, flow cytometer, PCR machines) without double bookings:
per-instrument rules, cleaning buffers, free-slot search, usage statistics and calendar export.**

Part of the *Research Automation Toolkit*: 100 open tools for daily research work.

## Why

Paper sign-up sheets and shared spreadsheets cause double bookings, forgotten cancellations and
no record of who used what (needed for cost recovery and facility reports). Full facility-management
systems are overkill for a department with a handful of instruments. A JSON file on a shared drive and
a command-line tool cover the essentials.

## Features

- Instruments with rules: maximum booking length, buffer minutes between users (cleaning, cool-down),
  opening hours
- Conflict detection including buffers; clear error naming the blocking booking
- Cancel (only by the owner when `--user` is given), agenda per day/instrument/user
- Free slots for a day, usage hours per instrument and user
- ICS export for Outlook/Google/Apple calendars

## Usage

```bash
pip install .
equipment-booking add-equipment Confocal --max-hours 4 --buffer 15 --open 8 --close 20
equipment-booking book Confocal "2026-05-04 09:00" "2026-05-04 11:00" --purpose "live imaging"
equipment-booking free Confocal 2026-05-04
equipment-booking agenda --day 2026-05-04
equipment-booking ics -o lab_equipment.ics
```

## Testing

```bash
python -m unittest discover -s tests -t .
```

## License

MIT (c) JANIN A APURBA
