from peewee import *

db = SqliteDatabase('scry.db')


class Listing(Model):
    cid = CharField()
    size = CharField()
    seller = CharField()
    name = CharField()

    class Meta:
        database = db


def create_tables():
    db.connect()
    db.create_tables([Listing], True)
