from marshmallow import Schema, fields, post_load


class Comment(object):
    def __init__(self, owner, repo, body):
        self.owner = owner
        self.repo = repo
        self.body = body


class CommentSchema(Schema):
    owner = fields.Str()
    repo = fields.Str()
    body = fields.Str()

    @post_load
    def make_comment(self, data):
        return Comment(**data)
