import requests
from config import engine, sql_session
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Mfr(Base):
    __tablename__ = 'mfr_db'
    id = Column(Integer, primary_key=True)
    country = Column(String(100), nullable=False)
    commonname = Column(String(100))
    name = Column(String(100))
    vehicle_type = Column(String(100)) # if vehicle type is present in JSON - load value

# Load data from JSON
    @staticmethod
    def getMFCdata(page):
        URL_MFRBASE = 'https://vpiclist.cdan.dot.gov/vpiclistapi/vehicles/'\
        'getallmanufacturers?format=json&page=%s'
        r = requests.get(URL_MFRBASE % page)
        return r.json()['Results']

# Parse JSON and populate mfr_db table of the database with JSON data
    @staticmethod
    def fill_mfr_db(page):
        if engine.has_table('mfr_db'):
            Mfr.__table__.drop(engine)
        data = Mfr.getMFCdata(page)
        Base.metadata.create_all(engine)
# this list keeps the number of id's processed
        ids = []
        for mfr_row in data:
# Check for unique ID - some id's from API are doubled and not unique!
            if mfr_row['Mfr_ID'] not in ids:
                type_vehicle = False
                ids.append(mfr_row['Mfr_ID'])
# Here is the algo for setting VehicleType field. The logic is that we loop through all VehicleTypes
# and look for IsPrimary = True field.
                if len(mfr_row['VehicleTypes']) != 0:
                    for vehicle_type in mfr_row['VehicleTypes']:
                        if vehicle_type['IsPrimary'] == True:
                            type_vehicle = vehicle_type['Name']
# Sometimes even if vehicle type is set, no primary key is defined.
# So we check that after iterating we have vehilce
# type set. If not = > manually set to no primary key.
# The same value is assigned when no VehicleType info is present
                if not type_vehicle:
                    type_vehicle = 'No primary type'
                    mfr_line = Mfr(id=mfr_row['Mfr_ID'], country=mfr_row['Country'],
                                   commonname=mfr_row['Mfr_CommonName'], name=mfr_row['Mfr_Name'],
                                   vehicle_type=type_vehicle)
                sql_session.add(mfr_line)
        sql_session.commit()

# class used to store Models based on loaded manufactures
class Model(Base):
    __tablename__ = 'model_db'

    id = Column(Integer, primary_key = True)
    name = Column(String)
    pic_url = Column(String)
    dealership = Column(String)
    price = Column(Integer)
    user_id = Column(Integer)
    mfr_id = Column(Integer, ForeignKey('mfr_db.id'))
    mfr = relationship(Mfr)

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
# Pic link is formed using flickr.com search engine and tags and not always produces
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
    def fill_models_db(year=2016, ids=None):
# Check if IDS is a list, otherwise exit
        if not isinstance(ids, list):
            print 'Ids is not list'
            return None
        Model.metadata.bind = engine
# Delete the model_db table and create a new one
# Delete the following two lines if no table recreation needed.
        Model.__table__.drop(checkfirst =True)
        Model.__table__.create(checkfirst =True)
# If list of ID's is empty then populate models for all makes
# Else use ids list to find models to populate model_db table
        if len(ids) == 0:
            mfr = sql_session.query(Mfr).all()
        else:
            mfr = sql_session.query(Mfr).filter(Mfr.id.in_(ids)).all()
        for entry in mfr:
# Try to get info from VPIC website API. If not successful, then skip the model
            try:
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
                            dealership = 'placeholder', price = 0, user_id = 0
                            )
                        sql_session.add(model_line)
                        print ('Added model with Id(no commitment made yet): ' + str(model_id) + '.' +
                             entry.commonname + ' ' + model_name)
            except:
                print ('Error raised. MFR ID:' + str(entry.id) + '.' + 'MFR Name:' + entry.name)
        sql_session.commit()
        print ('All commits added successfully')
