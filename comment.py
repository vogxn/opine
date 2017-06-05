from datetime import datetime
from marshmallow import Schema, fields, post_load


class Admin(object):
    def __init__(self, login, repo):
        self.login = login
        self.repo = repo


class User(object):
    def __init__(self, login, html_url=None, avatar_url=None):
        self.login = login
        self.html_url = html_url
        self.avatar_url = avatar_url


class Comment(object):
    def __init__(self, body, user=None, html_url=None,
                 created_at=datetime.now(), updated_at=datetime.now()):
        self.body = body
        self.user = user
        self.html_url = html_url
        self.created_at = created_at
        self.updated_at = updated_at


class AdminSchema(Schema):
    login = fields.Str(required=True)
    repo = fields.Str(required=True)

    @post_load
    def make_admin(self, data):
        return Admin(**data)


class UserSchema(Schema):
    login = fields.Str(required=True)
    html_url = fields.URL()
    avatar_url = fields.URL()

    @post_load
    def make_user(self, data):
        return User(**data)


class CommentSchema(Schema):
    body = fields.Str(required=True)
    html_url = fields.URL()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
    user = fields.Nested(UserSchema)

    @post_load
    def make_comment(self, data):
        return Comment(**data)
