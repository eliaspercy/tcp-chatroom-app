import socket
import sys
import threading
import tkinter as tk


# ------------------------------------------------ Initialisation ---------------------------------------------------- #

try:
    USER_NAME = str(sys.argv[1])
    HOST_NAME = str(sys.argv[2])
    PORT = int(sys.argv[3])
except Exception as err:
    print('Couldn\'t start client! Ensure the username, hostname, and port are included respectively when starting the'
          ' client. (Error: {}.)'.format(str(err)))
    sys.exit(1)

ADDRESS = (HOST_NAME, PORT)
HEADER_LENGTH = 4
FORMAT = 'utf-8'
DISCONNECT_MESSAGE = '/leave'
DISCONNECT = 'LEAVE'
MAKE_EXIT = 'END'
USER_NAME_GET = 'GET_USERNAME'
USER_NAME_USED = 'USERNAME_IN_USE'

try:
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
except (socket.error, Exception) as err:
    print('Error occurred whilst attempting to create the client socket. (Error: {})'.format(str(err)))
    sys.exit(1)


# ------------------------------------- GUI Setup, with read/write methods ------------------------------------------- #

class GUI:
    def __init__(self) -> None:
        self.message = None
        self.username = None

        # Initialise tkinter instance
        self.root = tk.Tk()
        self.root.title('Chat Room')
        self.root.resizable(width=True, height=True)
        self.root.minsize(width=350, height=420)
        self.root.maxsize(width=1000, height=800)
        self.root.configure(width=700, height=500, bg='#ABB2B9')

        # A header that displays the server address, with a line beneath to separate
        self.head = tk.Label(self.root, bg='#17202A', fg='#EAECEE', pady=5, text='{}:{}'.format(HOST_NAME, PORT))
        self.head.place(relwidth=1)
        self.line = tk.Label(self.root, width=450, bg="#ABB2B9")
        self.line.place(relwidth=1, rely=0.07, relheight=0.012)

        # The chat area (received messages)
        self.chat_window = tk.Text(self.root, width=25, height=2, bg="#17202A", fg="#EAECEE",
                                   font="Helvetica 14",  padx=5, pady=5, wrap=tk.WORD)
        self.chat_window.place(relheight=0.75, relwidth=1, rely=0.07)

        # The message area (sending messages) and an input prompt
        self.message_window = tk.Label(self.root, bg='#ABB2B9', fg='white', height=80, text="WRITE MESSAGE HERE")
        self.message_window.place(relwidth=1, rely=0.8)
        self.input_prompt = tk.Label(self.message_window, bg='#ABB2B9', fg='#17202A',
                                     font=('Arial', 12), text='Input your message here:')
        self.input_prompt.place(relwidth=0.5, relheight=0.02, rely=0.004, relx=0.1)
        self.entry_message = tk.Entry(self.message_window, bg='black', fg='white')
        self.entry_message.place(relwidth=0.74, relheight=0.038, rely=0.028, relx=0.011)
        self.entry_message.focus()

        # "Write" button
        self.send_button = tk.Button(self.message_window, text='Write', bg='blue', activebackground='light blue',
                                     width=20, font=('Arial', 16),  height=5,
                                     command=lambda: self.send(self.entry_message.get()))
        self.send_button.place(relx=0.77, rely=0.006, relheight=0.06, relwidth=0.22)
        self.root.bind('<Return>', self.enter)

        # Begin receiving messages
        receive_thread = threading.Thread(target=self.receive)
        receive_thread.start()

        # Finalise initialisation
        self.root.mainloop()

    # Allow "enter" to be used for writing messages
    def enter(self, event=None) -> None:
        self.send(self.entry_message.get())

    # Function to begin the thread for writing messages
    def send(self, message: str) -> None:
        if len(message) != 0:
            self.chat_window.config(state=tk.DISABLED)
            self.message = message
            self.entry_message.delete(0, tk.END)
            write_thread = threading.Thread(target=self.write)
            write_thread.start()

    # Function for displaying a message in the chat window
    def display(self, message: str) -> None:
        self.chat_window.config(state=tk.NORMAL)
        self.chat_window.insert(tk.END, message + "\n")
        self.chat_window.config(state=tk.DISABLED)
        self.chat_window.see(tk.END)

    # Function for examining and handling messages received by the server
    def query_received_message(self, message: str) -> bool:
        connected = True
        if message == USER_NAME_GET:
            username = USER_NAME.encode(FORMAT)
            username_header = "{username_length:<{header_length}}" \
                .format(username_length=len(username), header_length=HEADER_LENGTH).encode(FORMAT)
            clientSocket.send(username_header + username)
        elif message == USER_NAME_USED:
            self.display('The username {} is already in use! '
                         'Please close the window then try again with a new one.'.format(USER_NAME))
            connected = False
        elif message == DISCONNECT:
            self.display('You have left the server. Please close the window.')
            connected = False
        elif message == MAKE_EXIT:
            ext = MAKE_EXIT.encode(FORMAT)
            ext_header = "{exit_length:<{header_length}}" \
                .format(exit_length=len(ext),
                        header_length=HEADER_LENGTH).encode(FORMAT)
            clientSocket.send(ext_header + ext)
            self.display('The server has forced your disconnection. Please close the window.')
            connected = False
        else:
            self.display(message)
        return connected

    # Function for receiving messages from the server, these could indicate commands or could broadcast messages.
    def receive(self) -> None:
        connected = True
        while connected:
            try:
                message_header = clientSocket.recv(HEADER_LENGTH)
                if len(message_header):
                    message_length = int(message_header.decode(FORMAT).strip())
                    message = clientSocket.recv(message_length).decode(FORMAT)
                    connected = self.query_received_message(message)
            except WindowsError:
                connected = False
            except Exception as e:
                print('An error occurred! (Error: {})'.format(str(e)))
                connected = False
        clientSocket.close()
        sys.exit(0)

    # Function for writing messages which will then be sent to the server and back to the clients.
    def write(self) -> None:
        self.chat_window.config(state=tk.DISABLED)
        connected = True
        while connected:
            try:
                message = self.message
                if message == DISCONNECT_MESSAGE:
                    connected = False
                encode_and_send(message)
                break
            except WindowsError:
                self.display('You are no longer connected to the server.')
                connected = False
            except Exception as e:
                self.display('Something unexpected went wrong, connection closing. (Error: {}.)'.format(str(e)))
                clientSocket.close()
                sys.exit(1)
        if not connected:
            sys.exit(0)


# ------------------------------------------------ Functions --------------------------------------------------------- #

def encode_and_send(message: str) -> None:
    encoded_message = message.encode(FORMAT)
    message_header = "{encoded_length:<{header_length}}"\
        .format(encoded_length=len(encoded_message), header_length=HEADER_LENGTH).encode(FORMAT)
    clientSocket.send(message_header + encoded_message)


def start_client() -> None:
    try:
        clientSocket.connect(ADDRESS)
    except (socket.gaierror, Exception) as e:
        print('Couldn\'t start client! Could not connect to the address {}:{}. '
              'Try a different hostname or port. (Error: {}.)'.format(HOST_NAME, PORT, str(e)))
        sys.exit(1)
    print('The client has begun in a separate window.')
    interface = GUI()
    if interface:   # Will only run when the GUI is closed
        print('Client closed.')
        try:        # If the GUI was closed without typing /leave
            encode_and_send(MAKE_EXIT)
        except WindowsError:     # Will except if /leave had been typed (so the client had "officially" left)
            print('You left the server.')
            sys.exit(0)
        print('You have forcefully left the server.')
        clientSocket.close()
        sys.exit(0)


# ---------------------------------------------- Commencement -------------------------------------------------------- #

if __name__ == "__main__":
    try:
        start_client()
    except KeyboardInterrupt:
        print("Keyboard Interrupt detected! Disconnecting from server...")
        clientSocket.close()
    except Exception as err:
        print("Unexpected error: {}".format(str(err)))
    sys.exit(0)
