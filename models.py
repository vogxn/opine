from peewee import Model, SqliteDatabase
from peewee import CharField, IntegerField, \
     DateTimeField, BooleanField, BigIntegerField, ForeignKeyField


DATABASE = 'opine.db'
DEBUG = True
database = SqliteDatabase(DATABASE)


class BaseModel(Model):
    class Meta:
        database = database


class Installation(BaseModel):
    ghid = IntegerField(unique=True, null=False)
    repo = CharField()
    owner = CharField()
    active = BooleanField()
    created = DateTimeField()
    updated = DateTimeField()

    class Meta:
        order_by = ('id', )
        indexes = (('repo', 'owner'), False)


class Stats(BaseModel):
    installation = ForeignKeyField(Installation)
    comments = BigIntegerField()
    updated = DateTimeField()


class Session(BaseModel):
    sid = BigIntegerField(unique=True, null=False)
    active = BooleanField()
    expiry = DateTimeField()
