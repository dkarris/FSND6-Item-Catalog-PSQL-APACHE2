import requests
from config import engine, sql_session
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(100), nullable=False)
    picture = Column(String(250))
    oauthid = Column(String(250),nullable=False)


class Mfr(Base):
    __tablename__ = 'mfr_db'

    id = Column(Integer, primary_key=True)
    country = Column(String(100), nullable=False)
    commonname = Column(String(100))
    name = Column(String(100))
    vehicle_type = Column(String(100)) # if vehicle type is present in JSON - load value
    model = relationship("Model", cascade='delete, delete-orphan', single_parent=True,
        backref="mfr")
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    user = relationship(User, backref="mfr")

# Load data from JSON
    @staticmethod
    def getMFCdata(page):
        URL_MFRBASE = 'https://vpiclist.cdan.dot.gov/vpiclistapi/vehicles/'\
        'getallmanufacturers?format=json&page=%s'
        # print URL_MFRBASE % page
        r = requests.get(URL_MFRBASE % page)
        return r.json()['Results']

# Parse JSON and populate mfr_db table of the database with JSON data
    @staticmethod
    def fill_mfr_db(page, deleteTable, login_session):
        if login_session.get('username') == None:
            return (0,0,'You must be signed in to add models <BR>' +
                '<a href="/login">Click here</a> to login')
        if deleteTable == "yes":
# The following drop table does not work with cascade delete from model table, at least as of now. Thus
# simply delete all records in MFR for cascade delete the model table
            # Mfr.__table__.drop(engine)
            # Base.metadata.create_all(engine)
            records = sql_session.query(Mfr).all()
            for record in records:
                creator_id = record.user_id
# Check if the record belongs to authorized user
                if creator_id == login_session['username']:
                    sql_session.delete(record)
                else:
# If not then skip record. Later some nice stuff might be added to get back the list of 
# models not deleted and returned in a separate modal window
                    pass
            sql_session.commit()
        data = Mfr.getMFCdata(int(page))
# this list keeps the number of id's processed
        ids = []
# count for records appended and total records retrieved 
        new_records = 0
        total_records = len(data)
        for mfr_row in data:
# Check if Mfr_ID exists in DB = if yes => skip the record
            if sql_session.query(Mfr).filter(Mfr.id == mfr_row['Mfr_ID']).count() == 0:
# Check for unique ID -some id's from API are doubled and not unique!So we put processed IDS into list ids
                if mfr_row['Mfr_ID'] not in ids:
                    type_vehicle = False
                    ids.append(mfr_row['Mfr_ID'])
# Here is the algo for setting VehicleType field. The logic is that we loop through all VehicleTypes
# and look for IsPrimary = True field.
                    if len(mfr_row['VehicleTypes']) != 0:
                        for vehicle_type in mfr_row['VehicleTypes']:
                            if vehicle_type['IsPrimary'] == True:
                                type_vehicle = vehicle_type['Name']
# Sometimes even if vehicle type is set, no primary key is defined - NHTSA data consistency bug
# So we check that after iterating we have vehilce
# type set. If not = > manually set to 'no primary key'.
# The same value is assigned when no VehicleType info is present
                    if not type_vehicle:
                        type_vehicle = 'No primary type'
# Get current user, and update records with that user
                    mfr_line = Mfr(id=mfr_row['Mfr_ID'],country=mfr_row['Country'],
                                       commonname=mfr_row['Mfr_CommonName'],
                                       name=mfr_row['Mfr_Name'],vehicle_type=type_vehicle,
                                       user_id=login_session['user_id'])
                    sql_session.add(mfr_line)
                    new_records += 1
            sql_session.commit()
        error_txt = None
        return  new_records, total_records, error_txt

# class used to store Models based on loaded manufactures
class Model(Base):
    __tablename__ = 'model_db'

    id = Column(Integer, primary_key = True)
    name = Column(String)
    pic_url = Column(String)
    dealership = Column(String)
    price = Column(Integer)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    user = relationship(User, backref="model")
    mfr_id = Column(Integer, ForeignKey('mfr_db.id'))

# Populate models_db with manufactures from mfr_db
# by using VPIC API
# year should be greater than 1996 and mfr should be string
# function returns Json object if success or None if
# wrong arguments passed

    @staticmethod
    def getModeldata(year, mfr):
        if not isinstance(mfr, basestring):
            return None
        if year < 1996:
            return None
        URL_MODELS = 'https://vpiclist.cdan.dot.gov/vpiclistapi/'\
        'vehicles/getmodelsformakeyear/make/%s/modelyear/%s?format=json' % (mfr, year)
        r = requests.get(URL_MODELS)
        return r.json()['Results']

# Retrieve pic link from flickr.com using API and JSON requests.
# Pic link is formed using flickr.com search engine and tags do not always produce
# accurate search results
# But as of now it will suffice
# Returns url string to store in DB table

    
    @staticmethod
    def getModelPicLink(make, model, year='2016'):
        flickr_key = '576a54d7e34bf4d12ed64c37aaa5579e'
        flickr_endpoint = 'https://api.flickr.com/'\
            'services/rest/?method=flickr.photos.search&api_key=%s'\
            '&text=%s&format=json&nojsoncallback=1'

        flickr_url = flickr_endpoint % (flickr_key, make + ' ' + model + ' ' + year)
        r = requests.get(flickr_url).json()['photos']['photo']
        if len(r) != 0:
            link = r[0]
            url_link = 'https://farm'+str(link['farm'])+'.staticflickr.com/'+str(link['server'])+'/'\
                   + str(link['id'])+'_'+str(link['secret'])+'.jpg'
        else:
            url_link = '# - no link found on flickr'
        return url_link

# Fill in models_db
# If present ids = fill only data with manufactures ids in ids

    @staticmethod
    def fill_models_db(login_session,year=2016, ids=None):
# Check if IDS is a list, otherwise exit
        if not isinstance(ids, list):
            print 'Ids is not list'
            return None
        Model.metadata.bind = engine
# Delete the model_db table and create a new one
# Delete the following two lines if no table recreation needed.
        Model.__table__.drop(checkfirst =True)
        Model.__table__.create(checkfirst =True)
# If list of ID's is empty:  either populate models for all makes or do nothing. 
# The first choice is commented out, for the sake of speed.
# Else use ids list to find models to populate model_db table
        if len(ids) == 0:
#            mfr = sql_session.query(Mfr).all() - This will go to populate all makes 
             return ("No models selected - Nothing to add")
        else:
            mfr = sql_session.query(Mfr).filter(Mfr.id.in_(ids)).all()
        count = 0
        for entry in mfr:
# Try to get info from NHTSA website API. If not successful, then skip the model
            try:
# due to bugs in NHTSA database some records don't have short name in this case
# try to substitute full name. NHTSA model unique ids is all messy, so need to use
# just mfr name when querying their api
# so try to plug the first part of the long name and hope that it will work.
                if not entry.commonname:
                    entry.commonname = entry.name.split(' ')[0]   
                model_data = Model.getModeldata(year, entry.commonname.lower())
                for row in model_data:
                    model_id = row['Model_ID']
#Check if this model_id is present in db, if Yes => skip the record
                    if sql_session.query(Model).filter_by(id = model_id).count() == 0:
                        url_link = ''
                        model_name = row['Model_Name']
# Get URL to pic from flickr.com
                        url_link = Model.getModelPicLink(entry.commonname.lower(), model_name)
                        model_line = Model(id = model_id, name = model_name,
                            mfr_id = entry.id, pic_url = url_link,
                            dealership = 'placeholder', price = 0, user_id = login_session['user_id']
                            )
                        sql_session.add(model_line)
                        print ('Added model with Id(no commitment made yet): ' + str(model_id) + '.' +
                             entry.commonname + ' ' + model_name)
                        count += 1
            except:
                return ('Error raised. MFR ID:' + str(entry.id) + '.' + 'MFR Name:' + entry.name)
        sql_session.commit()
        return ('All commits added successfully. %s models added succesfully' % count)

Base.metadata.create_all(engine)
