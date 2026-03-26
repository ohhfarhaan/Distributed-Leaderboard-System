# Distributed Leaderboard System

A minimal real-time leaderboard over TCP sockets.  
The server persists scores in `leaderboard.json` and pushes live updates to every connected client.

---

## Requirements

- Python 3.10+ (uses `tkinter`, which ships with the standard library)

No third-party packages needed.

---

## Run

### 1 — Start the server (once, on any machine)
```bash
python server.py
```

### 2 — Start as many clients as you like
```bash
python client.py
```

For clients on **other machines**, open `client.py` and change:
```python
SERVER_HOST = "127.0.0.1"   # ← replace with the server's IP address
```

---

## Features

| | |
|---|---|
| **Submit score** | Enter a team name and score, press **SUBMIT** (or Enter). Only the highest score per team is kept. |
| **Live leaderboard** | Every connected client receives an automatic push the moment any score changes. No manual refresh needed. |
| **Persistence** | Scores are stored in `leaderboard.json` — the server survives restarts. |

---

## Files

```
server.py          TCP server — manages leaderboard.json and broadcasts updates
client.py          tkinter GUI client
leaderboard.json   Created automatically on first submission
```
