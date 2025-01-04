import yaml
import pandas as pd
import requests
import numpy as np
import argparse
from date_generator import generate_date_range


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

args = parser.parse_args()

#generate start and end datetime strings 
starttime, endtime = generate_date_range(args.year, args.month, args.end_month)
print(f"Start datetime: {starttime}")
print(f"End datetime: {endtime}")
# read config file

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
#starttime = "2024-06-30T22:00:00Z"
#endtime = "2024-12-29T21:59:59Z"
# convert to UTC time

# get data from producers
dataframesproducers = {}
all_dataprod = []

for producer in production:
    meterid = producer['meteringPoint']
    obiscode = producer['obiscode']
    url = comener['leneda']['url']+comener['leneda']['api']['meteringData']+meterid+"/time-series?startDateTime="+starttime+"&endDateTime="+endtime+"&obisCode="+obiscode
    headers = {
    comener['leneda']['energyId']['header']: comener['leneda']['energyId']['value'],
    comener['leneda']['apiKey']['header']: comener['leneda']['apiKey']['value'],
    }
    df_name = f"df-prod-{producer['name']}"   # dynamically crerate a name for the dataframe, based on the name of the person
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
combined_dfprod['percentage_prod'] = (combined_dfprod['valueprod'] / combined_dfprod['total_sum_prod'] * 100).round(2)

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
    df_name = f"df-cons-{consumer['name']}"   # dynamically crerate a name for the dataframe, based on the name of the person
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
combined_dfcons['percentage_cons'] = (combined_dfcons['valuecons'] / combined_dfcons['total_sum_cons'] * 100).round(2)

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

summarycons.to_csv('consumption.csv', index=False)
summaryprod.to_csv('production.csv', index=False)


# at this point, we may make the calculations ie define what amount of consumed energy was produced and by whom
# then we calculate the total amount of money to be transfered by whom to who
#example of such a line to be used to calculate
#startedAt	percentage_cons	percentage_cons	value	value	total_sum_cons	percentage_prod	percentage_prod	value	value	total_sum_prod																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																					
#	df-cons-christian	df-cons-marc	df-cons-christian	df-cons-marc		df-prod-marc	df-prod-véronique	df-prod-marc	df-prod-véronique																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																						
#2024-10-23 06:15:00+00:00	2.65	97.35	112	4.12	4232	0.0	100.0	0.0	312	312																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																					
#2024-10-23 06:30:00+00:00	8.51	91.49	132	1.42	1552	0.0	100.0	0.0	1096	1096																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																					
# first we calculate the percentage of the power used compared to the power consumed
merged_df['cons_vs_prod'] = (merged_df['total_sum_prod'] / merged_df['total_sum_cons'] * 100).round(2)
# we now limit this value at 100%, as power not consumed will not be paid
merged_df['cons_vs_prod_limit'] = merged_df['cons_vs_prod'].apply(lambda x: 100 if x > 100  else x)
merged_df['max_possible_cons_tot'] = merged_df['total_sum_cons'] * (merged_df['cons_vs_prod_limit'] / 100)
merged_df.to_csv('merged.csv', index=False)
name = 'marc'
#print(merged_df['value'][f"df-cons-{consumer['name']}"])
#print(merged_df['value'][f"df-cons-{name}"])
# algorithm
# !!!! we need to calculate the power available in the community, for the moment calculations are based on the total required power
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# calculate total to be paid
merged_df['total_to_be_paid'] = (merged_df['total_sum_cons'] * (merged_df['cons_vs_prod_limit'] / 100) * kwhprice / 4)
# now calculate the prorate for each pconsumer to pay
totalPowerFromCommunity = 0
count = 0
print("--------------------")
print(f"During the period from {starttime} to {endtime}, the following data are generated")
for consumer in consumption:
    count = count + 1
    df_name = f"df-cons-{consumer['name']}"
    merged_df[f"community_power_used-{consumer['name']}"] = merged_df['max_possible_cons_tot'] * (merged_df['percentage_cons'][df_name] / 100)
    if count == 1:
        merged_df["power_used_by_community"] = merged_df[f"community_power_used-{consumer['name']}"]
    else : 
        merged_df["power_used_by_community"] = merged_df["power_used_by_community"] + merged_df[f"community_power_used-{consumer['name']}"]
    merged_df.to_csv(f"merged{count}.csv", index=False)
    power_used = merged_df[f"community_power_used-{consumer['name']}"].sum()/4
    totalPowerFromCommunity = totalPowerFromCommunity + power_used
    totalPowerUsed = merged_df['valuecons'][df_name].sum()/4
    print(f"{consumer['name']} has used {power_used:.3f} kWh from available power out of o total consumption of {totalPowerUsed:.3f}")
    merged_df[f"has_to_pay-{consumer['name']}"] = (merged_df['total_to_be_paid'] * (merged_df['percentage_cons'][df_name] / 100))
    totalEur = merged_df[f"has_to_pay-{consumer['name']}"].sum()
    totalkWh = merged_df['valuecons'][df_name].sum() / 4
    print(f"{consumer['name']} has to pay {totalEur:.3f} EUR for a total of {power_used:.3f} kWh from community")
merged_df["power_sold_to_grid"] = merged_df["total_sum_prod"] - merged_df["power_used_by_community"]
total_produced = merged_df["total_sum_prod"].sum()/4
total_sold_to_community = merged_df["power_used_by_community"].sum() / 4
total_sold_to_grid = merged_df["power_sold_to_grid"].sum() / 4
print(f"The community consumers consumed {total_sold_to_community:.3f} kWh from the total available power of {total_produced:.3f} kWh and sold {total_sold_to_grid:.3f} kWh to Grid ")
print(f"The community generated internal income of {total_sold_to_community * (kwhprice - normalfee):.2f} EUR (internal fee - normal fee)")
for producer in production:
    df_name = f"df-prod-{producer['name']}"
    #merged_df['has_to_receive'][df_name] = (merged_df['total_to_be_paid'] * (merged_df['percentage_prod'][df_name] / 100))
    merged_df[f"has_to_receive-{producer['name']}"] = (merged_df['total_to_be_paid'] * (merged_df['percentage_prod'][df_name] / 100))
    totalEur = merged_df[f"has_to_receive-{producer['name']}"].sum()
    print(f"{producer['name']} will receive {totalEur:.2f} EUR ")
print("--------------------")
merged_df.to_csv('merged.csv', index=False)
