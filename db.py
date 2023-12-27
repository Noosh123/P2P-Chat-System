from pymongo import MongoClient

# Includes database operations
class DB:

    # db initializations
    def __init__(self):
        self.client = MongoClient('mongodb://localhost:27017')
        self.db = self.client['p2p-chat']

    # checks if an account with the username exists
    def is_account_exist(self, username):
        cursor = self.db.accounts.find({'username': username})
        doc_count = 0

        for document in cursor:
            doc_count += 1

        if doc_count > 0:
            return True
        else:
            return False


    # registers a user
    def register(self, username, password):
        account = {
            "username": username,
            "password": password,
        }
        self.db.accounts.insert_one(account)


    # retrieves the password for a given username
    def get_password(self, username):
        return self.db.accounts.find_one({"username": username})["password"]

    # def get_salt(self,username):
    #     return self.db.accounts.find_one({"username": username})["salt"]

    # checks if an account with the username online
    def is_account_online(self, username):
        if self.db.online_peers.count_documents({'username': username}) > 0:
            return True
        else:
            return False

    # logs in the user
    def user_login(self, username, ip, port):
        online_peer = {
            "username": username,
            "ip": ip,
            "port": port
        }
        #self.db.online_peers.insert(online_peer)
        self.db.online_peers.insert_one(online_peer)

    # logs out the user
    def user_logout(self, username):
        #self.db.online_peers.remove({"username": username})
        self.db.online_peers.delete_one({"username": username})

    # retrieves the ip address and the port number of the username
    def get_peer_ip_port(self, username):
        res = self.db.online_peers.find_one({"username": username})
        return (res["ip"], res["port"])
    

    

    def create_ChatRoom(self, name, owner):
        # Create a new chat room
        room_data = {
            "name": name,
            "owner": owner,
            "members": [owner]  # Owner is the first member
        }
        self.db.Chat_Rooms.insert_one(room_data)

    def join_Room(self, room_name, username):
        # Add a user to an existing room
        self.db.Chat_Rooms.update_one(
                {"name": room_name},
                {"$addToSet": {"members": username}}
            )
        


    def is_Room_exist(self, room_name):
        # Check if a room exists
        room = self.db.Chat_Rooms.find({"name": room_name})
        doc_count = 0
        for document in room:
            doc_count += 1
        if doc_count > 0:
            return True
        else:
            return False
        
    
    def get_online_members(self, room_name):
        # Get online members in a specific chat room
        online_members = []
        room = self.db.Chat_Rooms.find_one({"name": room_name})
        if room:
            for member in room['members']:
                if self.is_account_online(member):
                    online_members.append(member)
        return online_members
    
    def get_rooms_for_user(self, username):
        rooms = self.db.Chat_Rooms.find({"members": username})
        room_data = [[room["name"], room["owner"]] for room in rooms]
        return room_data


    # write a function that returns the owner of a room
    def get_room_owner(self, room_name):
        room = self.db.Chat_Rooms.find_one({"name": room_name})
        return room["owner"]
    
    # write a function that adds a member to a room
    def add_member_to_room(self, room_name, username):
        self.db.Chat_Rooms.update_one(
                {"name": room_name},
                {"$addToSet": {"members": username}}
            )   