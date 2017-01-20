import requests

flickr_key = '576a54d7e34bf4d12ed64c37aaa5579e'

make = 'honda'
model = 'accord'
year = '2016'

flickr_endpoint = 'https://api.flickr.com/'\
                  'services/rest/?method=flickr.photos.search&api_key=%s'\
                  '&text=%s&format=json&nojsoncallback=1'
def getModelPicLink(make, model, year):
    flickr =  flickr_endpoint % (flickr_key, make+'%20'+model+'%20'+year)
    print flickr
    r = requests.get(flickr).json()['photos']['photo']
    for link in r:
        url = 'https://farm'+str(link['farm'])+'.staticflickr.com/'+str(link['server'])+'/' + str(link['id'])+'_'+str(link['secret'])+'.jpg'+'   ' + link['title']
        print url
#    return r

# print flickr_endpoint % (flickr_key, make+'%20'+model+'%20'+year)
getModelPicLink(make,model,year)



    
    
