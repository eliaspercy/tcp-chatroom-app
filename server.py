import socket
import sys
import threading
import logging


# ---------------------------------------------- INITIALISATION ------------------------------------------------------ #

HEADER_LENGTH = 4
FORMAT = 'utf-8'
DISCONNECT = 'LEAVE'
MAKE_EXIT = 'END'
USER_NAME_GET = 'GET_USERNAME'
USER_NAME_USED = 'USERNAME_IN_USE'


logging.basicConfig(filename='server.log', level=logging.INFO,
                    format='%(asctime)s: %(message)s', datefmt='%d/%m/%Y %I:%M:%S %p')

HOST_NAME = '127.0.0.1'  # IP

try:
    PORT = int(sys.argv[1])
except Exception as err:
    print('Couldn\'t start server! Ensure you include the port when starting the server. (Error: {})'.format(str(err)))
    sys.exit(1)

ADDRESS = (HOST_NAME, PORT)

try:
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Overcomes "address already in use" error
except socket.error as err:
    print('Error occurred whilst attempting to create the server socket. (Error: {})'.format(str(err)))
    sys.exit(1)

clients = set()
usernames = set()

commands = {"/rename": ("/rename [New Username]", "Function: Renames your username to [New Username]."),
            "/users": ("/users", "Function: Outputs a list of all users currently online."),
            "/whisper": ("/whisper [Username] [Message...]",
                         "Function: Sends a private message to [Username]. Remember, usernames are case sensitive."),
            "/help": ("/help [/command (optional)]", "Function: Returns information about a specified command; "
                      "if no command is specified then outputs a list of available commands. "
                      "Commands are case sensitive."),
            "/leave": ("/leave", "Function: Removes you from the server.")}


# --------------------------------------------------- Client Class --------------------------------------------------- #

# Class containing the essential information about all connected clients, and methods "invoked" by them
class Client:
    def __init__(self, client_socket: socket.socket, username: str, client_address: str) -> None:
        self.client_socket = client_socket
        self.username = username
        self.client_address = client_address

    def error_handle(self, command: str, error: Exception) -> None:
        send_server_message("An error occurred! The {} command has failed for unforeseen reasons.".format(command),
                            self.client_socket)
        log('[PROTOCOL ERROR] Error ({}) occurred after {} attempted the {} command.'
            .format(str(error), self.username, command))

    def param_error_handle(self, command: str) -> None:
        send_server_message('Invalid parameters! Ensure command is in the form: {}.'.format(commands[command][0]),
                            self.client_socket)
        log('[PROTOCOL ERROR] {} inputted the wrong parameters for the {} command.'.format(self.username, command))

    def send_all(self, message: str) -> None:
        log("[NEW MESSAGE] Received message from {}: {}".format(self.username, message))
        broadcast('{}> {}'.format(self.username, message))

    def change_username(self, new_username: str) -> None:
        if new_username == self.username:
            send_server_message('Your username is already set as {}!'.format(new_username), self.client_socket)
            log('[PROTOCOL ERROR] {} tried to change their username to their current username.'.format(self.username))
        elif new_username in usernames:
            send_server_message('There already exists a user called {}!'.format(new_username), self.client_socket)
            log('[PROTOCOL ERROR] {} tried to change their username to an existing one.'.format(self.username))
        elif not len(new_username):
            send_server_message('You can\'t change your username to nothing!', self.client_socket)
            log('[PROTOCOL ERROR] {} tried to change their username to nothing.'.format(self.username))
        else:
            usernames.remove(self.username)
            usernames.add(new_username)
            broadcast('The user {} has changed their username to {}.'.format(self.username, new_username))
            log('[USERNAME CHANGE] The user from {}:{} has changed their username from {} to {}.'
                .format(self.client_address[0], self.client_address[1], self.username, new_username))
            self.username = new_username

    def list_users(self) -> None:
        num_users = len(usernames)
        if num_users == 1:
            message = "There is only 1 user online: \n{}.".format(list(usernames)[0])
        else:
            message = "There are {} users currently online: ".format(str(num_users))
            for username in usernames:
                message += "\n{}".format(username)
        send_server_message(message, self.client_socket)
        log('[USER LIST] {} requested a list of users.'.format(self.username))

    def whisper(self, username: str, message: str) -> None:
        if username == self.username:
            send_server_message('You can\'t whisper to yourself!', self.client_socket)
            log('[PROTOCOL ERROR] {} tried to whisper to themself.'.format(self.username))
        elif username not in usernames:
            send_server_message('Could not locate the user {}! Type /users to see who is online.'.format(username),
                                self.client_socket)
            log('[PROTOCOL ERROR] {} tried to whisper to a non-existing user.'.format(self.username))
        elif len(message) == 0:
            send_server_message('You can\'t whisper nothing! Please include a message.', self.client_socket)
            log('[PROTOCOL ERROR] {} tried to whisper without including a message.'.format(self.username))
        else:
            to_client = [client for client in clients if client.username == username][0].client_socket
            send_server_message('From you to {}> {}'.format(username, message), self.client_socket)
            send_server_message('From {} to you> {}'.format(self.username, message), to_client)
            log('[WHISPER] {} whispered to {}: {}'.format(self.username, username, message))

    def help(self, command: str) -> None:
        if len(command):
            if command in commands:
                out = commands[command]
                send_server_message('Format: {}.\n{}'.format(out[0], out[1]), self.client_socket)
                log('[HELP] {} requested help for the {} command.'.format(self.username, command))
            else:
                send_server_message('/help command failed, {} is not a valid command!'.format(command),
                                    self.client_socket)
                log('[PROTOCOL ERROR] {} attempted to use the /help command on a non-existing command.'
                    .format(self.username))
        else:
            send_server_message("List of commands: /rename, /users, /whisper, /help, /leave.\n"
                                "Type /help [/command] for more info about that command.", self.client_socket)
            log('[HELP] {} used the /help command.'.format(self.username))

    def leave(self) -> None:
        send_server_message('Goodbye, {}.'.format(self.username), self.client_socket)
        send_server_message(DISCONNECT, self.client_socket)
        log('[LEAVE] {} used the /leave command.'.format(self.username))
        remove_client(self)

    # Function for distinguishing between the commands
    def query_message(self, message: str) -> None:
        if message[0] == '/':
            words = message.split(' ')
            try:
                if words[0] == '/rename':
                    if len(words) != 2:
                        self.param_error_handle('/rename')
                    else:
                        self.change_username(words[1])
                elif words[0] == '/users':
                    if len(words) > 1:
                        self.param_error_handle('/users')
                    else:
                        self.list_users()
                elif words[0] == '/whisper':
                    if len(words) < 3:
                        self.param_error_handle('/whisper')
                    else:
                        self.whisper(words[1], ' '.join(words[2:]))
                elif words[0] == '/help':
                    if len(words) == 2:
                        self.help(words[1])
                    elif len(words) == 1:
                        self.help('')
                    else:
                        self.param_error_handle('/help')
                elif words[0] == '/leave':
                    if len(words) > 1:
                        self.param_error_handle('leave')
                    else:
                        self.leave()
                else:
                    send_server_message('{} is not a valid command.'.format(words[0]), self.client_socket)
                    log('[PROTOCOL ERROR] {} attempted the command {}, which doesn\'t exist.'
                        .format(self.username, words[0]))
            except Exception as e:
                self.error_handle(words[0], e)
        else:
            try:
                self.send_all(message)
            except Exception as e:
                send_server_message('Something unforeseen went wrong whilst processing your message!',
                                    self.client_socket)
                log('[ERROR] Error occurred ({}) upon {} sending the message {}.'
                    .format(str(e), self.username, message))


# ------------------------------------------------- Server Functions ------------------------------------------------- #

# Log a message to server.log and print it to the console.
def log(message: str) -> None:
    print(message)
    logging.info(message)


# Send a message from the server to a single specified client.
def send_server_message(message: str, client_socket: socket.socket) -> None:
    encoded_message = message.encode(FORMAT)
    message_header = "{encoded_length:<{header_length}}"\
        .format(encoded_length=len(encoded_message), header_length=HEADER_LENGTH).encode(FORMAT)
    client_socket.send(message_header + encoded_message)


# Broadcast a message to all connected clients.
def broadcast(message: str) -> None:
    for client in clients:
        send_server_message(message, client.client_socket)


# Attempt to retrieve a message from a client.
def receive_message(client_socket: socket.socket) -> str or None:
    message_header = client_socket.recv(HEADER_LENGTH)
    if len(message_header):
        message_length = int(message_header.decode(FORMAT).strip())
        message = client_socket.recv(message_length).decode(FORMAT)
        return message


# Remove a client from the server (i.e., stop storing their data and close their socket.)
def remove_client(client: Client) -> None:
    usernames.remove(client.username)
    clients.remove(client)
    client.client_socket.close()
    broadcast('{} has left.'.format(client.username))
    log("[CONNECTION CLOSED] Closed connection from the user {} from {}:{}."
        .format(client.username, client.client_address[0], client.client_address[1]))


# Function for handling each individual client after they connect; the while loop will continue until the client leaves.
def client_handler(client: Client) -> None:
    connected = True
    while connected:
        try:
            message = receive_message(client.client_socket)
            if message[0] == '/':   # This indicates the user inputted, or attempted to input, a command.
                client.query_message(message)
                if client not in clients:    # Is True when a client has left.
                    connected = False
            elif message == MAKE_EXIT:
                try:
                    remove_client(client)
                except RuntimeError:
                    # Client already removed
                    pass
                connected = False
            elif message:
                log("[NEW MESSAGE] Received message from {}: {}".format(client.username, message))
                broadcast('{}> {}'.format(client.username, message))
        except WindowsError:  # Excepts when unable to receive message: the client must have forcefully disconnected.
            try:  # Attempt to remove the client from the database
                remove_client(client)
            except RuntimeError:  # Client already removed from database
                pass
            connected = False
    sys.exit(0)


def shut_down() -> None:
    broadcast('[SERVER WARNING] The server is now self destructing.')
    client_lst = list(clients)
    num_clients = len(client_lst)
    for client in client_lst:
        send_server_message(MAKE_EXIT, client.client_socket)
        while len(list(clients)) == num_clients:
            pass
        num_clients -= 1
    serverSocket.close()
    log('[SERVER CLOSED] The server has been closed.\n')


def kick_user(words: list) -> None:
    try:
        c = [client for client in clients if client.username == words[1]][0]
        log('[KICK] The user {} has been kicked from the server.'.format(c.username))
        send_server_message(MAKE_EXIT, c.client_socket)
    except IndexError:
        log('[ERROR] Kick failed as the user was not found.')


# Function to allow the server to send custom messages to the clients, kick clients, or shut the server down.
def server_write() -> None:
    running = True
    while running:
        message = input('')
        if not message:
            continue
        elif message[0] == '/':
            words = message.split(' ')
            if words[0] == '/end':   # move to shut_down_server
                shut_down()
                running = False
            elif words[0] == '/kick':
                kick_user(words)
            else:
                log('[ERROR] Server attempted to use an invalid command.')
        else:
            broadcast('[THE SERVER SPEAKS] {}'.format(message))
            log('[SERVER BROADCAST] The server broadcasted the message: {}'.format(message))
    sys.exit(0)


def collect_clients() -> None:
    running = True
    while running:
        try:
            client_socket, client_address = serverSocket.accept()
        except WindowsError:
            running = False
            continue

        send_server_message(USER_NAME_GET, client_socket)
        username = receive_message(client_socket)

        if username in usernames:
            send_server_message(USER_NAME_USED, client_socket)
            log("[ATTEMPTED CONNECTION] New connection attempted from {}:{} with the username '{}'. "
                "Rejected because the username is in use.".format(client_address[0], client_address[1], username))
            client_socket.close()
        elif username:     # Ensures the username is sent
            usernames.add(username)
            client = Client(client_socket, username, client_address)
            clients.add(client)

            log("[NEW CONNECTION] New connection accepted from {}:{} with the username '{}'."
                .format(client_address[0], client_address[1], username))
            send_server_message("You have successfully connected to the server, welcome!\n"
                                "Type /help for a list of commands.\n", client_socket)
            broadcast('{} has joined!'.format(username))

            try:
                client_thread = threading.Thread(target=client_handler, args=(client,))
                client_thread.start()
            except Exception as e:
                log('[ERROR] The server crashed! (Error: {}).'.format(str(e)))


def start_server() -> None:
    try:
        serverSocket.bind(ADDRESS)
        serverSocket.listen()
        log('[LISTENING] The server is listening on {}:{} and is ready to receive.'.format(HOST_NAME, PORT))
        server_thread = threading.Thread(target=server_write)
        server_thread.start()
        collect_clients()
    except KeyboardInterrupt:
        log('[KeyboardInterrupt] Keyboard Interrupt detected: shutting down server.\n')
        shut_down()
        sys.exit(0)
    except Exception as e:
        log('[ERROR] Unexpected error occurred! ({}). Attempting to shutting down server).\n'.format(str(e)))
        shut_down()
        sys.exit(1)
    sys.exit(0)


# ----------------------------------------------- Commencement ------------------------------------------------------- #

if __name__ == "__main__":
    try:
        log("[STARTING] The server is starting...")
        start_server()
    except Exception as err:
        log('[ERROR] Server couldn\'t start! (Error {}.)'.format(str(err)))
