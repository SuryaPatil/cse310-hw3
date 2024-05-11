'''
This module defines the behaviour of server in your Chat Application
'''
import sys
import getopt
import socket
import util
import logging
import time
import queue
import threading
import random 

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
        self.users_dict = {} # map usernames to addresses
        self.messageQueue = queue.Queue() # messages from all clients are stored here
        self.messages = {} # map addresses to messages
        self.received_acks = {} # map client addresses to booleans. 
                                # Boolean = whether or not the most recent packet the server sent was ack'd by the client
    
    def join(self, username, addr):
        logger.debug(self.users_dict)
        if len(self.users_dict) >= util.MAX_NUM_CLIENTS:
            # The server has already MAX_NUM_CLIENTS, so it will reply with ERR_SERVER_FULL message and will print
            print("disconnected: server full")
            msg = util.make_message("err_server_full",2) 
            #packet = util.make_packet(msg=msg).encode()
            #self.sock.sendto(packet, addr)   
            self.send_packet(msg, addr)         

        elif username in self.users_dict:
            # The username is already taken by another client. In this case, the server will reply with
            # ERR_USERNAME_UNAVAILABLE message and will print:
            msg = util.make_message("err_username_unavailable",2) 
            #packet = util.make_packet(msg=msg).encode()
            #self.sock.sendto(packet, addr)
            self.send_packet(msg, addr)
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
     #   logger.debug(res)

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
        #packet = util.make_packet(msg=msg).encode()
        #self.sock.sendto(packet, addr)
        self.send_packet(msg, addr)

    # @addr: address of the sender
    # @text: the command the sender entered into the CLI
    # @num_receivers: The number of users the client wants to send the message to
    def msg(self, addr, text, num_receivers):
        logger.debug("text: %s",text)
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
            #packet = util.make_packet(msg=msg).encode()
            if user_addr == None:
                print("msg:",sender,"to non-existent user", user)
            else:
                t1 = threading.Thread(target=self.send_packet, args=(msg, user_addr,)) # make a thread for each client you have to forward the message to
                t1.start()
                #self.sock.sendto(packet, user_addr)

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

    # helper function that sends data in chunks and waits for ack before sending next packet
    # @msg: the message the sender will send; output of make_message() from function caller
    def send_packet(self, msg, addr):
        seq_num = random.randint(100, 499) # The sequence number of each packet sent. This will be incremented each time a packet is sent 
        packet = util.make_packet(msg_type="start", seqno=seq_num).encode() # To start a connection, send a START packet
        self.sock.sendto(packet, addr) # send the packet
        logger.debug("server sent start msg %d", seq_num)

        self.received_acks[addr] = False 
        while not self.received_acks[addr]: # wait for the ack from the client
            pass
        self.received_acks[addr] = False
        
        logger.debug("server passed start loop")
        chunks = [msg[i:i+util.CHUNK_SIZE] for i in range(0, len(msg), util.CHUNK_SIZE)] # Split the user input message into chunks
        i = 1
        for chunk in chunks:
          #  logger.debug("chunk %d: %s",i,chunk)
            i += 1
            seq_num += 1 # seq_num should be incremented for each additional packet sent
            packet = util.make_packet(msg_type="data",msg=chunk, seqno=seq_num).encode() # send messages in the format of a header, followed by a chunk of data
            self.sock.sendto(packet, addr) # send the packet

          #  parsed_pkt = util.parse_packet(packet.decode())
          #  logger.debug("client msg chunk: %s", parsed_pkt)
            while not self.received_acks[addr]: 
                pass
            self.received_acks[addr] = False

        seq_num += 1 # increment seq_num 
        logger.debug("server passed initial data loop")
        packet = util.make_packet(msg_type="end", seqno=seq_num).encode() # After transmitting the entire message, send END packet to 
                                                                          # to mark end of the connection 
        self.sock.sendto(packet, addr) # send the packet
        while not self.received_acks[addr]:
            pass
        logger.debug("server passed end loop")

    def handle_pkt(self):
        while True:
            while not self.messageQueue.empty():
                packet, address = self.messageQueue.get()
                parsed_pkt = util.parse_packet(packet.decode())
                logger.debug(parsed_pkt) 

                pkt_type = parsed_pkt[0] # obtain the packet type ("start", ack, "data", or "end")
                seqno = int(parsed_pkt[1]) # obtain the sequence number
                
                decoded_pkt = packet.decode()
                logger.debug("decoded packet: %s", decoded_pkt)
               # if not util.validate_checksum(decoded_pkt):
                #    logger.debug("*** Checksum invalid. Must discard packet. Calculated: %s, field: %s ***",  parsed_pkt[2])
                   # continue # discard the packet if checksum is invalid (don't send an ack)

                msg_type_arr = ""
                msg_type = ""

                if pkt_type == "ack":
                    logger.debug("server received ack")  
                    self.received_acks[address] = True # Set to True, because we received an ack from the client
                    continue
                if pkt_type == "start":
                    packet = util.make_packet(msg_type="ack", seqno=seqno+1).encode() # ack client's start packet
                    self.messages[address] = "" # start constructing a new message for this connection
                    self.sock.sendto(packet, address) # send the ack
                    logger.debug("start ack sent %s", seqno+1)
                    continue
                elif pkt_type == "data":
                    #logger.debug("msg chunk: %s", parsed_pkt[2])
                    self.messages[address] += parsed_pkt[2] # append the message chunk to the message
                    packet = util.make_packet(msg_type="ack", seqno=seqno+1).encode() # ack client's start packet
                    self.sock.sendto(packet, address)
                    logger.debug("data ack sent %s", seqno+1)
                    continue
                elif pkt_type == "end":
                    packet = util.make_packet(msg_type="ack", seqno=seqno+1).encode() # ack client's start packet
                    self.sock.sendto(packet, address)
                    logger.debug("end ack sent %s", seqno+1)
                    logger.debug("complete message from client: %s", self.messages[address])
                    msg_type_arr = self.messages[address].split(' ')
                    msg_type = msg_type_arr[0]

                #logger.debug("msg_type_arr: %s", msg_type_arr)
                #logger.debug("msg_type: %s", msg_type)
                if msg_type == "join":
                    username = msg_type_arr[2]
                    #self.join(username, address)
                    t1 = threading.Thread(target=self.join, args=(username, address,))
                    t1.start()
                elif msg_type == "request_users_list":
                    #self.list(address)
                    t1 = threading.Thread(target=self.list, args=(address,))
                    t1.start()
                elif msg_type == "send_message":
                    # parsed_pkt[2] contains the text of the message
                    # msg_type_arr[3] represents how many recipients the message has
                    self.msg(address, self.messages[address], int(msg_type_arr[3]))
                elif msg_type == "disconnect":
                    username = msg_type_arr[2]
                    del self.users_dict[username]
                    print("disconnected:",username)        
                elif msg_type == "unknown": # server receives a message it does not recognize
                    self.unknown(address)
                #self.messageQueue.task_done() # I retrieved the information from the list, but I’ve finished with it

    def read(self):
        while True:
            # Receive the client packet along with the address it is coming from
            packet, address = self.sock.recvfrom(5000)
            self.messageQueue.put((packet, address)) # put the message in the message queue        
    def start(self):
        '''
        Main loop.
        continue receiving messages from Clients and processing it.
        '''
        t1 = threading.Thread(target=SERVER.read) # puts messages into message queue
        t2 = threading.Thread(target=SERVER.handle_pkt) # reads from message queue and writes responses to the client 

        t1.start()
        t2.start()
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
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(message)s Line %(lineno)d')
        logger = logging.getLogger(__name__)
        # Disable DEBUG level logging for the root logger
       # logging.getLogger().setLevel(logging.INFO)
        # Create a file handler
        # file_handler = logging.FileHandler('debug.log')
        # file_handler.setLevel(logging.DEBUG)  # Set the handler level to DEBUG

        # # Create a formatter and set it for the file handler
        # formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        # file_handler.setFormatter(formatter)

        # # Add the file handler to the logger
        # logger.addHandler(file_handler)
        # t1 = threading.Thread(target=SERVER.start) # puts messages into message queue
        # t2 = threading.Thread(target=SERVER.handle_pkt) # reads from message queue and writes responses to the client 

        # t1.start()
        # t2.start()
        SERVER.start()
    except (KeyboardInterrupt, SystemExit):
        exit()
