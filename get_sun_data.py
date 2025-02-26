#this api returns the sunsrise and sunset data
#https://api.sunrisesunset.io/json?lat=49.819294&lng=6.274638&date=2024-07-01&time_format=24

import pandas as pd
import requests
from datetime import datetime
import time

def get_sun_visibility(df, datetime_column, lat=49.819294, lng=6.274638):
    """
    Check sun visibility for each 15-minute timeslot.
    
    Parameters:
    df (pandas.DataFrame): Input DataFrame with 15-minute timeslots
    datetime_column (str): Name of the column containing datetime strings
    lat (float): Latitude
    lng (float): Longitude
    
    Returns:
    pandas.DataFrame: Original DataFrame with added sun visibility column
    """
    # Convert datetime strings to datetime objects if they aren't already
    df[datetime_column] = pd.to_datetime(df[datetime_column])
    
    # Create an empty list to store results
    visibility_data = []
    
    # Process each row
    for idx, row in df.iterrows():
        
        #current_datetime = row[datetime_column]
        #current_datetime = row[datetime_column].to_pydatetime()
        current_datetime = row[datetime_column].iloc[0] if isinstance(row[datetime_column], pd.Series) else row[datetime_column]
        date_str = current_datetime.strftime('%Y-%m-%d')
        time_str = current_datetime.strftime('%H:%M')
        # Construct API URL
        url = f"https://api.sunrisesunset.io/json?lat={lat}&lng={lng}&date={date_str}&time_format=24"
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] == 'OK':
                results = data['results']
                # Convert times to datetime objects for comparison
                date = current_datetime.date()
                current_time = datetime.strptime(time_str, '%H:%M').time()
                sunrise_time = datetime.strptime(results['sunrise'], '%H:%M:%S').time()
                sunset_time = datetime.strptime(results['sunset'], '%H:%M:%S').time()
                
                # Check if current time is between sunrise and sunset
                is_sun_visible = sunrise_time <= current_time <= sunset_time
                
                visibility_data.append({
                    'startedAt': current_datetime,
                    'sun_visible': is_sun_visible,
                    'sunrise': results['sunrise'],
                    'sunset': results['sunset']
                })
                
            else:
                print(f"API error for datetime {current_datetime}: {data['status']}")
                visibility_data.append({
                    'startedAt': current_datetime,
                    'sun_visible': None,
                    'sunrise': None,
                    'sunset': None
                })
            
            # Add a small delay to avoid hitting rate limits
            time.sleep(1)
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data for {current_datetime}: {e}")
            visibility_data.append({
                'startedAt': current_datetime,
                'sun_visible': None,
                'sunrise': None,
                'sunset': None
            })
    
    # Create a DataFrame from the results
    visibility_df = pd.DataFrame(visibility_data)

    
    # now we have the data for the producers and the consumers, and we can merge the two by using the commun key, which is startedAT
    #result_df = pd.merge(df, visibility_df, on='startedAt')
    return visibility_df