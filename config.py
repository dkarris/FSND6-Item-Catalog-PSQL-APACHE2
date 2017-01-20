from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///cars.db')
DBSession = sessionmaker(bind=engine)
sql_session = DBSession()
