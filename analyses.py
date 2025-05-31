
# this script is used to analyse the different data from the consumers and producers
# it requests all interesting obiscodes for the different POD's and merges them into one dataframe
# it then calculates the total consumption and production for each obiscode
# and adds a final row with the total consumption and production
# it then saves the dataframe to a csv file


# import libraries

import yaml
import pandas as pd
import requests
import numpy as np
import matplotlib.pyplot as plt
import argparse
from date_generator import generate_date_range
from get_sun_data import get_sun_visibility
from add_weatherdata import process_data
import time
import csv
import re
from collections import defaultdict


# define input parameters
parser = argparse.ArgumentParser(
    description='Generate ISO format datetime strings for month ranges with UTC timezone an get the data from that period from Leneda'
)


parser.add_argument(
    '-g', '--groupeDePartageNumber',
    type=str,
    required=True,
    help='What yaml file to use (example : CR00006041)'
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



args = parser.parse_args()

datapath = "/Users/marcdurbach/Development/python/ComEner-calculator/data"
configpath = "/Users/marcdurbach/Development/python/ComEner-calculator/configs"
yamlFileToUse = configpath+"/"+args.groupeDePartageNumber+".yaml"
groupeDePartage = args.groupeDePartageNumber
calcYear = args.year
calcMonth = args.month
# generate timestring to prefix file names
ftimestr = time.strftime("%Y%m%d-%H")
# api to get sunrise and sunset
sunApi = "https://api.sunrisesunset.io/json?lat=49.819294&lng=6.274638&date=2024-07-01&time_format=24"
#generate start and end datetime strings 
starttime, endtime = generate_date_range(args.year, args.month, args.end_month)
print(f"Start datetime: {starttime}")
print(f"End datetime: {endtime}")
# read config file
csv_data = [["Nom", "Consommation", "a payer","Production","a recevoir"]]
with open(yamlFileToUse, 'r') as file:
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

# start data retrieval
# get data from producers


# This will hold all DataFrames keyed by name
dataframes = {}
# create obiscode list for producers
# production, autoconsommation, comm locsl, com nat, grid
obiscode_producers = ["1-1:2.29.0","1-65:2.29.1","1-65:2.29.2","1-65:2.29.3","1-65:2.29.9"]
#production (0), partagé avec soi-même (1), partagé par CEL (2), partagé_résidentiel (3)), vendu fournisseur(9)
obiscode_consumers = ["1-1:1.29.0","1-65:1.29.1","1-65:1.29.2","1-65:1.29.3","1-65:1.29.9"]
#consommation (0),autoconsommation_air (1), consommation par CEL (2), autoconsommation _résidentiel (3)), acheté fournisseur(9)
merged_df = None
for obiscode in obiscode_producers:
    print(obiscode)
    for producer in production:
        meterid = producer['meteringPoint']
        # create GET request for the Leneda Platform
        url = comener['leneda']['url']+comener['leneda']['api']['meteringData']+meterid+"/time-series?startDateTime="+starttime+"&endDateTime="+endtime+"&obisCode="+obiscode
        print("producer url : ",url)
        headers = {
        comener['leneda']['energyId']['header']: comener['leneda']['energyId']['value'],
        comener['leneda']['apiKey']['header']: comener['leneda']['apiKey']['value'],
        }
        df_name = f"df-prod-{producer['name']}-{obiscode}"   # dynamically create a name for the dataframe, based on the name of the person
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Make sure the request succeeded
        json_data = response.json() # store the result in a json object
        items = json_data.get('items', []) # get the items from the json object

        # Only process if there are items, the call may return a result, but no items, if the POD is not configured yet
        if not items:
            print(f"⚠️ No data returned for {producer['name']} with OBIS {obiscode}. Skipping.")
            continue

        df = pd.DataFrame(items)

        # Only keep 'startedAt' and 'value' if they exist
        if 'startedAt' not in df.columns or 'value' not in df.columns:
            print(f"⚠️ 'startedAt' or 'value' missing in data for {df_name}. Skipping.")
            continue

        df = df[['startedAt', 'value']].copy()
        df['startedAt'] = pd.to_datetime(df['startedAt'])
        df = df.rename(columns={'value': f'prod_{producer["name"]}_{obiscode}'})
        print(df)

        # add the dataframe to the dictionary with the name of the producer and the obiscode

        dataframes[df_name] = df

# get data from consumers
for obiscode in obiscode_consumers:
    print(obiscode)
    for consumer in consumption:
        meterid = consumer['meteringPoint']
        # create GET request for the Leneda Platform
        url = comener['leneda']['url']+comener['leneda']['api']['meteringData']+meterid+"/time-series?startDateTime="+starttime+"&endDateTime="+endtime+"&obisCode="+obiscode
        print("producer url : ",url)
        headers = {
        comener['leneda']['energyId']['header']: comener['leneda']['energyId']['value'],
        comener['leneda']['apiKey']['header']: comener['leneda']['apiKey']['value'],
        }
        df_name = f"df-cons-{consumer['name']}-{obiscode}"   # dynamically create a name for the dataframe, based on the name of the person
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Make sure the request succeeded
        json_data = response.json()
        items = json_data.get('items', [])

        # Only process if there is data
        if not items:
            print(f"⚠️ No data returned for {consumer['name']} with OBIS {obiscode}. Skipping.")
            continue

        df = pd.DataFrame(items)

        # Only keep 'startedAt' and 'value' if they exist
        if 'startedAt' not in df.columns or 'value' not in df.columns:
            print(f"⚠️ 'startedAt' or 'value' missing in data for {df_name}. Skipping.")
            continue

        df = df[['startedAt', 'value']].copy()
        df['startedAt'] = pd.to_datetime(df['startedAt'])
        df = df.rename(columns={'value': f'cons_{consumer["name"]}_{obiscode}'})
        print(df)

        # add the dataframe to the dictionary with the name of the consumer and the obiscode

        dataframes[df_name] = df
# at this moment, all dataframes are in the dictionary dataframes as received by the API queries

for df in dataframes.values():
    if merged_df is None:
        merged_df = df
    else:
        merged_df = pd.merge(merged_df, df, on='startedAt', how='outer')
# now the dataframes are merged into one dataframe, using the startedAt column as the key
# Sort the DataFrame by 'startedAt' column
merged_df['startedAt'] = pd.to_datetime(merged_df['startedAt'])
# Sort by timestamp (optional)
merged_df = merged_df.sort_values(by='startedAt')

# now add the sums per obiscode and the total sums of all columns

# Step 1: Group columns by OBIS code
obiscode_groups = {}
for col in merged_df.columns:
    if col == 'startedAt':
        continue
    match = re.search(r'(\d+-\d+:\d+\.\d+\.\d+)$', col)
    if match:
        obis = match.group(1)
        obiscode_groups.setdefault(obis, []).append(col)

# Step 2: Add per-OBIS sum columns
for obiscode, cols in obiscode_groups.items():
    merged_df[f'sum_{obiscode}'] = merged_df[cols].sum(axis=1, skipna=True)
# we need to get the values now, as in the next step we add the sum, if the following 4 lines are calculated later the are double the value
total_cons = 0 # 1-1:1.29.0
total_prod = 0 # 1-1:2.29.0
total_auto_cons_self = 0 # 1-65:1.29.1
total_auto_cons_res =0 # 1-65:1.29.3
total_cons_local = 0 # 1-65:1.29.2
total_purchased = 0 # 1-65:1.29.9
total_sold_provider = 0 # 1-65:2.29.9
#if 'sum_1-65:2.29.0' in merged_df.columns:
#    total_prod = merged_df["sum_1-1:2.29.0"].sum()/4
if 'sum_1-1:1.29.0' in merged_df.columns:
    total_cons = merged_df["sum_1-1:1.29.0"].sum()/4
if 'sum_1-1:2.29.0' in merged_df.columns:
    total_prod = merged_df["sum_1-1:2.29.0"].sum()/4    
if 'sum_1-65:2.29.1' in merged_df.columns:
    total_auto_cons_self = merged_df["sum_1-65:2.29.1"].sum()/4
if 'sum_1-65:2.29.3' in merged_df.columns:
    total_auto_cons_res =  merged_df["sum_1-65:2.29.3"].sum()/4
total_auto_cons = total_auto_cons_self + total_auto_cons_res
if 'sum_1-65:2.29.2' in merged_df.columns:
    total_cons_local = merged_df["sum_1-65:2.29.2"].sum()/4
if 'sum_1-65:1.29.9' in merged_df.columns:
    total_purchased = merged_df["sum_1-65:1.29.9"].sum()/4
total_sold_community = total_prod - total_auto_cons - total_cons_local
if 'sum_1-65:2.29.9' in merged_df.columns:
    total_sold_provider = merged_df["sum_1-65:2.29.9"].sum()/4
# Step 3: Add a final row with total sums per column

total_row = merged_df.drop(columns='startedAt').sum(numeric_only=True)/4
total_row['startedAt'] = 'TOTAL'
merged_df = pd.concat([merged_df, pd.DataFrame([total_row])], ignore_index=True)#


# Save to CSV
merged_df.to_csv(f'{datapath}/{groupeDePartage}-analyses.csv', index=False)
# once the file saved as csv we may add lines at the end to conatin new calculated data

# Calculate the difference between production and send to the grid
#total_prod = merged_df["sum_1-1:2.29.0"].sum()/4
#total_auto_cons = (merged_df["sum_1-65:2.29.1"].sum()/4) + (merged_df["sum_1-65:2.29.3"].sum()/4)
#total_cons_local = merged_df["sum_1-65:2.29.2"].sum()/4
#total_sold = total_prod - total_auto_cons - total_cons_local

csv_data = [["Libelle", "Value"]]
csv_data.append(['Groupe de partage', groupeDePartage])
csv_data.append(['Year',calcYear])
csv_data.append (['Mois', calcMonth])
csv_data.append(['total production', round(total_prod, 2)])
csv_data.append(['total consommation', round(total_cons, 2)])
csv_data.append(['total auto consommation self', round(total_auto_cons_self, 2)])
csv_data.append(['total auto consommation résidentiel', round(total_auto_cons_res, 2)])
csv_data.append(['total auto consommation', round(total_auto_cons, 2)])
csv_data.append(['total consommation local', round(total_cons_local, 2)])
csv_data.append(['total purchased', round(total_purchased, 2)])
csv_data.append(['total sold to provider', round(total_sold_provider, 2)])
with open(f"{datapath}/{groupeDePartage}-analyses-summary.csv", 'w', newline='') as csv_file:
    csv_writer = csv.writer(csv_file, delimiter=';')

    csv_writer.writerows(csv_data) 

print("CSV file 'analyses.csv' has been created.")  
#
