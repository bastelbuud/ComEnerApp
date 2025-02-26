import yaml
import pandas as pd
import requests
import numpy as np
import argparse
from date_generator import generate_date_range
from get_sun_data import get_sun_visibility
from add_weatherdata import process_data
import time
import csv




# define input parameters
parser = argparse.ArgumentParser(
    description='Generate ISO format datetime strings for month ranges with UTC timezone an get the data from that period from Leneda'
)

parser.add_argument(
    '-y', '--year',
    type=int,
    required=True,
    help='Year (positive integer)'
)

parser.add_argument(
    '-m', '--month',
    type=int,
    required=True,
    help='Starting month (1-12)'
)

parser.add_argument(
    '-e', '--end-month',
    type=int,
    required=False,
    help='Optional ending month (1-12)'
)

parser.add_argument(
    '-d', '--daylight',
    action='store_true',
    help='Optional daylight analyses'
)

parser.add_argument(
    '-w', '--weather',
    action='store_true',
    help='Optional weather retrieval'
)

args = parser.parse_args()
if args.daylight == True:
    checkDaylightUsage = True
else:
    checkDaylightUsage = False

if args.weather == True:
    checkweather = True
else:
    checkweather = False

# generate timestring to prefix file names
ftimestr = time.strftime("%Y%m%d")
# api to get sunrise and sunset
sunApi = "https://api.sunrisesunset.io/json?lat=49.819294&lng=6.274638&date=2024-07-01&time_format=24"
#generate start and end datetime strings 
starttime, endtime = generate_date_range(args.year, args.month, args.end_month)
print(f"Start datetime: {starttime}")
print(f"End datetime: {endtime}")
# read config file
csv_data = [["Nom", "Consommation", "a payer","a recevoir"]]
with open('config.yaml', 'r') as file:
    comener = yaml.safe_load(file)
# get consumers data from config file
consumers = comener['consumers']['names']
consumption = []
idx = 0
for consumer in consumers:
    consumption.append({"name":consumer,"meteringPoint":comener['consumers']['smartmeters'][idx],"obiscode":comener['consumers']['obiscode'][idx]})
    idx = idx+1
# get producers data from config file and load them in a json object
producers = comener['producers']['names']
production = []
idx = 0
for producer in producers:
    production.append({"name":producer,"meteringPoint":comener['producers']['smartmeters'][idx],"obiscode":comener['producers']['obiscode'][idx]})
    idx = idx+1
print("Consumer details")
for element in consumption:
    print(element)
print("Producer details")
for element in production:
    print(element)

# read price from yaml file
kwhprice = comener['pricing']['kwhprice'] 
normalfee = comener['pricing']['normalfee']
network = comener['pricing']['network']
consumerprice = comener['pricing']['consumerprice']
tax = comener['pricing']['tax']
compensation = comener['pricing']['compensation']
tva = comener['pricing']['tva']
tvamul = 1 + tva
kwhpriceCons = (consumerprice + network + tax + compensation) * tvamul 

# get data from producers
dataframesproducers = {}
all_dataprod = []

for producer in production:
    meterid = producer['meteringPoint']
    obiscode = producer['obiscode']
    # create GET request for the Leneda Platform
    url = comener['leneda']['url']+comener['leneda']['api']['meteringData']+meterid+"/time-series?startDateTime="+starttime+"&endDateTime="+endtime+"&obisCode="+obiscode
    headers = {
    comener['leneda']['energyId']['header']: comener['leneda']['energyId']['value'],
    comener['leneda']['apiKey']['header']: comener['leneda']['apiKey']['value'],
    }
    df_name = f"df-prod-{producer['name']}"   # dynamically create a name for the dataframe, based on the name of the person
    response = requests.get(url, headers=headers)
    df = pd.DataFrame(response.json())
    df['value'] = df['items'].apply(lambda x: x['value'])
    df['startedAt'] = df['items'].apply(lambda x: pd.to_datetime(x['startedAt']))
    df = df.drop('items', axis=1)
    dataframesproducers[df_name] = df
    # Prepare data for summary
    summary_data = {
        'startedAt': df['startedAt'],
        'valueprod': df['value'],
        'source': df_name
    }
    all_dataprod.append(pd.DataFrame(summary_data))
combined_dfprod = pd.concat(all_dataprod, ignore_index=True)
# Calculate total sum for each timestamp
timestamp_sums = combined_dfprod.groupby('startedAt')['valueprod'].sum().reset_index()
timestamp_sums.columns = ['startedAt', 'total_sum_prod']   
# Add total sums back to combined DataFrame
combined_dfprod = combined_dfprod.merge(timestamp_sums, on='startedAt')
# Calculate percentages
combined_dfprod['percentage_prod'] = (combined_dfprod['valueprod'] / combined_dfprod['total_sum_prod'] * 100).round(3)

# Update individual dataframes with percentages
for df_name in dataframesproducers.keys():
    mask = combined_dfprod['source'] == df_name
    df_with_pct = combined_dfprod[mask].copy()
    dataframesproducers[df_name] = dataframesproducers[df_name].assign(
        percentage=df_with_pct['percentage_prod'].values,
        total_sum=df_with_pct['total_sum_prod'].values
    )

# Create summary with percentages by source
summaryprod = combined_dfprod.pivot_table(
    index='startedAt',
    columns='source',
    values=['valueprod', 'percentage_prod'],
    aggfunc='first'
).reset_index()

# Add total sums to summary
summaryprod['total_sum_prod'] = timestamp_sums['total_sum_prod']
    


# get data from consumers
dataframesconsumers = {}
all_datacons = []

for consumer in consumption:
    meterid = consumer['meteringPoint']
    obiscode = consumer['obiscode']
    url = comener['leneda']['url']+comener['leneda']['api']['meteringData']+meterid+"/time-series?startDateTime="+starttime+"&endDateTime="+endtime+"&obisCode="+obiscode
    headers = {
    comener['leneda']['energyId']['header']: comener['leneda']['energyId']['value'],
    comener['leneda']['apiKey']['header']: comener['leneda']['apiKey']['value'],
    }
    df_name = f"df-cons-{consumer['name']}"   # dynamically create a name for the dataframe, based on the name of the person
    response = requests.get(url, headers=headers)
    df = pd.DataFrame(response.json())
    df['value'] = df['items'].apply(lambda x: x['value'])
    df['startedAt'] = df['items'].apply(lambda x: pd.to_datetime(x['startedAt']))
    df = df.drop('items', axis=1)
    dataframesconsumers[df_name] = df
    # Prepare data for summary
    summary_data = {
        'startedAt': df['startedAt'],
        'valuecons': df['value'],
        'source': df_name
    }
    all_datacons.append(pd.DataFrame(summary_data))
combined_dfcons = pd.concat(all_datacons, ignore_index=True)

# Calculate total sum for each timestamp
timestamp_sums = combined_dfcons.groupby('startedAt')['valuecons'].sum().reset_index()
timestamp_sums.columns = ['startedAt', 'total_sum_cons']   
# Add total sums back to combined DataFrame
combined_dfcons = combined_dfcons.merge(timestamp_sums, on='startedAt')

# Calculate percentages
combined_dfcons['percentage_cons'] = (combined_dfcons['valuecons'] / combined_dfcons['total_sum_cons'] * 100).round(3)

# Update individual dataframes with percentages
for df_name in dataframesconsumers.keys():
    mask = combined_dfcons['source'] == df_name
    df_with_pct = combined_dfcons[mask].copy()
    dataframesconsumers[df_name] = dataframesconsumers[df_name].assign(
        percentage=df_with_pct['percentage_cons'].values,
        total_sum=df_with_pct['total_sum_cons'].values
    )

# Create summary with percentages by source
summarycons = combined_dfcons.pivot_table(
    index='startedAt',
    columns='source',
    values=['valuecons', 'percentage_cons'],
    aggfunc='first'
).reset_index()

# Add total sums to summary
summarycons['total_sum_cons'] = timestamp_sums['total_sum_cons']

# now we have the data for the producers and the consumers, and we can merge the two by using the commun key, which is startedAT
merged_df = pd.merge(summarycons, summaryprod, on='startedAt')

# we store the files as csv to check the data manually
summarycons.to_csv(f'{ftimestr}-consumption.csv', index=False, sep=";")
summaryprod.to_csv(f'{ftimestr}production.csv', index=False, sep=";")

# at this point, we may make the calculations ie define what amount of consumed energy was produced and by whom
# then we calculate the total amount of money to be transfered by whom to who
# 																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																					
# first we calculate the percentage of the power used compared to the power consumed
merged_df['cons_vs_prod'] = (merged_df['total_sum_prod'] / merged_df['total_sum_cons'] * 100).round(2)
# we now limit this value at 100%, as power not consumed will not be paid
merged_df['cons_vs_prod_limit'] = merged_df['cons_vs_prod'].apply(lambda x: 100 if x > 100  else x)
merged_df['max_possible_cons_tot'] = merged_df['total_sum_cons'] * (merged_df['cons_vs_prod_limit'] / 100)
# algorithm
# !!!! we need to calculate the power available in the community, for the moment calculations are based on the total required power
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# calculate total to be paid:
# total consumed, but to a maximum of produced energy, multiplied by the price and divided by 4 (in order to transform power in energy for a 15 min slot)
merged_df['total_to_be_paid'] = (merged_df['total_sum_cons'] * (merged_df['cons_vs_prod_limit'] / 100) * kwhprice / 4)
# now calculate the prorate for each consumer to pay
totalEnergyFromCommunity = 0
count = 0
print("--------------------")
print(f"During the period from {starttime} to {endtime}, the following data have been generated:")
for consumer in consumption:
    count = count + 1
    df_name = f"df-cons-{consumer['name']}"
    # we calculate the share of consumed energy, produced by the community, per consumer
    merged_df[f"community_power_used-{consumer['name']}"] = merged_df['max_possible_cons_tot'] * (merged_df['percentage_cons'][df_name] / 100)
    # we add the consumed energy per consumer to get a total, if this is the first consumer, we create the column
    if count == 1:
        merged_df["power_used_by_community"] = merged_df[f"community_power_used-{consumer['name']}"]
    else : 
        merged_df["power_used_by_community"] = merged_df["power_used_by_community"] + merged_df[f"community_power_used-{consumer['name']}"]
    energy_used = merged_df[f"community_power_used-{consumer['name']}"].sum()/4
    totalEnergyFromCommunity = totalEnergyFromCommunity + energy_used
    totalEnergyUsed = merged_df['valuecons'][df_name].sum()/4
    print(f"{consumer['name']} has used {energy_used:.3f} kWh from available power out of a total consumption of {totalEnergyUsed:.3f}")
    merged_df[f"has_to_pay-{consumer['name']}"] = (merged_df['total_to_be_paid'] * (merged_df['percentage_cons'][df_name] / 100))
    totalEur = merged_df[f"has_to_pay-{consumer['name']}"].sum()
    difference = ((totalEur/ kwhprice) * kwhpriceCons) - totalEur
    totalkWh = merged_df['valuecons'][df_name].sum() / 4
    print(f"{consumer['name']} has to pay {totalEur:.3f} EUR for a total of {energy_used:.3f} kWh from community, this is {difference:.3f} less than the fee to be paid to the provider ({(difference/totalEur)*100:.2f} %)")
    # add line to array
    csv_data.append([consumer['name'], energy_used, totalEur])
merged_df["power_sold_to_grid"] = merged_df["total_sum_prod"] - merged_df["power_used_by_community"]
total_produced = merged_df["total_sum_prod"].sum()/4
total_sold_to_community = merged_df["power_used_by_community"].sum() / 4
total_sold_to_grid = merged_df["power_sold_to_grid"].sum() / 4
print(f"The community consumers consumed {total_sold_to_community:.3f} kWh from the total available energy of {total_produced:.3f} kWh and sold {total_sold_to_grid:.3f} kWh to the Grid ")
print(f"The community generated internal income for producers of {total_sold_to_community * (kwhprice - normalfee):.2f} EUR (internal fee - normal fee)")
print(f"The community generated an internal saving for consumers of {total_sold_to_community * (kwhpriceCons - kwhprice):.2f} EUR")
for producer in production:
    df_name = f"df-prod-{producer['name']}"
    print(df_name)
    #merged_df['has_to_receive'][df_name] = (merged_df['total_to_be_paid'] * (merged_df['percentage_prod'][df_name] / 100))
    merged_df[f"has_to_receive-{producer['name']}"] = (merged_df['total_to_be_paid'] * (merged_df['percentage_prod'][df_name] / 100))
    totalEur = merged_df[f"has_to_receive-{producer['name']}"].sum()
    difference = totalEur - ((totalEur/ kwhprice) * normalfee)
    print(f"{producer['name']} will receive {totalEur:.2f} EUR, this is {difference:.3f} more than the fee received by the provider ({(difference/totalEur)*100:.2f} %)")
    csv_data.append([producer['name'],0,0,totalEur)])
print("--------------------")
merged_df.to_csv(f'{ftimestr}-merged.csv', index=False, sep=";")
# now enrich the dataset with the sunset and sunrise data
# loop through the datetime column and add a boolean if the sun is visible
if checkDaylightUsage:
    print("We are now retrieving tha data for daylight production analyses")
    print("This will take a long time based on the selected timerange")
    df_with_visibility = get_sun_visibility(merged_df,'startedAt')
    df_with_visibility.to_csv('withsun.csv', index=False)
    merged_df["sun_visible"] = df_with_visibility["sun_visible"]
    #or
    #merged_df = merged_df.merge(df_with_visibility[['startedAt', 'sun_visible']], on='startedAt')
    # save the csv file for further analysis
    # conditional sums based on : daylight_sum = df[df['daylight'] == True]['energy_consumption'].sum()
    merged_df.to_csv(f'{ftimestr}-merged_withsun.csv', index=False, sep=";")
    #now make the analyses for day and night consumption
    df = pd.read_csv(f'{ftimestr}-merged_withsun.csv',sep=";")

    # View the first 5 rows
    df.head()
    daylight_cons_sum = merged_df[merged_df['sun_visible'] == True]['total_sum_cons'].sum() / 4
    daylight_prod_sum = merged_df[merged_df['sun_visible'] == True]['total_sum_prod'].sum() / 4
    ratio = (daylight_prod_sum/daylight_cons_sum) * 100
    print(f"Considering the consumption during daylight({daylight_cons_sum:.2f}), and the production {daylight_prod_sum:.2f} , we have a ratio of {ratio:.2f}%")
    night_cons_sum = merged_df[merged_df['sun_visible'] == False]['total_sum_cons'].sum() / 4
    night_prod_sum = merged_df[merged_df['sun_visible'] == False]['total_sum_prod'].sum() / 4
    ratio = (night_prod_sum/night_cons_sum) * 100
    print(f"Considering the consumption during night({night_cons_sum:.2f}), and the production {night_prod_sum:.2f} , we have a ratio of {ratio:.2f}%")
    total_cons_sum = merged_df['total_sum_cons'].sum() / 4
    total_prod_sum = merged_df['total_sum_prod'].sum() / 4
    ratio = (total_prod_sum/total_cons_sum) * 100
    print(f"Total consumption ({total_cons_sum:.2f}), and total production {total_prod_sum:.2f} , we have a ratio of {ratio:.2f}%")
else:
    print("Daylight checking skipped")
# loop through the datetime column and add a boolean if the sun is visible
if checkweather:
    print("We are now retrieving tha data for weatheranalyses")
    print("This will take a long time based on the selected timerange")
    merged_df['day_of_week'] = merged_df['startedAt'].dt.dayofweek
    merged_df['day_of_year'] = merged_df['startedAt'].dt.dayofyear
    print("generating the merged_df_days.csv file")
    merged_df.to_csv(f'{ftimestr}-merged_df_days.csv', index=False, sep=";")
    df_with_weather = process_data(merged_df,'startedAt')
    #merged_df.merge(df_with_weather, on='startedAt')   : this does not work, however, adding each column individually works fine 
    merged_df["temperature"]=  df_with_weather["temperature"]
    merged_df["weather_condition"]=  df_with_weather["weather_condition"]
    merged_df["dew_point"]=  df_with_weather["dew_point"]
    merged_df["rain"]=  df_with_weather["rain"]
    merged_df["snowfall"]=  df_with_weather["snowfall"]
    merged_df["cloud_cover"]=  df_with_weather["cloud_cover"]
    print("generating the merged_weather.csv file")
    merged_df.to_csv(f'{ftimestr}-merged_weather.csv', index=False, sep=";")
# generate csv file as summary
with open(f"decompte-{starttime}-{endtime}", 'w', newline='') as csv_file:
    csv_writer = csv.writer(csv_file, delimiter=';')

    csv_writer.writerows(csv_data) 
print("Programm terminated")