import unittest
import db

db =db.DB()

class UnitTest(unittest.TestCase):
    def test_registration_success(self):
        username = "test-user"
        self.assertFalse(db.is_account_exist(username))
        db.register(username, "t1234567")
        self.assertTrue(db.is_account_exist(username))

    def test_account_online_failure(self):
        username = "test-user"
        self.assertFalse(db.is_account_online(username))
    
    def test_login_success(self):
        username = "test-user"
        self.assertFalse(db.is_account_online(username))
        db.user_login(username, "192.168.1.10", 15501, 15502)
        self.assertTrue(db.is_account_online(username))

    def test_create_room_success(self):
        self.assertFalse(db.is_Room_exist("test-room"))
        db.create_ChatRoom("test-room", "test-user")

    def test_get_room_success(self):
        self.assertTrue(db.is_Room_exist("test-room"))

    def test_get_room_failure(self):
        self.assertFalse(db.is_Room_exist("test-room-wrong"))

    def test_get_room_owner_failure(self):
        self.assertTrue(db.is_Room_exist("test-room"))
        self.assertFalse(db.get_room_owner("test-room") != "test-user")

    def test_get_room_owner_success(self):
        self.assertTrue(db.is_Room_exist("test-room"))
        self.assertTrue(db.get_room_owner("test-room") == "test-user")

    def test_join_room(self):
        self.assertTrue(db.is_Room_exist("test-room"))
        self.assertFalse("test-user-join" in db.get_chatroom_members("test-room"))
        db.add_member_to_room("test-room", "test-user-join")
        self.assertTrue("test-user-join" in db.get_chatroom_members("test-room"))

    def test_logout(self):
        self.assertTrue(db.is_account_online("test-user"))
        db.user_logout("test-user")
        self.assertFalse(db.is_account_online("test-user"))
    
if __name__ == '__main__':
    unittest.main()

