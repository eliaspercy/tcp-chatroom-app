# PROTOCOL DOCUMENTATION

### The Protocol

The "messages" sent between the client and the server are encoded in the utf-8 format prior to being sent. The messages that are sent have two parts: the header and the data. The head will contain metadata about the message sent, specifically it contains the length of the original, nonencoded message in characterss. The maximum length of the header is 4 bytes, meaning it can indicate message lengths of up to 2147483647 chars. This header is important as upon receiving a message, the client or server will first extract the header (of known length) to observe the size of the original message, before extracting the original message with this size in mind. This ensures that the messages received will always be the correct length based on the messages sent.

Moreover, the content of the message could contain keywords that issue commands. A selection of these keywords is visible at the top of the code of the client and server as constants. For instance, if the client receives a message that is precisely 'LEAVE', the client will disconnect from the server. None of these keywords can be called by mistake, as all other messages will have certain prefixes enforced by the program.


On the server, custom messages can be sent (i.e., broadcasted) to all connected clients by simply inputting the message into the terminal. These will be encoded and sent to the clients, and then decoded and displayed in plain text to each. Furthermore, the server has access to two commands: the /end command, which will shut down the server after forcing all clients to leave, and the /kick command, which will kick a specified client from the server.

The clients can send messages containing basically anything, as long as they contain something (i.e., you can not send an empty message). These messages are first sent to the server, and then broadcasted to all of the clients, prefixed by the sender's username. Additonally, an array of commands are available to the user, all prefixed by the symbol '/'. So, to make a command, the client must type '/' followed by the command. A list of commands can be displayed by typing '/help'. The following is an exhaustive list of commands available to the clients, along with their expected responses.
- '/rename'   -- This will allow the user to change their username
- '/users'    -- This will show the user a list of the usernames of all connected clients
- '/whisper'  -- This allows the user to send a private message to another, specified user
- '/help'     -- This will show the user a list of available commands, and show the usage of specified ones
- '/leave'    -- This will disconnect the user from the server gracefully (note that the client can also disconnect "ungracefully", e.g. by closing the window or via a keyboard interrupt; these will be handled appropriately by the server.)

Whenever these commands are called, the messages are first sent to the server as usual, and the server will detect the '/' at the start of the decoded message. If the following command is not one of the above, or the usage is incorrect, the server will respond to the client who issued the command indicating so. Otherwise, the server will respond to the client abiding by the command. If the '/rename' or '/leave' commands are called, then the server will also broadcast to all of the clients that a user has changed their name, or they have left. When the '/whisper' command is called, the server will send a response to both the whisperer and the whisperee. The responses of all of the commands will depend on the state of the server.



### Design choices

The code itself generally follows the PEP8 standard (with a few exceptions, such as the maximum line length being increased from 79 to 120). On server.py, I used a class to represent each individual client as it is an intuitive way of storing the essential information for them and also allowed me to bind the heavily client-dependent methods (for the protocol) to each client. Furthermore, a class was used to represent the GUI for the client (which utilised tkinter due to its clarity and ease of use), which also contains the methods for writing to and reading from the server. The threading library was utilised due to for both the client and the server, and the logging library was used for the process of logging. Type hints were used to increase comprehensibility of the code, and a conscious effort was made to make variable, constant, and function names very clear and obvious.