# execute this file with command
# python -m utils.psql.create_tables

from . import Base, engine

Base.metadata.create_all(bind=engine)