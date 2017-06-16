from peewee import Model, PostgresqlDatabase
from playhouse.db_url import connect, parse
from peewee import CharField, IntegerField, \
     DateTimeField, BooleanField, BigIntegerField, ForeignKeyField

from settings import DATABASE_URL

DEBUG = True
DB_ARGS = parse(DATABASE_URL)
DB = PostgresqlDatabase(**DB_ARGS)


class BaseModel(Model):
    """ BaseModel for all Schema definitions in Opine """
    class Meta:
        database = DB


class Installation(BaseModel):
    """ Represents a github app installation """
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
    """ Simple counters for app and number of comments against app """
    installation = ForeignKeyField(Installation)
    comments = BigIntegerField()
    updated = DateTimeField()


if __name__ == '__main__':
    DB.create_tables([Installation, Stats], safe=True)
