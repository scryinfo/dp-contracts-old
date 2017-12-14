from peewee import *

db = SqliteDatabase('scry.db')


class Listing(Model):
    cid = CharField()
    size = CharField()
    owner = CharField()
    name = CharField()
    price = DecimalField(constraints=[Check('price > 0')])

    class Meta:
        database = db
        indexes = (
            # create a unique constraint
            (('cid', 'owner'), True),
        )


class Trader(Model):
    name = CharField()
    account = CharField()
    role = CharField()

    class Meta:
        database = db
        indexes = (
            # create a unique constraint
            (('name', 'role'), True),
        )


def create_tables():
    db.connect()
    db.create_tables([Listing, Trader], True)


create_tables()
