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
    origin = CharField()
    active = BooleanField()
    created = DateTimeField()
    updated = DateTimeField()

    class Meta:
        order_by = ('id', )
        indexes = (
            (('repo', 'owner', 'origin', 'active'), False),
        )


class Stats(BaseModel):
    installation = ForeignKeyField(Installation)
    comments = BigIntegerField()
    updated = DateTimeField()


if __name__ == '__main__':
    database.connect()
    database.create_tables([Installation, Stats])
