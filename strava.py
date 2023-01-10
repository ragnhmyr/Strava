'''
https://www.strava.com/oauth/authorize?client_id=[CLIENT_ID]&redirect_uri=http://localhost&response_type=code&scope=activity:read_all

First time run
import requests 


url = "https://www.strava.com/oauth/token?client_id=[CLIENT_ID]&client_secret=[CLIENT_SECRET]&code=[CODE_FROM_PREVIOUS_CALL]&grant_type=authorization_code"
myobj = {"key":"value"}
x = requests 

x = requests.post(url)

print(x.text)


'''
#Elevation not working yet
#Follow steps from https://towardsdatascience.com/using-the-strava-api-and-pandas-to-explore-your-activity-data-d94901d9bfde / https://developers.strava.com/docs/getting-started/#oauth to get started with the Strava API

#Credits: thanks to René from https://towardsdatascience.com/visualize-your-strava-data-on-an-interactive-map-with-python-92c1ce69e91d for the code
#sources: https://towardsdatascience.com/visualize-your-strava-data-on-an-interactive-map-with-python-92c1ce69e91d 
#sources: https://betterprogramming.pub/connecting-and-mapping-strava-data-with-python-and-django-41456b874f3b
#source: https://nddoornekamp.medium.com/plotting-strava-data-with-python-7aaf0cf0a9c3



import os
import requests
import urllib3
import polyline
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import time
import matplotlib.pyplot as plt
import folium
import polyline
import base64
from tqdm import tqdm
import config #config file with client_id, client_secret, refresh_token

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

auth_url = "https://www.strava.com/oauth/token"
activites_url = "https://www.strava.com/api/v3/athlete/activities"

payload = {
    'client_id': config.client_id, #my client id
    'client_secret': config.client_secret, #my cient secret
    'refresh_token': config.refresh_token, #my refresh token 
    'grant_type': "refresh_token",
    'f': 'json'
}

print("Requesting Token...\n")
res = requests.post(auth_url, data=payload, verify=False)
access_token = res.json()['access_token']
print("Access Token = {}\n".format(access_token))

def get_data(access_token, per_page=200, page=1):
 
   activities_url = 'https://www.strava.com/api/v3/athlete/activities'
   headers = {'Authorization': 'Bearer ' + access_token}
   params = {'per_page': per_page, 'page': page}
   
   data = requests.get(
       activities_url, 
       headers=headers, 
       params=params
   ).json()
 
   return data
# get you strava data
max_number_of_pages = 10
data = list()
for page_number in tqdm(range(1, max_number_of_pages + 1)):
    page_data = get_data(access_token, page=page_number)
    if page_data == []:
        break
    data.append(page_data)

# data dictionaries
data_dictionaries = []
for page in data:
    data_dictionaries.extend(page)
# print number of activities
print('Number of activities downloaded: {}'.format(len(data_dictionaries)))

# normalize data
activities = pd.json_normalize(data_dictionaries)
# sample activities
#activities[['name', 'distance', 'average_speed', 'moving_time']]\.sample(5)

print(activities)
# add decoded summary polylines
activities['map.polyline'] = activities['map.summary_polyline'].apply(polyline.decode)
print(activities)
# define function to get elevation data using the open-elevation API

'''
def get_elevation(latitude, longitude):
    base_url = 'https://api.open-elevation.com/api/v1/lookup'
    payload = {'locations': f'{latitude},{longitude}'}
    r = requests.get(base_url, params=payload).json()['results'][0]
    return r['elevation']
# get elevation data
elevation_data = list()
for idx in tqdm(activities.index):
    activity = activities.loc[idx, :]
    elevation = [get_elevation(coord[0], coord[1]) for coord in activity['map.polyline']]
    elevation_data.append(elevation)
# add elevation data to dataframe
activities['map.elevation'] = elevation_data
print(activities)
'''

# convert data types
activities.loc[:, 'start_date'] = pd.to_datetime(activities['start_date']).dt.tz_localize(None)
activities.loc[:, 'start_date_local'] = pd.to_datetime(activities['start_date_local']).dt.tz_localize(None)
# convert values
activities.loc[:, 'distance'] /= 1000 # convert from m to km
activities.loc[:, 'average_speed'] *= 3.6 # convert from m/s to km/h
activities.loc[:, 'max_speed'] *= 3.6 # convert from m/s to km/h
# set index
activities.set_index('start_date_local', inplace=True)
# drop columns
activities.drop(
    [
        'map.summary_polyline', 
        'resource_state',
        'external_id', 
        'upload_id', 
        'location_city', 
        'location_state', 
        'has_kudoed', 
        'start_date', 
        'athlete.resource_state', 
        'utc_offset', 
        'map.resource_state', 
        'athlete.id', 
        'visibility', 
        'heartrate_opt_out', 
        'upload_id_str', 
        'from_accepted_tag', 
        'map.id', 
        'manual', 
        'private', 
        'flagged', 
    ], 
    axis=1, 
    inplace=True
)
print(activities)

# color scheme
# color argument of Icon should be one of: {'green', 'lightgreen', 'red', 'black', 'cadetblue', 'lightred', 'lightblue', 'white', 'darkpurple', 'blue', 'darkred', 'darkblue', 'darkgreen', 'beige', 'pink', 'orange', 'gray', 'lightgray', 'purple'}.
color = {'Ride':'red', 'EBikeRide':'red', 'NordicSki':'blue', 'Run': 'green', 'Walk':'lightgreen', 'Hike':'lightgreen', 'Swim':'cadetblue', 'Workout':'orange', 'Kayaking':'cadetblue', 'Rowing':'cadetblue'}
# create dictionary with elevation profiles

'''
elevation_profile = dict()
for row in activities.iterrows():
    row_values = row[1]
 
    # figure
    fig, ax = plt.subplots(figsize=(6, 2))
    ax = pd.Series(row_values['map.elevation']).rolling(3).mean().plot(
        ax=ax, 
        color=color[row_values['type']],
        legend=False, 
    )
    ax.set_ylabel('Elevation')
    ax.axes.xaxis.set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    png = 'elevation_profile_{}.png'.format(row_values['id'])
    fig.savefig(png, dpi=75)
    plt.close()
 
    # read png file
    elevation_profile[row_values['id']] = base64.b64encode(open(png, 'rb').read()).decode()
 
    # delete file
    os.remove(png)
'''
    # plot all activities on map
resolution, width, height = 75, 6, 6.5
def centroid(polylines):
    x, y = [], []
    for polyline in polylines:
        for coord in polyline:
            x.append(coord[0])
            y.append(coord[1])
    return [(min(x)+max(x))/2, (min(y)+max(y))/2]
m = folium.Map(location=centroid(activities['map.polyline']), zoom_start=4)
for row in activities.iterrows():
    row_index = row[0]
    row_values = row[1]
    if row_values['map.polyline']:
        #print(row_values['map.polyline'])
        folium.PolyLine(row_values['map.polyline'], color=color[row_values['type']]).add_to(m)
        halfway_coord = row_values['map.polyline'][int(len(row_values['map.polyline'])/2)]
# popup text
    html = """
    <h3>{}</h3>
        <p>
            <code>
            Date : {} <br>
            Time : {}
            </code>
        </p>
    <h4>{}</h4>
        <p> 
            <code>
                Distance&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp: {} km <br>
                Elevation Gain&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp: {} m <br>
                Moving Time&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp: {} <br>
                Average Speed&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp: {} km/h (maximum: {} km/h) <br>
                Average Cadence&nbsp;&nbsp;&nbsp;&nbsp;&nbsp: {} rpm <br>
                Average Heart Rate&nbsp;&nbsp: {} bpm (maximum: {} bpm) <br>
                Average Temperature&nbsp: {} <br>
                Relative Effort&nbsp;&nbsp;&nbsp;&nbsp;&nbsp: {} <br>
                Athletes&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp: {} <br>
                Kudos&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp: {} <br>
            </code>
        </p>
    <img src="data:image/png;base64,{}">
    """.format(
        row_values['name'], 
        row_index.date(), 
        row_index.time(),   
        row_values['distance'], 
        row_values['total_elevation_gain'], 
        time.strftime('%H:%M:%S', time.gmtime(row_values['moving_time'])), 
        row_values['average_speed'], row_values['max_speed'], 
        row_values['average_cadence'],  
        row_values['average_heartrate'], row_values['max_heartrate'], 
        #row_values['average_watts'], 
        row_values['average_temp'], 
        #row_values['kilojoules'], 
        row_values['suffer_score'], 
        row_values['athlete_count'], 
        row_values['kudos_count'], 
        "test",
        "test",
        #elevation_profile[row_values['id']], 
    )
    
    # add marker to map
    iframe = folium.IFrame(html, width=(width*resolution)+20, height=(height*resolution)+20)
    popup = folium.Popup(iframe, max_width=2650)
    icon = folium.Icon(color=color[row_values['type']], icon='info-sign')
    marker = folium.Marker(location=halfway_coord, popup=popup, icon=icon)
    marker.add_to(m)
m.save('mymap.html')
#display(m)