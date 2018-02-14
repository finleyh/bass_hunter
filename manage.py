# this is Alembic, a part of flask-migrate. this file manage.py will manage database migrations to update a database's schema
import os
from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand

#import app and db from app.py
from app import app, db

app.config.from_object(os.environ['APP_SETTINGS'])

migrade = Migrate(app,db)
manager = Manager(app)

manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
	manager.run()
