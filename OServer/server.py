#Copyright [2025] [LightOfTheWar]

#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#imitations under the License.

import socket
import threading
import sqlite3
import hashlib
import os
import time

HOST = '0.0.0.0'
PORT = 12345

clients = {}  # pseudo : socket
admins = {"admin"}  # admin par défaut
CHAT_FILE = "chat.txt"

printcolors = {
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "reset": "\033[0m"
}

# Connexion à SQLite
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users (pseudo TEXT PRIMARY KEY, password TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS banned_users (pseudo TEXT PRIMARY KEY)")
conn.commit()


def add_user(pseudo, password):
    cursor.execute("INSERT INTO users (pseudo, password) VALUES (?, ?)", (pseudo, password))
    conn.commit()


def check_user(pseudo, password):
    cursor.execute("SELECT password FROM users WHERE pseudo = ?", (pseudo,))
    row = cursor.fetchone()
    return row and row[0] == password


def is_banned(pseudo):
    cursor.execute("SELECT pseudo FROM banned_users WHERE pseudo = ?", (pseudo,))
    return cursor.fetchone() is not None


def ban_user(pseudo):
    cursor.execute("INSERT OR IGNORE INTO banned_users (pseudo) VALUES (?)", (pseudo,))
    conn.commit()


def clear_chat():
    open(CHAT_FILE, "w", encoding="utf-8").close()


def save_message(pseudo, message):
    with open(CHAT_FILE, "a", encoding="utf-8") as f:
        f.write(f"{pseudo}: {message}\n")


def get_chat_history():
    if not os.path.exists(CHAT_FILE):
        return ""

    with open(CHAT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return "".join(lines[-40:])


def broadcast(message):
    print(f"{printcolors["blue"]}{message}{printcolors['reset']}")  # Affiche dans console serveur
    to_remove = []
    for user, conn in clients.items():
        try:
            conn.send(message.encode("utf-8"))
        except:
            to_remove.append(user)
    for user in to_remove:
        remove_client(user)


def remove_client(pseudo):
    if pseudo in clients:
        try:
            clients[pseudo].close()
        except:
            pass
        del clients[pseudo]
        broadcast(f"[SERVER] {pseudo} s'est déconnecté.")


def handle_command(command, pseudo):
    if pseudo not in admins:
        return

    args = command.split()
    if args[0] == "/clear":
        clear_chat()
        broadcast(f"[SERVER] [Chat vidé par un admin]")
    elif args[0] == "/ban" and len(args) > 1:
        banned_user = args[1]
        if banned_user in clients:
            try:
                clients[banned_user].close()
            except:
                pass
            del clients[banned_user]
        ban_user(banned_user)
        broadcast(f"[SERVER] {banned_user} a été banni.")
        print(f"{printcolors['red']}{banned_user} a été banni.{printcolors['reset']}")


def handle_client(conn, addr):
    pseudo = None
    try:
        # Le client envoie pseudo et mdp séparés par '\n' dans un seul message
        data = conn.recv(1024).decode("utf-8")
        if "\n" not in data:
            conn.send("Format identifiants incorrect".encode("utf-8"))
            conn.close()
            return
        pseudo, password = data.split("\n", 1)
        pseudo = pseudo.strip()
        password = password.strip()
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        if is_banned(pseudo):
            conn.send("Vous avez été banni.".encode("utf-8"))
            conn.close()
            print(f"{printcolors['red']}{pseudo} a essayer de se connecter (banned){printcolors['reset']}")
            return

        cursor.execute("SELECT * FROM users WHERE pseudo = ?", (pseudo,))
        if cursor.fetchone():
            if not check_user(pseudo, hashed_password):
                conn.send("Mot de passe incorrect.".encode("utf-8"))
                conn.close()
                return
        else:
            add_user(pseudo, hashed_password)

        clients[pseudo] = conn
        conn.send(get_chat_history().encode("utf-8"))
        broadcast(f"[SERVER] {pseudo} a rejoint le chat !")

        print(f"{printcolors["yellow"]}{pseudo}{printcolors["reset"]} connecté depuis {addr}")

        while True:
            message = conn.recv(2048).decode("utf-8")
            if not message:
                break

            if message.startswith("/"):
                handle_command(message, pseudo)
            else:
                save_message(pseudo, message)
                broadcast(f"{pseudo} : {message}")

    except Exception as e:
        print(f"{printcolors["red"]}Erreur client{printcolors["reset"]} {pseudo} : {e}")
    finally:
        remove_client(pseudo)


def server_console(server_socket):
    while True:
        cmd = input()
        args = cmd.split()
        if cmd.lower() == "stop":
            print(f"{printcolors["magenta"]}Arrêt du serveur demandé.{printcolors['reset']}")
            broadcast(f"[SERVER] Arrêt du serveur...")
            time.sleep(3)
            try:
                server_socket.close()
            except:
                pass
            os._exit(0)  # Quitte immédiatement
        elif cmd.lower() == "clear":
            clear_chat()
            print(f"{printcolors["magenta"]}Chat réinitialisé par la console serveur{printcolors['reset']}")
            broadcast(f"[SERVER] [Chat réinitialisé par la console serveur]")
        elif cmd.lower() == "help":
            print(f"\nCommandes :\n'stop' : stop le serveur\n'clear' : clear le chat\n'say' : permet d'envoyer un message depuis la console (mette le message apres le 'say')\n")
        elif args[0] == "ban" and len(args) > 1:
            banned_user = args[1]
            if banned_user in clients:
                try:
                    clients[banned_user].close()
                except:
                    pass
                del clients[banned_user]
            ban_user(banned_user)
            print(f"{printcolors['red']}{banned_user} a été banni.{printcolors['reset']}")
            broadcast(f"[SERVER] {banned_user} a été banni.")
        elif args[0] == "say" and len(args) > 1:
            message = " ".join(args[1:])
            broadcast(f"[CONSOLE] {message}")


def start_server():
    print(f"{printcolors["magenta"]}Demarrage..{printcolors["reset"]}\n")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"{printcolors["green"]}Serveur démarré{printcolors["reset"]} sur {HOST}:{PORT}")
    print(f"Vous pouvez modifiez l'adresse dans le server.py\n \nLe serveur est accessible en local :\nip : 127.0.0.1\nport : {PORT}")
    print(f"\nCommandes visibles avec 'help'\n")

    threading.Thread(target=server_console, args=(server,), daemon=True).start()

    while True:
        try:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
        except Exception as e:
            print(f"{printcolors["red"]}Erreur accept{printcolors["reset"]} : {e}")
            break

    server.close()


if __name__ == "__main__":
    start_server()