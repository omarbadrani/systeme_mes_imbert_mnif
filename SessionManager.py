# services/session_manager.py
class SessionManager:
    _instance = None

    def __init__(self):
        self.access_token = None
        self.refresh_token = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = SessionManager()
        return cls._instance

    def set_tokens(self, access_token, refresh_token):
        self.access_token = access_token
        self.refresh_token = refresh_token

    def get_access_token(self):
        return self.access_token

    def get_refresh_token(self):
        return self.refresh_token
