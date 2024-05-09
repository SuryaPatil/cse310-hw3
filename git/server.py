'''
This module defines the behaviour of server in your Chat Application
'''
import sys
import getopt
import socket
import util
import logging

class Server:
    '''
    This is the main Server Class. You will write Server code inside this class.
    '''
    def __init__(self, dest, port, window):
        self.server_addr = dest
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(None)
        self.sock.bind((self.server_addr, self.server_port))
        self.users_dict = {}
    
    def join(self, username, addr):
        logger.debug(self.users_dict)
        if len(self.users_dict) >= util.MAX_NUM_CLIENTS:
            # The server has already MAX_NUM_CLIENTS, so it will reply with ERR_SERVER_FULL message and will print
            print("disconnected: server full")
            msg = util.make_message("err_server_full",2) 
            packet = util.make_packet(msg=msg).encode()
            self.sock.sendto(packet, addr)            

        elif username in self.users_dict:
            # The username is already taken by another client. In this case, the server will reply with
            # ERR_USERNAME_UNAVAILABLE message and will print:
            msg = util.make_message("err_username_unavailable",2) 
            packet = util.make_packet(msg=msg).encode()
            self.sock.sendto(packet, addr)
            print("disconnected: username not available")
            
        else:
            # The server allows the user to join the chat
            self.users_dict[username] = addr
            print("join:",username)
    
    def list(self, addr):
        s = "list: " # the string the server will respond with 
        list = [] # list of clients
        for user in self.users_dict:
            list.append(user)
            #if i == len
        sorted_list = sorted(list) # sort the list
        for user in sorted_list:
            s += user+" "
        res = s[0:len(s)-1] # remove the last space in the string
        logger.debug(res)

        # find the client who sent this unrecognized message
        sender = ""
        for key, value in self.users_dict.items():
            if value == addr:
                sender = key
        if sender == "": 
            logger.debug("sender username not found")
        else:
            print("request_users_list:",sender)

        msg = util.make_message("response_users_list",3, res) 
        packet = util.make_packet(msg=msg).encode()
        self.sock.sendto(packet, addr)

    def msg(self, addr, text, num_receivers):
        # find who sent the message
        sender = ""
        for key, value in self.users_dict.items():
            if value == addr:
                sender = key
        if sender == "":
             logger.debug("sender username not found")
        
        # get list of all recipients of the message
        receiver_list = []
        num_spaces = 0
        i = 0
        while num_spaces < 4 and i < len(text):
            if text[i] == ' ':
                num_spaces += 1
            i += 1  
        receiver_arr = text[i:].split(' ')
        for x in range(num_receivers):
            receiver_list.append(receiver_arr[x])
        logger.debug(receiver_list)

        # msg_text is the string we will send to all the recipients
        msg_text = str(num_receivers+1)+" "+sender+" "+text[i:]
        logger.debug(msg_text)
        print("msg:", sender)
        for user in receiver_list:
            user_addr = self.users_dict.get(user)
            msg = util.make_message("forward_message",4, msg_text) 
            packet = util.make_packet(msg=msg).encode()
            if user_addr == None:
                print("msg:",sender,"to non-existent user", user)
            else:
                self.sock.sendto(packet, user_addr)

            

    def unknown(self, addr):
        # find the client who sent this unrecognized message
        sender = ""
        for key, value in self.users_dict.items():
            if value == addr:
                sender = key
        if sender == "": 
            logger.debug("sender username not found")
        else:
            # remove sender from users dictionary
            del self.users_dict[sender]
            logger.debug("%s removed", sender)
            logger.debug(self.users_dict)
        print("disconnected:",sender,"sent unknown command")
        msg = util.make_message("err_unknown_message",2) 
        packet = util.make_packet(msg=msg).encode()
        self.sock.sendto(packet, addr)

    def start(self):
        '''
        Main loop.
        continue receiving messages from Clients and processing it.
        '''

        while True:
            # Receive the client packet along with the address it is coming from
            packet, address = self.sock.recvfrom(1024)

            parsed_pkt = util.parse_packet(packet.decode())
            
            msg_type_arr = parsed_pkt[2].split(' ')
            logger.debug(parsed_pkt)
            msg_type = msg_type_arr[0]
            
            if msg_type == "join":
                username = msg_type_arr[2]
                self.join(username, address)
            elif msg_type == "request_users_list":
                self.list(address)
            elif msg_type == "send_message":
                # parsed_pkt[2] contains the text of the message
                # msg_type_arr[3] represents how many recipients the message has
                self.msg(address, parsed_pkt[2], int(msg_type_arr[3]))
            elif msg_type == "disconnect":
                username = msg_type_arr[2]
                del self.users_dict[username]
                print("disconnected:",username)        
            elif msg_type == "unknown": # server receives a message it does not recognize
                self.unknown(address)




    #    raise NotImplementedError # remove it once u start your implementation

# Do not change below part of code

if __name__ == "__main__":
    def helper():
        '''
        This function is just for the sake of our module completion
        '''
        print("Server")
        print("-p PORT | --port=PORT The server port, defaults to 15000")
        print("-a ADDRESS | --address=ADDRESS The server ip or hostname, defaults to localhost")
        print("-w WINDOW | --window=WINDOW The window size, default is 3")
        print("-h | --help Print this help")

    try:
        OPTS, ARGS = getopt.getopt(sys.argv[1:],
                                   "p:a:w", ["port=", "address=","window="])
    except getopt.GetoptError:
        helper()
        exit()

    PORT = 15000
    DEST = "localhost"
    WINDOW = 3

    for o, a in OPTS:
        if o in ("-p", "--port="):
            PORT = int(a)
        elif o in ("-a", "--address="):
            DEST = a
        elif o in ("-w", "--window="):
            WINDOW = a

    SERVER = Server(DEST, PORT,WINDOW)
    try:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
        logger = logging.getLogger(__name__)
        # Disable DEBUG level logging for the root logger
        logging.getLogger().setLevel(logging.INFO)
        # Create a file handler
        # file_handler = logging.FileHandler('debug.log')
        # file_handler.setLevel(logging.DEBUG)  # Set the handler level to DEBUG

        # # Create a formatter and set it for the file handler
        # formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        # file_handler.setFormatter(formatter)

        # # Add the file handler to the logger
        # logger.addHandler(file_handler)
        SERVER.start()
    except (KeyboardInterrupt, SystemExit):
        exit()
