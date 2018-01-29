import datetime
from peewee import *

db = SqliteDatabase('scry.db')


class Trader(Model):
    name = CharField(unique=True)
    account = CharField()
    password = CharField()
    created_at = TimestampField(utc=true)

    class Meta:
        database = db
        indexes = (
            # create a unique constraint
            (('name', 'account'), True),
        )


class Listing(Model):
    cid = CharField()
    size = CharField()
    owner = ForeignKeyField(Trader, related_name='listings')
    name = CharField()
    price = DecimalField(constraints=[Check('price > 0')])
    created_at = TimestampField(utc=true)

    class Meta:
        database = db
        indexes = (
            # create a unique constraint
            (('cid', 'owner'), True),
        )


class PurchaseOrder(Model):
    buyer = ForeignKeyField(Trader, related_name='purchases')
    listing = ForeignKeyField(Listing, related_name='sales')
    verifier = ForeignKeyField(Trader, related_name='verifications', null=True)
    create_block = IntegerField()
    needs_verification = BooleanField()
    needs_closure = BooleanField()
    buyer_auth = CharField()
    verifier_auth = CharField(null=True)
    created_at = TimestampField(utc=True)

    class Meta:
        database = db


def create_tables():
    db.connect()
    db.create_tables([Listing, Trader, PurchaseOrder], True)
    db.close()


create_tables()
