import pandas as pd
from datetime import datetime
import time
import requests

def fetch_historical_weather(wtimestamp,lat=49.819294, lng=6.274638):
    """Fetch historical weather data from Open-Meteo API"""
    #date = datetime.strptime(wtimestamp, '%d.%m.%Y %H:%M:%S')
    date = wtimestamp.strftime("%Y-%m-%d"                           )
    date_hour = wtimestamp.strftime("%H")
    url = f"https://archive-api.open-meteo.com/v1/archive"
    
    params = {
        "latitude": lat,
        "longitude": lng,
        "start_date": date,
        "end_date": date,
        "hourly": ["temperature_2m", "weathercode", "dewpoint_2m", "rain", "snowfall", "cloud_cover"],
        "timezone": "Europe/Berlin"
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()        
        # Find the closest hour in the returned data
        hour_index = int(date_hour)
        
        temp = data['hourly']['temperature_2m'][hour_index]
        weather_code = data['hourly']['weathercode'][hour_index]
        dewpoint = data['hourly']['dewpoint_2m'][hour_index]
        rain = data['hourly']['rain'][hour_index]
        snowfall = data['hourly']['snowfall'][hour_index]
        cloud_cover = data['hourly']['cloud_cover'][hour_index]

        return temp, weather_code, dewpoint, rain, snowfall, cloud_cover
    else:
        print(" return code ", response.status_code, " for call ",url, " ",params)
        return None, None, None, None, None, None

def weather_code_to_condition(code):
    """Convert WMO weather codes to text descriptions"""
    weather_codes = {
        0: "clear",
        1: "mainly clear",
        2: "partly cloudy",
        3: "overcast",
        45: "foggy",
        48: "depositing rime fog",
        51: "light drizzle",
        53: "moderate drizzle",
        55: "dense drizzle",
        61: "slight rain",
        63: "moderate rain",
        65: "heavy rain",
        71: "slight snow",
        73: "moderate snow",
        75: "heavy snow",
        77: "snow grains",
        80: "slight rain showers",
        81: "moderate rain showers",
        82: "violent rain showers",
        95: "thunderstorm"
    }

    return weather_codes.get(code, "unknown")
   
def process_data(df,datetime_column):
    """Process the input spreadsheet and add weather data"""
    # Read the input file
    # add day of week ( to test between weekdays on weekends) and day of year column
    df[datetime_column] = pd.to_datetime(df[datetime_column])
    df['day_of_week'] = df[datetime_column].dt.dayofweek
    df['day_of_year'] = df[datetime_column].dt.dayofyear
    # Initialize new columns
    weather_data = []

    
    # Process each row
    for index, row in df.iterrows():
        current_datetime = row[datetime_column].iloc[0] if isinstance(row[datetime_column], pd.Series) else row[datetime_column]
        date_str = current_datetime.strftime('%Y-%m-%d')
        time_str = current_datetime.strftime('%H:%M')
        
        # Add delay to avoid API rate limiting
        if index > 0:
            time.sleep(1)
               
        temp, weather_code, dewpoint, rain, snowfall, cloud_cover  = fetch_historical_weather(
            current_datetime,
            49.81933020502184, 
            6.274531751725807, 
            
        )
        if temp is not None:
            weather_data.append({
                    'startedAt': current_datetime,
                    'temperature': temp,
                    'weather_condition': weather_code_to_condition(weather_code),
                    'dew_point': dewpoint,
                    'rain': rain,
                    'snowfall': snowfall,
                    'cloud_cover': cloud_cover
                })


            #print(f"getting info for row {row['day']} {row['time']} - temp = {temp} - weather = {weather_code} - dew_point = {dewpoint} - rain = {rain}, snowfall = {snowfall}, cloud_cover = {cloud_cover}")
    # Select and reorder columns
    result_df =  pd.DataFrame(weather_data)
    weather_df = pd.DataFrame(result_df)
    return weather_df
