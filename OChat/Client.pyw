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

import customtkinter as ctk
import socket
import threading

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class ClientApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.iconbitmap("logo.ico")
        self.title("Client Chat")
        self.geometry("500x500")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.client_socket = None
        self.receive_thread = None

        self.current_frame = None
        self.ip = None
        self.port = None
        self.pseudo = None

        self.show_server_frame()

    def show_server_frame(self):
        if self.current_frame:
            self.current_frame.destroy()

        frame = ctk.CTkFrame(self)
        frame.pack(expand=True, fill="both", padx=20, pady=20)

        label = ctk.CTkLabel(frame, text="Adresse IP du serveur :", font=ctk.CTkFont(size=18))
        label.pack(pady=(0, 5))
        self.entry_ip = ctk.CTkEntry(frame, placeholder_text="ex: 127.0.0.1")
        self.entry_ip.pack(pady=5)

        label_port = ctk.CTkLabel(frame, text="Port du serveur :", font=ctk.CTkFont(size=18))
        label_port.pack(pady=(15, 5))
        self.entry_port = ctk.CTkEntry(frame, placeholder_text="ex: 12345")
        self.entry_port.pack(pady=5)

        button = ctk.CTkButton(frame, text="Se connecter", command=self.connect_to_server)
        button.pack(pady=20)

        self.current_frame = frame

    def connect_to_server(self):
        ip = self.entry_ip.get().strip()
        port_str = self.entry_port.get().strip()
        if not ip or not port_str.isdigit():
            self.show_error("IP ou port invalide.")
            return
        self.ip = ip
        self.port = int(port_str)

        # Essayer de créer socket pour tester connexion
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect((self.ip, self.port))
            sock.close()
        except Exception as e:
            self.show_error(f"Impossible de joindre le serveur:\n{e}")
            return

        self.show_login_frame()

    def show_login_frame(self):
        if self.current_frame:
            self.current_frame.destroy()

        frame = ctk.CTkFrame(self)
        frame.pack(expand=True, fill="both", padx=20, pady=20)

        label = ctk.CTkLabel(frame, text="Pseudo :", font=ctk.CTkFont(size=18))
        label.pack(pady=(0, 5))
        self.entry_pseudo = ctk.CTkEntry(frame)
        self.entry_pseudo.pack(pady=5)

        label_pass = ctk.CTkLabel(frame, text="Mot de passe :", font=ctk.CTkFont(size=18))
        label_pass.pack(pady=(15, 5))
        self.entry_password = ctk.CTkEntry(frame, show="*")
        self.entry_password.pack(pady=5)

        button = ctk.CTkButton(frame, text="Se connecter", command=self.login)
        button.pack(pady=20)

        self.current_frame = frame

    def login(self):
        pseudo = self.entry_pseudo.get().strip()
        password = self.entry_password.get().strip()
        if not pseudo or not password:
            self.show_error("Pseudo et mot de passe requis.")
            return

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.ip, self.port))
        except Exception as e:
            self.show_error(f"Connexion échouée :\n{e}")
            return

        try:
            # Envoi pseudo + mdp dans un seul message séparé par \n
            self.client_socket.send(f"{pseudo}\n{password}".encode("utf-8"))
        except Exception as e:
            self.show_error(f" d'envoi des identifiants :\n{e}")
            return

        # Attendre l'historique du chat
        try:
            history = self.client_socket.recv(4096).decode("utf-8")
        except Exception as e:
            self.show_error(f" réception historique :\n{e}")
            return

        self.pseudo = pseudo
        self.show_chat_frame(history)

        self.receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
        self.receive_thread.start()

    def show_chat_frame(self, history_text):
        if self.current_frame:
            self.current_frame.destroy()

        frame = ctk.CTkFrame(self)
        frame.pack(expand=True, fill="both", padx=10, pady=10)

        self.chat_textbox = ctk.CTkTextbox(frame, wrap="word", state="normal")
        self.chat_textbox.pack(expand=True, fill="both", pady=(0,10))
        self.chat_textbox.insert("end", history_text)
        self.chat_textbox.configure(state="disabled")

        self.entry_message = ctk.CTkEntry(frame)
        self.entry_message.pack(fill="x", side="left", expand=True, padx=(0, 5))
        self.entry_message.bind("<Return>", self.send_message)

        send_button = ctk.CTkButton(frame, text="Envoyer", width=80, command=self.send_message)
        send_button.pack(side="right")

        self.current_frame = frame

    def receive_messages(self):
        while True:
            try:
                message = self.client_socket.recv(2048).decode("utf-8")
                if not message:
                    self.append_message("[...] [Connexion fermée par le serveur]")
                    break
                self.append_message(message)
            except Exception:
                self.append_message("[Erreur] [Erreur de connexion]")
                break

    def append_message(self, message):
        self.chat_textbox.configure(state="normal")
        self.chat_textbox.insert("end", message + "\n")
        self.chat_textbox.see("end")
        self.chat_textbox.configure(state="disabled")

    def send_message(self, event=None):
        msg = self.entry_message.get().strip()
        if not msg:
            return
        try:
            self.client_socket.send(msg.encode("utf-8"))
            self.entry_message.delete(0, "end")
        except Exception:
            self.append_message("[Erreur] [Impossible d'envoyer le message]")
            print(f"\033[31m[Error]\033[0m : [Impossible d'envoyer le message]")
            self.client_socket.close()

    def show_error(self, message):
        from tkinter import messagebox
        messagebox.showerror("Erreur", message)
        print(f"\033[31m[Error]\033[0m : {message}")

    def on_close(self):
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        self.destroy()


if __name__ == "__main__":
    app = ClientApp()
    app.mainloop()