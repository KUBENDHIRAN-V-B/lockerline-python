# LockerLine

LockerLine is a small parcel-locker API. This is the finished project.

| Part | What it does |
|---|---|
| The image | Python 3.12 slim, pinned dependencies, FastAPI application |
| Running it | A `/data` volume, `--env-file`, `.dockerignore`, logs on stdout, this README |

## Run it locally

```bash
python -m venv .venv
python -m uvicorn lockerline.app:app --host 127.0.0.1 --port 8080
```

Open <http://localhost:8080/> for the wall and <http://localhost:8080/docs> for the API. Settings come from the
environment or a `.env` file (`.env.example` lists every one); nothing is hard-coded.

Run the tests: `python -m pytest tests`. The grading suite: `python -m pytest sandbox`.

## Run it in a container

```bash
docker build -t lockerline .
docker run -p 8080:8080 lockerline
```

The image bakes in only `HOST=0.0.0.0` and `PORT=8080`. Every other setting comes from the env-file. For real use,
copy `.env.example` to `.env` and run the container with the env-file and the database on a named volume:

```bash
cp .env.example .env
docker run -d --name lockerline -p 8080:8080 -v lockerline-data:/data --env-file .env lockerline
```

The database lives on the `lockerline-data` volume, so you can `docker rm -f lockerline` and run the same command
again: every parcel is still there. Change `FREE_WINDOW_HOURS` in `.env`, remove the container and run it again. The
rule book shows the new window, with no rebuild. Logs go to stdout: `docker logs lockerline`.

## One parcel, from drop to collection

```bash
# 1. the wall: 48 doors, all free
curl -s http://localhost:8080/towers/A/doors | head -c 300

# 2. a courier books a medium door for flat 302 — note the door and the code (shown once)
curl -s -X POST http://localhost:8080/drops -H 'content-type: application/json' -d '{"size_class":"M","flat":"302"}'
# {"parcel_id":"P001","door":"D21","size_class":"M","flat":"302","dropped_at":"…Z","code":"482913","expires_at":"…Z"}

# 3. the door is holding
curl -s "http://localhost:8080/towers/A/doors?state=holding"

# 4. the resident opens it with the code
curl -s -X POST http://localhost:8080/pickups -H 'content-type: application/json' -d '{"code":"482913"}'
# {"parcel_id":"P001","door":"D21","opened_at":"…Z","dwell_seconds":158520}

# 5. the same code again is refused
curl -s -X POST http://localhost:8080/pickups -H 'content-type: application/json' -d '{"code":"482913"}'
# {"type":"/errors/code-used","title":"This code has already opened its door","status":409,"detail":"…"}

# 6. the parcel's history — dropped, code issued, opened
curl -s http://localhost:8080/parcels/P001
```

The timestamps and code vary on every run. Use the actual code returned by your own drop in steps 4 and 5.

## Conventions

- Every error is `application/problem+json`: `{type, title, status, detail}` plus the fields named for that refusal.
- Ids on the wire are opaque strings (P001, D21); database integers never leave the app, not even in a log line.
- The pickup code is hashed with keyed SHA-256 (HMAC with `CODE_HASH_KEY`), not bcrypt. The plain code appears in the drop response and nowhere else: not in the database, not in a log line, not in an event.
- The clock and the database session are dependencies, so every time-based rule is tested against a fixed clock.
- Logs go to stdout. Each request gets one request line with a request id; each parcel event gets one line with a public parcel id. Pickup codes and resident names are never logged.

## Verified on this build

Docker is not available in the environment used to prepare these changes, so the image build, volume restart, host-network checks and `docker diff` have not been run here. Run the checks below on the target machine and replace placeholders with actual results.

| Check | Result |
|---|---|
| `docker build` | Not run in this environment |
| GET `/healthz` from the host | Expected: HTTP 200, `{"status":"ok"}`; verify locally |
| GET `/towers/A/doors` from the host | Expected: 48 doors, free 48; verify locally |
| The same two from another container | Not run in this environment |
| drop <id 1> (<door 1>) and <id 2> (<door 2>), `docker rm -f`, run again on the same volume | `GET /parcels/<id 1>` byte-identical before and after; holding doors identical apart from dwell; old code opens <door 1> (200), then `code-used` (409) |
| `FREE_WINDOW_HOURS=24` in a copy of the env-file, container removed and run again | `GET /settings` → `{"free_window_hours":24,…}`; same image id; new drop expires 24 h after it |
| `docker logs` | one line per request (`request method=… path=… status=… request_id=…`) and one per event (`event kind=dropped parcel_id=<id> door=<door>`); code appears 0 times; no resident name appears |
| `docker diff` | only `A /data` (the volume's mount point); nothing written under `/app` |
| The two build-and-run commands alone (`docker run -p 8080:8080 lockerline`, no env-file) | health 200 and wall answers. Without env-file the database path falls back to `./lockerline.db` inside the container, so use env-file and volume for persistent data. |
| `pip freeze` in the image | Compare with `requirements.lock` (excluding pip/setuptools/wheel) |
| `find /app -name __pycache__ -o -name '*.db' -o -name sandbox -o -name tests` | Expected to print nothing; verify locally |

<!-- learntube:start -->
---

[![tests](https://github.com/KUBENDHIRAN-V-B/lockerline-python/actions/workflows/tests.yml/badge.svg)](https://github.com/KUBENDHIRAN-V-B/lockerline-python/actions/workflows/tests.yml)

### Progress

- [x] Ticket 1 · Forty-eight doors, and a wall you can look at
- [x] Ticket 2 · A courier asks for a door
- [x] Ticket 3 · The code that dies at midnight
- [x] Ticket 4 · Three ways to say no
- [x] Ticket 5 · The door opens, and the clock stops
- [x] Ticket 6 · A notebook nobody can rewrite
- [x] Ticket 7 · One file becomes an app
- [x] Ticket 8 · The rule table, and then the rule changes
- [x] Ticket 9 · It runs on a machine that isn't yours
- [x] Ticket 10 · It survives being switched off

Built by KUBENDHIRAN V B on [LearnTube Guided Projects](https://guidedprojects.learntube.ai).
<!-- learntube:end -->
