from playhouse.migrate import *
db = SqliteDatabase('scry.db')

migrator = SqliteMigrator(db)
with db.transaction():
    migrate(
        migrator.drop_column('purchaseorder', 'verifiers')
    )
