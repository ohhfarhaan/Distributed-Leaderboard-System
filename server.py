import socket
import threading
import json
import os
import ssl

HOST = "0.0.0.0"
PORT = 9999
DATA_FILE = "leaderboard.json"

clients: list[socket.socket] = []
clients_lock = threading.Lock()
data_lock = threading.Lock()


# ─── Persistence ─────────────────────────────────────────────────────────────

def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}


def save_data(data: dict) -> None:
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_sorted_leaderboard() -> list[dict]:
    data = load_data()
    sorted_entries = sorted(data.items(), key=lambda x: x[1], reverse=True)
    return [{"team": team, "score": score} for team, score in sorted_entries]


# ─── Networking helpers ───────────────────────────────────────────────────────

def send_message(sock: socket.socket, payload: dict) -> None:
    raw = json.dumps(payload) + "\n"
    sock.sendall(raw.encode())


def broadcast(payload: dict) -> None:
    with clients_lock:
        dead = []
        for sock in clients:
            try:
                send_message(sock, payload)
            except Exception:
                dead.append(sock)
        for sock in dead:
            clients.remove(sock)


# ─── Request handling ─────────────────────────────────────────────────────────

def process_message(conn: socket.socket, data: dict) -> None:
    action = data.get("action")

    if action == "submit":
        team = data.get("team", "").strip()
        score = data.get("score")

        if not team or score is None:
            send_message(conn, {"type": "status", "message": "Invalid submission."})
            return

        try:
            score = int(score)
        except (ValueError, TypeError):
            send_message(conn, {"type": "status", "message": "Score must be an integer."})
            return

        with data_lock:
            leaderboard = load_data()
            existing = leaderboard.get(team)
            if existing is None or score > existing:
                leaderboard[team] = score
                save_data(leaderboard)
                updated = True
            else:
                updated = False

        if updated:
            broadcast({"type": "leaderboard", "data": get_sorted_leaderboard()})
            send_message(conn, {"type": "status", "message": f"Score updated for {team}."})
        else:
            send_message(
                conn,
                {
                    "type": "status",
                    "message": f"Score not updated — current score ({existing}) is higher.",
                },
            )

    elif action == "get":
        send_message(conn, {"type": "leaderboard", "data": get_sorted_leaderboard()})

    else:
        send_message(conn, {"type": "status", "message": "Unknown action."})


# ─── Client thread ────────────────────────────────────────────────────────────

def handle_client(conn: socket.socket, addr: tuple) -> None:
    print(f"[+] Connected  {addr[0]}:{addr[1]}")

    with clients_lock:
        clients.append(conn)

    # Push current leaderboard immediately on connect
    try:
        send_message(conn, {"type": "leaderboard", "data": get_sorted_leaderboard()})
    except Exception:
        pass

    buf = ""
    try:
        while True:
            chunk = conn.recv(4096).decode()
            if not chunk:
                break
            buf += chunk
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.strip()
                if line:
                    try:
                        process_message(conn, json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        print(f"[!] Error with {addr[0]}:{addr[1]}: {e}")
    finally:
        with clients_lock:
            if conn in clients:
                clients.remove(conn)
        conn.close()
        print(f"[-] Disconnected  {addr[0]}:{addr[1]}")


# ─── Entry point ─────────────────────────────────────────────────────────────

def main() -> None:

    # create SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")

    # normal TCP socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()

    # wrap socket with SSL
    server = context.wrap_socket(server, server_side=True)

    print(f"[*] Secure Leaderboard server listening on port {PORT}")

    try:
        while True:
            conn, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\n[*] Server shutting down.")
    finally:
        server.close()


if __name__ == "__main__":
    main()
