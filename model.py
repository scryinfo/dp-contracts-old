import datetime
from peewee import *
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SqliteDatabase('scry.db')


class Trader(UserMixin, Model):
    name = CharField(unique=True)
    account = CharField()
    created_at = TimestampField(utc=True)
    password_hash = CharField(128)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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
    created_at = TimestampField(utc=True)

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
    rewards = IntegerField(default=1)

    class Meta:
        database = db


def create_tables():
    db.connect()
    db.create_tables([Listing, Trader, PurchaseOrder])
    db.close()


create_tables()
