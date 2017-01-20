import requests
google_url = 'https://www.google.com/search?q=honda%20accord'

def get_all_links(page):
    links = []
    while True:
        url,endpos = get_next_target(page)
        if url:
            print url
            page = page[endpos:]
        else:
            break
    return links
def get_next_target(page):
    start_link = page.find('<im')
    if start_link == -1: 
        return None, 0
    start_quote = page.find('"', start_link)
    end_quote = page.find('"', start_quote + 1)
    url = page[start_quote + 1:end_quote]
    return url, end_quote

r = requests.get(google_url).text
# print r
print get_all_links(r)



