'''
This module defines the behaviour of a client in your Chat Application
'''
import sys
import getopt
import socket
import random
from threading import Thread
import os
import util
import logging
import time

'''
Write your code inside this class. 
In the start() function, you will read user-input and act accordingly.
receive_handler() function is running another thread and you have to listen 
for incoming messages in this function.
'''

class Client:
    '''
    This is the main Client Class. 
    '''
    def __init__(self, username, dest, port, window_size):
        self.server_addr = dest
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(None)
        self.sock.bind(('', random.randint(10000, 40000)))
        self.name = username
        self.running = True
        self.ack_received = False
        self.seq_num = 0 # The sequence number of each packet sent. This will be incremented each time a packet is sent

    def start(self):
        '''
        Main Loop is here
        Start by sending the server a JOIN message. 
        Use make_message() and make_util() functions from util.py to make your first join packet
        Waits for userinput and then process it
        '''
        try: 
            self.send_packet("join") # Begin by sending a join message

            while self.running:
                valid = True # Is the user input valid?
                # Wait for user input
                user_input = input()
                input_arr = user_input.split(' ')
                msg = None

                # check the first word in the user input and make the appropriate message
                if input_arr[0] == "list":
                    self.send_packet("list")
                elif input_arr[0] == "msg":
                    self.send_packet(user_input)
                elif input_arr[0] == "quit":
                    self.send_packet("quit")
                elif input_arr[0] == "help":
                    s = '''1) msg <number_of_users> <username1> <username2> ... <message>
2) list
3) help
4) quit'''
                    print(s)
                else:
                    valid = False

                # if self.running and valid: # If socket is still open and input is valid, send the packet
                #     self.sock.sendto(packet, (self.server_addr, self.server_port)) 
                #     if input_arr[0] == "quit": # if the user input was to quit, exit the program
                #         print("quitting")
                #         sys.exit()
                # else:
                if not self.running:
                    logger.debug("breaking...")
                    break
                if not valid:
                    print("incorrect userinput format")
                
        except OSError:
            logger.debug("OS Error")
            sys.exit()

    # helper function that sends data in chunks and waits for ack before sending next packet
    # @user_input: the command the user entered into the CLI (JOIN, MSG, LIST, QUIT)
    def send_packet(self, user_input):
        seq_num = random.randint(100, 499) # The sequence number of each packet sent. This will be incremented each time a packet is sent
        packet = util.make_packet(msg_type="start", seqno=seq_num).encode() # To start a connection, send a START packet
        self.sock.sendto(packet, (self.server_addr, self.server_port)) # send the packet

        start_time = time.time()
        while not self.ack_received: # wait for the ack from the server
            if time.time() - start_time >= util.TIME_OUT:
                j = 0
                # Timeout occurred
                #logger.debug("***Timeout occurred while waiting for ack.***")
                #self.sock.sendto(packet, (self.server_addr, self.server_port)) # resend the packet
            pass
        self.ack_received = False
        
        logger.debug("passed start loop")
        msg = None
        if user_input == "join":
            msg = util.make_message(user_input,1, self.name)
        elif user_input == "list":
            msg = util.make_message("request_users_list",2)
        elif user_input == "quit":
            msg = util.make_message("disconnect",1, self.name) 
        elif user_input[0:3] == "msg":
            msg = util.make_message("send_message",4, user_input) 
        chunks = [msg[i:i+util.CHUNK_SIZE] for i in range(0, len(msg), util.CHUNK_SIZE)] # Split the user input message into chunks
        for chunk in chunks:
            logger.debug("chunk: %s",chunk)
            seq_num += 1 # seq_num should be incremented for each additional packet sent
            packet = util.make_packet(msg_type="data",msg=chunk, seqno=seq_num).encode() # send messages in the format of a header, followed by a chunk of data
            self.sock.sendto(packet, (self.server_addr, self.server_port)) # send the packet

            start_time = time.time()
            while not self.ack_received: # wait for the ack from the server
                if time.time() - start_time >= util.TIME_OUT:
                    j = 0
                    # Timeout occurred
                    logger.debug("***Timeout occurred while waiting for data ack.***")
                    self.sock.sendto(packet, (self.server_addr, self.server_port)) # resend the packet
                pass
            self.ack_received = False

        seq_num += 1 # increment seq_num 
        logger.debug("passed initial data loop")
        packet = util.make_packet(msg_type="end", seqno=seq_num).encode() # After transmitting the entire message, send END packet to 
                                                                                # to mark end of the connection 
        self.sock.sendto(packet, (self.server_addr, self.server_port)) # send the packet
        start_time = time.time()
        while not self.ack_received: # wait for the ack from the server
            if time.time() - start_time >= util.TIME_OUT:
                # Timeout occurred
                #logger.debug("***Timeout occurred while waiting for end ack.***")
                self.sock.sendto(packet, (self.server_addr, self.server_port)) # resend the packet
            pass

        if user_input == "quit":
            print("quitting")
            sys.exit()

    def receive_handler(self):
        '''
        Waits for a message from server and process it accordingly
        '''

        while True:
            #logger.debug("waiting for message...")
            packet, address = self.sock.recvfrom(1024)
            #logger.debug(packet)
            msg_type, seqno, data, checksum = util.parse_packet(packet.decode())
            #logger.debug(data)
            if msg_type == "ack":
                #logger.debug("received ack")
                self.ack_received = True
                continue
            msg_type_arr = data.split(' ')
          #  logger.debug(data)
          #  logger.debug(msg_type_arr)
            
            msg = msg_type_arr[0]
            if msg == "err_server_full":
                print("disconnected: server full")
                self.running = False  # Set the shutdown flag
                self.sock.close()
                sys.exit() # program still runs for some reason
                
            #     self.sock.shutdown(socket.SHUT_WR)
            elif msg == "err_username_unavailable":
                print("disconnected: username not available")
                self.running = False  # Set the shutdown flag
                self.sock.close()
                sys.exit() # program still runs for some reason
                
            elif msg == "response_users_list":
                num_spaces = 0
                i = 0
                while num_spaces < 2:
                    if data[i] == ' ':
                        num_spaces += 1
                    i += 1 
                print(data[i:])
            elif msg == "forward_message":
                num_spaces = 0
                i = 0
                num_users = msg_type_arr[2]
                while num_spaces < int(num_users)+3:
                    if data[i] == ' ':
                        num_spaces += 1
                    i += 1 
                sender = msg_type_arr[3]
                print("msg:",sender+":",data[i:])
            elif msg == "err_unknown_message":
                print("disconnected: server received an unknown command")
                self.running = False  # Set the shutdown flag
                self.sock.close()
                sys.exit() # program still runs for some reason


# Do not change below part of code
if __name__ == "__main__":
    def helper():
        '''
        This function is just for the sake of our Client module completion
        '''
        print("Client")
        print("-u username | --user=username The username of Client")
        print("-p PORT | --port=PORT The server port, defaults to 15000")
        print("-a ADDRESS | --address=ADDRESS The server ip or hostname, defaults to localhost")
        print("-w WINDOW_SIZE | --window=WINDOW_SIZE The window_size, defaults to 3")
        print("-h | --help Print this help")
    try:
        OPTS, ARGS = getopt.getopt(sys.argv[1:],
                                   "u:p:a:w", ["user=", "port=", "address=","window="])
    except getopt.error:
        helper()
        exit(1)

    PORT = 15000
    DEST = "localhost"
    USER_NAME = None
    WINDOW_SIZE = 3
    for o, a in OPTS:
        if o in ("-u", "--user="):
            USER_NAME = a
        elif o in ("-p", "--port="):
            PORT = int(a)
        elif o in ("-a", "--address="):
            DEST = a
        elif o in ("-w", "--window="):
            WINDOW_SIZE = a

    if USER_NAME is None:
        print("Missing Username.")
        helper()
        exit(1)

    S = Client(USER_NAME, DEST, PORT, WINDOW_SIZE)
    try:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(message)s Line %(lineno)d')
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

        # Start receiving Messages
        T = Thread(target=S.receive_handler)
        T.daemon = True
        T.start()
        # Start Client
        S.start()
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
