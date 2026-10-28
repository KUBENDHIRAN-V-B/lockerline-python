# LockerLine (Python)

[![tests](https://github.com/KUBENDHIRAN-V-B/lockerline-python/actions/workflows/tests.yml/badge.svg)](https://github.com/KUBENDHIRAN-V-B/lockerline-python/actions/workflows/tests.yml)

A bank of 48 parcel lockers in an apartment block: couriers drop, residents collect with a code that expires.

## Progress

- [x] Ticket 1 · Forty-eight doors, and a wall you can look at
- [x] Ticket 2 · A courier asks for a door
- [x] Ticket 3 · The code that dies at midnight
- [x] Ticket 4 · Three ways to say no
- [x] Ticket 5 · The door opens, and the clock stops
- [x] Ticket 6 · A notebook nobody can rewrite
- [x] Ticket 7 · One file becomes an app
- [x] Ticket 8 · The rule table, and then the rule changes
- [ ] Ticket 9 · It runs on a machine that isn't yours
- [ ] Ticket 10 · It survives being switched off

## Run it

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest          # the tests
python -m uvicorn lockerline.app:app --port 8080   # the app, on http://127.0.0.1:8080
```

## Built with

Python 3.12 · FastAPI · SQLAlchemy · Pydantic · pytest

---

Built by KUBENDHIRAN V B on [LearnTube Guided Projects](https://guidedprojects.learntube.ai).
