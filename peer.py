'''
    ##  Implementation of peer
    ##  Each peer has a client and a server side that runs on different threads
    ##  150114822 - Eren Ulaş
'''
from socket import *
import threading
import time
import select
import logging
from re import search
import netifaces as ni
import pickle
from tabulate import tabulate 
terminate=threading.Event()
terminate.clear()

server_responses = {
        "REGISTER": {110: "110 REGSUC",
                    150: "150 REGDATAERR",
                    151: "150 REGNAMEUSD"
                    },
        "LOGIN":    {111: "111 LOGGEDSUC",
                    112: "112 ALREADYLOGGEDIN",
                    152: "152 UNAUTHORIZED",
                    154: "154 ACCNOTFOUND"
                    },
        "LOGOUT":   {114: "114 LOGGEDOUT",
                    157: "157 USERNOTLOGGEDIN"
                    }
}




class udpReciever(threading.Thread):
    def __init__(self, udpServerPort):
        threading.Thread.__init__(self)
        self.udpServerPort = udpServerPort
        self.udpServerSocket = socket(AF_INET, SOCK_DGRAM)
        self.udpServerSocket.bind((gethostname(), self.udpServerPort))
        self.udpServerSocket.setblocking(0)
        self.isOnline = True
        self.db = self.client['p2p-chat']
        self.db.online_peers.delete_many({})
        self.db.rooms.delete_many({})
        self.db.online_rooms.delete_many({})
        self.db.room_members.delete_many({})
        self.db.room_messages.delete_many({})
        self.db.room_requests.delete_many({})
        self.db.room_join_requests.delete_many({})

# Server side of peer
class PeerServer(threading.Thread):


    # Peer server initialization
    def __init__(self, username, peerServerPort, udpServerPort):
        threading.Thread.__init__(self)
        # keeps the username of the peer
        self.username = username
        # tcp socket for peer server
        self.tcpServerSocket = socket(AF_INET, SOCK_STREAM)
        # port number of the peer server
        self.peerServerPort = peerServerPort

        self.udpServerPort = udpServerPort
        self.udp_receiver = None    
        # if 1, then user is already chatting with someone
        # if 0, then user is not chatting with anyone
        self.isChatRequested = 0
        # keeps the socket for the peer that is connected to this peer
        self.connectedPeerSocket = None
        # keeps the ip of the peer that is connected to this peer's server
        self.connectedPeerIP = None
        # keeps the port number of the peer that is connected to this peer's server
        self.connectedPeerPort = None
        # online status of the peer
        self.isOnline = True
        # keeps the username of the peer that this peer is chatting with
        self.chattingClientName = None
    

    # main method of the peer server thread
    def run(self):

        print("Peer server started...")    

        # gets the ip address of this peer
        # first checks to get it for windows devices
        # if the device that runs this application is not windows
        # it checks to get it for macos devices
        hostname=gethostname()
        try:
            self.peerServerHostname=gethostbyname(hostname)
        except gaierror:
            import netifaces as ni
            self.peerServerHostname = ni.ifaddresses('en0')[ni.AF_INET][0]['addr']
        print(self.udpServerPort)
        
        self.udp_receiver = UDPReceiver(self.peerServerHostname, self.udpServerPort)
        # ip address of this peer
        #self.peerServerHostname = 'localhost'
        # socket initializations for the server of the peer
        self.tcpServerSocket.bind((self.peerServerHostname, self.peerServerPort))
        self.tcpServerSocket.listen(4)
        # inputs sockets that should be listened
        inputs = [self.tcpServerSocket,self.udp_receiver.udpServerSocket]
        # server listens as long as there is a socket to listen in the inputs list and the user is online
        while inputs and self.isOnline:
            # monitors for the incoming connections
            try:
                readable, writable, exceptional = select.select(inputs, [], [])
                # If a server waits to be connected enters here
                for s in readable:
                    # if the socket that is receiving the connection is 
                    # the tcp socket of the peer's server, enters here
                    if s is self.tcpServerSocket:
                        # accepts the connection, and adds its connection socket to the inputs list
                        # so that we can monitor that socket as well
                        connected, addr = s.accept()
                        connected.setblocking(0)
                        inputs.append(connected)
                        # if the user is not chatting, then the ip and the socket of
                        # this peer is assigned to server variables
                        if self.isChatRequested == 0:     
                            print(self.username + " is connected from " + str(addr))
                            self.connectedPeerSocket = connected
                            self.connectedPeerIP = addr[0]
                    # if the socket that receives the data is the one that
                    # is used to communicate with a connected peer, then enters here
                    elif s is self.udp_receiver.udpServerSocket:
                        self.udp_receiver.run()
                    else:
                        # message is received from connected peer
                        messageReceived = s.recv(1024).decode()
                        # logs the received message
                        logging.info("Received from " + str(self.connectedPeerIP) + " -> " + str(messageReceived))
                        # if message is a request message it means that this is the receiver side peer server
                        # so evaluate the chat request
                        if len(messageReceived) > 11 and messageReceived[:12] == "CHAT-REQUEST":
                            # text for proper input choices is printed however OK or REJECT is taken as input in main process of the peer
                            # if the socket that we received the data belongs to the peer that we are chatting with,
                            # enters here
                            if s is self.connectedPeerSocket:
                                # parses the message
                                messageReceived = messageReceived.split()
                                # gets the port of the peer that sends the chat request message
                                self.connectedPeerPort = int(messageReceived[1])
                                # gets the username of the peer sends the chat request message
                                self.chattingClientName = messageReceived[2]
                                # prints prompt for the incoming chat request
                                print("Incoming chat request from " + self.chattingClientName + " >> ")
                                print("Enter OK to accept or REJECT to reject:  ")
                                # makes isChatRequested = 1 which means that peer is chatting with someone
                                self.isChatRequested = 1
                            # if the socket that we received the data does not belong to the peer that we are chatting with
                            # and if the user is already chatting with someone else(isChatRequested = 1), then enters here
                            elif s is not self.connectedPeerSocket and self.isChatRequested == 1:
                                # sends a busy message to the peer that sends a chat request when this peer is 
                                # already chatting with someone else
                                message = "BUSY"
                                s.send(message.encode())
                                # remove the peer from the inputs list so that it will not monitor this socket
                                inputs.remove(s)

                        
                        elif messageReceived[:9] == "JOIN-ROOM":
                            messageReceived = messageReceived.split()
                            print("Incoming Room-request to Room: " + messageReceived[1] + " From: "+ messageReceived[2]+ " >> ")
                            print("Enter YES to accept or NO to reject:  ")
                            self.isChatRequested = 0
                            inputs.remove(s)


                        # if an OK message is received then ischatrequested is made 1 and then next messages will be shown to the peer of this server
                        elif messageReceived == "OK":
                            self.isChatRequested = 1
                        # if an REJECT message is received then ischatrequested is made 0 so that it can receive any other chat requests
                        elif messageReceived == "REJECT":
                            self.isChatRequested = 0
                            inputs.remove(s)
                        # if a message is received, and if this is not a quit message ':q' and 
                        # if it is not an empty message, show this message to the user
                        
                        

                        elif messageReceived[:2] != ":q" and len(messageReceived)!= 0:
                            print("\n" + self.chattingClientName + ": " + messageReceived)
                        # if the message received is a quit message ':q',
                        # makes ischatrequested 1 to receive new incoming request messages
                        # removes the socket of the connected peer from the inputs list
                        elif messageReceived[:2] == ":q":
                            self.isChatRequested = 0
                            inputs.clear()
                            inputs.append(self.tcpServerSocket)
                            # connected peer ended the chat
                            if len(messageReceived) == 2:
                                print("User you're chatting with ended the chat")
                                print("Press enter to quit the chat: ")
                        # if the message is an empty one, then it means that the
                        # connected user suddenly ended the chat(an error occurred)
                        elif len(messageReceived) == 0:
                            self.isChatRequested = 0
                            inputs.clear()
                            inputs.append(self.tcpServerSocket)
                            print("User you're chatting with suddenly ended the chat")
                            print("Press enter to quit the chat: ")
            # handles the exceptions, and logs them
            except OSError as oErr:
                logging.error("OSError: {0}".format(oErr))
            except ValueError as vErr:
                logging.error("ValueError: {0}".format(vErr))
            

class UDPReceiver(threading.Thread):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(UDPReceiver, cls).__new__(cls)
        return cls._instance

    def __init__(self, peerServerHostname, udpServerPort):
        if not getattr(self, '_initialized', False):
            threading.Thread.__init__(self)
            self.udpServerSocket = socket(AF_INET, SOCK_DGRAM)
            self.udpServerSocket.bind((peerServerHostname, udpServerPort))
            self.unread_messages = []
            self.in_this_room = False
            self.room_name = None
            self.sender_colors = {}
            self._initialized = True

    def run(self):
        print("UDP Receiver started...")
        response = self.udpServerSocket.recvfrom(1024)
        print('recievesddsad message')
        response = pickle.loads(response[0])
        # Assign a color to the sender if they don't have one yet

        if self.in_this_room and self.room_name:
            print(response["sender"] + ": " + response["message"])
        else:
            print('\033[A' + ' ' * len("Enter your choice:") + '\033[A', end='', flush=True)
            print()
            print(f"received message from {response['sender']} in room {response['room_name']}")
            self.unread_messages.append(response)
            print("Enter your choice:")
    def print_unread_messages(self):
        for message in self.unread_messages:
            color = self.sender_colors[message["sender"]]
            print(f"{message['sender']}: {message['message']}")
            self.unread_messages.remove(message)




# Client side of peer
class PeerClient(threading.Thread):
    # variable initializations for the client side of the peer
    def __init__(self, ipToConnect, portToConnect, username, peerServer, responseReceived):
        threading.Thread.__init__(self)
        # keeps the ip address of the peer that this will connect
        self.ipToConnect = ipToConnect
        # keeps the username of the peer
        self.username = username
        # keeps the port number that this client should connect
        self.portToConnect = portToConnect
        # client side tcp socket initialization
        self.tcpClientSocket = socket(AF_INET, SOCK_STREAM)
        # keeps the server of this client
        self.peerServer = peerServer
        # keeps the phrase that is used when creating the client
        # if the client is created with a phrase, it means this one received the request
        # this phrase should be none if this is the client of the requester peer
        self.responseReceived = responseReceived
        # keeps if this client is ending the chat or not
        self.isEndingChat = False


    # main method of the peer client thread
    def run(self):
        print("Peer client started...")
        # connects to the server of other peer
        self.tcpClientSocket.connect((self.ipToConnect, self.portToConnect))
        # if the server of this peer is not connected by someone else and if this is the requester side peer client then enters here
        if self.peerServer.isChatRequested == 0 and self.responseReceived is None:
            # composes a request message and this is sent to server and then this waits a response message from the server this client connects
            requestMessage = "CHAT-REQUEST " + str(self.peerServer.peerServerPort)+ " " + self.username
            # logs the chat request sent to other peer
            logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> " + requestMessage)
            # sends the chat request
            self.tcpClientSocket.send(requestMessage.encode())
            print("Request message " + requestMessage + " is sent...")
            # received a response from the peer which the request message is sent to
            self.responseReceived = self.tcpClientSocket.recv(1024).decode()
            # logs the received message
            logging.info("Received from " + self.ipToConnect + ":" + str(self.portToConnect) + " -> " + self.responseReceived)
            print("Response is " + self.responseReceived)
            # parses the response for the chat request
            self.responseReceived = self.responseReceived.split()
            # if response is ok then incoming messages will be evaluated as client messages and will be sent to the connected server
            if self.responseReceived[0] == "OK":
                # changes the status of this client's server to chatting
                self.peerServer.isChatRequested = 1
                # sets the server variable with the username of the peer that this one is chatting
                self.peerServer.chattingClientName = self.responseReceived[1]
                # as long as the server status is chatting, this client can send messages
                while self.peerServer.isChatRequested == 1:
                    # message input prompt
                    messageSent = input(self.username + ": ")
                    # sends the message to the connected peer, and logs it
                    self.tcpClientSocket.send(messageSent.encode())
                    logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> " + messageSent)
                    # if the quit message is sent, then the server status is changed to not chatting
                    # and this is the side that is ending the chat
                    if messageSent == ":q":
                        self.peerServer.isChatRequested = 0
                        self.isEndingChat = True
                        break
                # if peer is not chatting, checks if this is not the ending side
                if self.peerServer.isChatRequested == 0:
                    if not self.isEndingChat:
                        # tries to send a quit message to the connected peer
                        # logs the message and handles the exception
                        try:
                            self.tcpClientSocket.send(":q ending-side".encode())
                            logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> :q")
                        except BrokenPipeError as bpErr:
                            logging.error("BrokenPipeError: {0}".format(bpErr))
                    # closes the socket
                    self.responseReceived = None
                    self.tcpClientSocket.close()
            # if the request is rejected, then changes the server status, sends a reject message to the connected peer's server
            # logs the message and then the socket is closed       
            elif self.responseReceived[0] == "REJECT":
                self.peerServer.isChatRequested = 0
                print("client of requester is closing...")
                self.tcpClientSocket.send("REJECT".encode())
                logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> REJECT")
                self.tcpClientSocket.close()
            # if a busy response is received, closes the socket
            elif self.responseReceived[0] == "BUSY":
                print("Receiver peer is busy")
                self.tcpClientSocket.close()
        # if the client is created with OK message it means that this is the client of receiver side peer
        # so it sends an OK message to the requesting side peer server that it connects and then waits for the user inputs.
        elif self.responseReceived == "OK":
            # server status is changed
            self.peerServer.isChatRequested = 1
            # ok response is sent to the requester side
            okMessage = "OK"
            self.tcpClientSocket.send(okMessage.encode())
            logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> " + okMessage)
            print("Client with OK message is created... and sending messages")
            # client can send messsages as long as the server status is chatting
            while self.peerServer.isChatRequested == 1:
                # input prompt for user to enter message
                messageSent = input(self.username + ": ")
                self.tcpClientSocket.send(messageSent.encode())
                logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> " + messageSent)
                # if a quit message is sent, server status is changed
                if messageSent == ":q":
                    self.peerServer.isChatRequested = 0
                    self.isEndingChat = True
                    break
            # if server is not chatting, and if this is not the ending side
            # sends a quitting message to the server of the other peer
            # then closes the socket
            if self.peerServer.isChatRequested == 0:
                if not self.isEndingChat:
                    self.tcpClientSocket.send(":q ending-side".encode())
                    logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> :q")
                self.responseReceived = None
                self.tcpClientSocket.close()
                
    def join_request(self, room_name, username):
        self.tcpClientSocket.connect((self.ipToConnect, self.portToConnect))
        message = "JOIN-ROOM " + room_name + " " + username
        logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode().split()
        if response[0] == "Join-succ":
            print("Room Joining is successful...")
            sender_socket = socket(AF_INET, SOCK_STREAM)
            sender_socket.connect((gethostname(), 15600))
            regmessage = "JOIN-succ " + room_name + " " + username
            sender_socket.send(regmessage.encode())
            sender_socket.close()
            self.tcpClientSocket.close()
            
        if response[0] == "Join-fail":
            print("Joining the room failed...")
            self.tcpClientSocket.close()
            logging.info("Received from " + self.ipToConnect + ":" + str(self.portToConnect) + " -> " + " ".join(response))
        
class ClientRoom(threading.Thread):
    def __init__(self, room_name, owner, members, peerServer , originalThrd):
        threading.Thread.__init__(self)
        self.room_name = room_name                          # room name  
        self.owner = owner                                  # room owner
        self.members = members                              # this peer's client ip address will connect
        self.online_members = []                            
        self.members_ips = []                               # list of ips of members
        self.udpClientSocket = socket(AF_INET, SOCK_DGRAM)  # this peer's client udp socket
        self.peerServer = peerServer           # this peer's server
        self.originalThrd :peerMain = originalThrd                        # main thread of the peer
        self.isEndingChat = False                           # this is set to true when the user ends the chat

    # main method of the peer client room thread
    def run(self):
        print("Peer client room started...")
        self.peerServer.udp_receiver.print_unread_messages()
        while not self.isEndingChat:
            # message input prompt
            message = input()
            print('\033[A' + ' ' * len(message) + '\033[A', end='', flush=True)
            print()
            self.online_members = self.originalThrd.get_UDP_ports(self.room_name)
            if message == ":q":
                self.isEndingChat = True
                self.peerServer.udp_receiver.in_this_room = False
                self.peerServer.udp_receiver.room_name = None
                break
            if message:
                print(self.originalThrd.loginCredentials[0] + ": " + message)
                messageSent = {
                    "room_name": self.room_name,
                    "sender": self.originalThrd.loginCredentials[0],
                    "message": message
                }
                messageSent = pickle.dumps(messageSent)
                for member in self.online_members:
                    member_port = member
                    # print(member_ip, member_port, self.peerServer.udpServerPort)
                    if int(member_port) != self.originalThrd.udpServerPort:
                        member_port = int(member_port)
                        # Create a new UDP socket for each member
                        sock = socket(AF_INET, SOCK_DGRAM)
                        sock.sendto(messageSent, (gethostname(), member_port))
                        sock.close()        
        

# main process of the peer
class peerMain:

    # peer initializations
    def __init__(self):
        # ip address of the registry
        self.registryName = gethostname()
        try:
            host=gethostbyname(self.registryName)
        except gaierror:
            host = ni.ifaddresses('en0')[ni.AF_INET][0]['addr']
        #self.registryName = 'localhost'
        # port number of the registry
        self.registryPort = 15600
        # tcp socket connection to registry
        self.tcpClientSocket = socket(AF_INET, SOCK_STREAM)
        self.tcpClientSocket.connect((self.registryName,self.registryPort))
        # initializes udp socket which is used to send hello messages
        self.udpClientSocket = socket(AF_INET, SOCK_DGRAM)
        # udp port of the registry
        self.registryUDPPort = 15500
        # login info of the peer
        self.loginCredentials = (None, None)
        # online status of the peer
        self.isOnline = False
        # server port number of this peer
        self.peerServerPort = None
        # server of this peer
        self.peerServer = None  
        self.udpServerPort = None
        # client of this peer
        self.peerClient = None
        # timer initialization
        self.timer = None
        
        choice = "0"
        # log file initialization
        logging.basicConfig(filename="peer.log", level=logging.INFO)
        # as long as the user is not logged out, asks to select an option in the menu
        if(input("do you want to create an account? (y/n): ") == "y"):
                username = input("Enter username: ")
                password = self.get_valid_password()
                
                self.createAccount(username, password)
        while True:
            # menu selection prompt
            #choice = input("Choose: \nCreate account: 1\nLogin: 2\nLogout: 3\nSearch: 4\nStart a chat: 5\n")

            choose_outter = input("Choose: \nLogin: 1\nExit: 2\n")
            if(choose_outter=="1" and not self.isOnline):
                    username = input("username: ")
                    password = input("password: ")
                # asks for the port number for server's tcp socket
                    peerServerPort = int(input("Enter a port number for peer server: "))
                    udpServerPort = int(input("Enter a port number for peer udp server: "))
                
                    status = self.login(username, password, peerServerPort,udpServerPort)
                # is user logs in successfully, peer variables are set
                    if status == 1:
                        self.isOnline = True
                        self.loginCredentials = (username, password)
                        self.peerServerPort = peerServerPort
                        self.udpServerPort = udpServerPort
                        # creates the server thread for this peer, and runs it
                        self.peerServer = PeerServer(self.loginCredentials[0], self.peerServerPort,self.udpServerPort)
                        self.peerServer.start()
                        # hello message is sent to registry
                        self.sendHelloMessage()
            elif(choose_outter=="1" and self.isOnline):
                print("You are already logged in")
            else:
                self.logout(2)
                self.isOnline = False
                self.loginCredentials = (None, None)
                self.peerServer.isOnline = False
                self.peerServer.tcpServerSocket.close()
                if self.peerClient is not None:
                    self.peerClient.tcpClientSocket.close()
                # close all running threads
                terminate.set()
                print("Logged out successfully")
                break

            
            choice = input("Choose: \nLogout: 3\nSearch: 4\nStart a chat: 5\nCreate Room: 6\nJoin an Existing Room: 7\nJoin new Room: 8\n")

            # if choice is 1, creates an account with the username
            # and password entered by the user
            # if choice == "1":
            #     username = input("username: ")
            #     password = self.get_valid_password()
                
            #     self.createAccount(username, password)
            # if choice is 2 and user is not logged in, asks for the username
            # and the password to login
            # elif choice == "2" and not self.isOnline:
            #     username = input("username: ")
            #     password = input("password: ")
            #     # asks for the port number for server's tcp socket
            #     peerServerPort = int(input("Enter a port number for peer server: "))
                
            #     status = self.login(username, password, peerServerPort)
            #     # is user logs in successfully, peer variables are set
            #     if status == 1:
            #         self.isOnline = True
            #         self.loginCredentials = (username, password)
            #         self.peerServerPort = peerServerPort
            #         # creates the server thread for this peer, and runs it
            #         self.peerServer = PeerServer(self.loginCredentials[0], self.peerServerPort)
            #         self.peerServer.start()
            #         # hello message is sent to registry
            #         self.sendHelloMessage()
            # if choice is 3 and user is logged in, then user is logged out
            # and peer variables are set, and server and client sockets are closed
            if choice == "3" and self.isOnline:
                self.logout(1)
                self.isOnline = False
                self.loginCredentials = (None, None)
                self.peerServer.isOnline = False
                self.peerServer.tcpServerSocket.close()
                if self.peerClient is not None:
                    self.peerClient.tcpClientSocket.close()
                print("Logged out successfully")
                
            
            # if choice is 4 and user is online, then user is asked
            # for a username that is wanted to be searched
            elif choice == "4" and self.isOnline:
                username = input("Username to be searched: ")
                searchStatus = self.searchUser(username)
                # if user is found its ip address is shown to user
                if searchStatus is not None and searchStatus != 0:
                    print("IP address of " + username + " is " + searchStatus)
            # if choice is 5 and user is online, then user is asked
            # to enter the username of the user that is wanted to be chatted
            elif choice == "5" and self.isOnline:
                username = input("Enter the username of user to start chat: ")
                searchStatus = self.searchUser(username)
                # if searched user is found, then its ip address and port number is retrieved
                # and a client thread is created
                # main process waits for the client thread to finish its chat
                if searchStatus != None and searchStatus != 0:
                    searchStatus = searchStatus.split(":")
                    self.peerClient = PeerClient(searchStatus[0], int(searchStatus[1]) , self.loginCredentials[0], self.peerServer, None)
                    self.peerClient.start()
                    self.peerClient.join()

            elif choice == "6" and self.isOnline:
                room_name = input("Enter the name of the room: ")
                self.createRoom(room_name, self.loginCredentials[0])


            elif choice == "7" and self.isOnline:
                self.get_rooms(self.loginCredentials[0])
                room_name = input("Enter the name of the room: ")
                roomSearchStatus = self.SearchRoom(room_name)
                if roomSearchStatus != None and roomSearchStatus != 0:
                    owner = roomSearchStatus["owner"]
                    members = roomSearchStatus["members"]
                    if self.loginCredentials[0] in members:
                        print("Joining Room....")
                        self.userClientRoom = ClientRoom(room_name, owner , members, self.peerServer, self)
                        self.peerServer.udp_receiver.room_name = room_name
                        self.peerServer.udp_receiver.in_this_room = True
                        self.userClientRoom.start()
                        self.userClientRoom.join()


            elif choice == "8" and self.isOnline:
                room_name = input("Enter the name of the room: ")
                roomSearchStatus = self.SearchRoom(room_name)
                if roomSearchStatus != None and roomSearchStatus != 0:
                    roomSearchStatus = roomSearchStatus.split(":")
                    self.peerclient = PeerClient(roomSearchStatus[0], int(roomSearchStatus[1]) , self.loginCredentials[0], self.peerServer, None)    
                    a = threading.Thread(target=self.peerclient.join_request,args=(room_name,self.loginCredentials[0]))
                    a.start()
                    a.join()
                    
                

            # if this is the receiver side then it will get the prompt to accept an incoming request during the main loop
            # that's why response is evaluated in main process not the server thread even though the prompt is printed by server
            # if the response is ok then a client is created for this peer with the OK message and that's why it will directly
            # sent an OK message to the requesting side peer server and waits for the user input
            # main process waits for the client thread to finish its chat
            elif choice == "OK" and self.isOnline:
                okMessage = "OK " + self.loginCredentials[0]
                logging.info("Send to " + self.peerServer.connectedPeerIP + " -> " + okMessage)
                self.peerServer.connectedPeerSocket.send(okMessage.encode())
                self.peerClient = PeerClient(self.peerServer.connectedPeerIP, self.peerServer.connectedPeerPort , self.loginCredentials[0], self.peerServer, "OK")
                self.peerClient.start()
                self.peerClient.join()

            elif choice == "YES" and self.isOnline:
                self.peerServer.connectedPeerSocket.send("Join-succ".encode())
                self.peerServer.isChatRequested = 0
                logging.info("Send to " + self.peerServer.connectedPeerIP + " -> Join-succ")

            elif choice == "NO" and self.isOnline:
                self.peerServer.connectedPeerSocket.send("Join-fail".encode())
                self.peerServer.isChatRequested = 0
                logging.info("Send to " + self.peerServer.connectedPeerIP + " -> Join-fail")
            # if user rejects the chat request then reject message is sent to the requester side
            elif choice == "REJECT" and self.isOnline:
                self.peerServer.connectedPeerSocket.send("REJECT".encode())
                self.peerServer.isChatRequested = 0
                logging.info("Send to " + self.peerServer.connectedPeerIP + " -> REJECT")
            # if choice is cancel timer for hello message is cancelled
            elif choice == "CANCEL":
                self.timer.cancel()
                break
        # if main process is not ended with cancel selection
        # socket of the client is closed
        if choice != "CANCEL":
            self.tcpClientSocket.close()

    # account creation function
    def createAccount(self, username, password):
        # join message to create an account is composed and sent to registry
        # if response is success then informs the user for account creation
        # if response is exist then informs the user for account existence
        message = "REGISTER " + username + " " + password
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode()
        logging.info("Received from " + self.registryName + " -> " + response)
        if response == server_responses['REGISTER'][110]:
            print("Account created...")
        elif response == server_responses["REGISTER"][151]:
            print("choose another username or login...")
        elif response == server_responses["REGISTER"][150]:
            print("Invalid username or password...")
    
    # function for getting a valid password
    def get_valid_password(self):
        print("Password must be at least 8 characters long and contain at least one non-numeric character.")
        while True:
            password = input("Enter password: ")
            if len(password) >= 8 and search("[^0-9]", password):
                return password
            else:
                print("Invalid password. Please follow the password policy.")

    # login function
    def login(self, username, password, peerServerPort, udpServerPort):
        # a login message is composed and sent to registry
        # an integer is returned according to each response
        message = "LOGIN " + username + " " + password + " " + str(peerServerPort) + " " + str(udpServerPort)
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode()
        logging.info("Received from " + self.registryName + " -> " + response)
        if response == server_responses["LOGIN"][111]:
            print("Logged in successfully...")
            return 1
        elif response == server_responses["LOGIN"][154]:
            print("Account does not exist...")
            return 0
        elif response == server_responses["LOGIN"][112]:
            print("Account is already online...")
            return 2
        elif response == server_responses["LOGIN"][152]:
            print("Wrong password...")
            return 3
    
    # logout function
    def logout(self, option):
        # a logout message is composed and sent to registry
        # timer is stopped
        if option == 1:
            message = "LOGOUT " + self.loginCredentials[0]
            self.timer.cancel()
        else:
            message = "LOGOUT"
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        

    # function for searching an online user
    def searchUser(self, username):
        # a search message is composed and sent to registry
        # custom value is returned according to each response
        # to this search message
        message = "SEARCH " + username
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode().split()
        logging.info("Received from " + self.registryName + " -> " + " ".join(response))
        if response[0] == "search-success":
            print(username + " is found successfully...")
            return response[1]
        elif response[0] == "search-user-not-online":
            print(username + " is not online...")
            return 0
        elif response[0] == "search-user-not-found":
            print(username + " is not found")
            return None
    

    def createRoom(self, room_name, owner):
        message = "CRTROOM " + room_name + " " + owner
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024).decode().split()
        logging.info("Received from " + self.registryName + " -> " + " ".join(response))
        if response[0] == "crtroom-success":
            print("Room created successfully...")
        else:
            print("Room creation failed...")

    def get_rooms(self, username):
        message = "GETROOMS " + username
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = pickle.loads(self.tcpClientSocket.recv(1024))
        logging.info("Received from " + self.registryName + " -> " + str(response))
        if response[0] == "getrooms-success":
            print("Rooms retrieved successfully...")
            response[0] = ["Room Name", "Owner"]
            print(tabulate(response, headers="firstrow", tablefmt="psql"))
        else:
            print("Room retrieval failed...")
    

    def SearchRoom(self, room_name):
        message = "SEARCHROOM " + room_name
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024)
        response = pickle.loads(response)
        logging.info("Received from " + self.registryName + " -> " + " ".join(response["heading"]))
        if response["heading"] == "searchroom-success":
            print("Room found successfully...")
            print("Requesting to join the room...")
            return response
        elif response["heading"] == "Owner-offline":
            print("Room owner is offline...")
            return 0
        else:
            print("Room not found...")
            return None
    
    def get_UDP_ports(self,room_name):
        message = "GETPORTS " + room_name
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message)
        self.tcpClientSocket.send(message.encode())
        response = self.tcpClientSocket.recv(1024)
        response = pickle.loads(response)
        logging.info("Received from " + self.registryName + " -> " + " ".join(response["heading"]))
        if response["heading"] == "getports-success":
            return response["ports"]
        else:
            print("Ports retrieval failed...")
            return None

    # function for sending hello message
    # a timer thread is used to send hello messages to udp socket of registry
    def sendHelloMessage(self):
        message = "HELLO " + self.loginCredentials[0]
        logging.info("Send to " + self.registryName + ":" + str(self.registryUDPPort) + " -> " + message)
        self.udpClientSocket.sendto(message.encode(), (self.registryName, self.registryUDPPort))
        self.timer = threading.Timer(1, self.sendHelloMessage)
        self.timer.start()

# peer is started
main = peerMain()