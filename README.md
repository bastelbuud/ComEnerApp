This application can be used to create an automatic reporting of the energy distribution for a local  Energy Community in Luxemburg.  
The data is based on the Leneda platform.  
The user of the application needs to have the required accesses to the different datasets for consumers and producers.  
You have to create an API key on the Leneda.lu platform first.  
Four each participants, you have to define a name, the distribution point ID's ( f the smartmeters) and the OBIS code ( which is used on order to get the correct data) in a yaml file named config.yaml. The yaml files are stored in a folder named configs. You can have multiple yaml files, and use the provided shell script to parse the configs folder and call the programm for each configuration file.  
You need also to define your Leneda Access id, and the APIkey to access the data.  
The application  requires at least one parameter for the current year and a month, a second month is optional to define a range greater than one month  
The system then calculates the datetime strings for the period for which the date should be retrieved.  
It then downloads the data for all required accounts by using the API provided by the Leneda Platform  
The application uses Pandas in order to handle the data.  
The data is based on power information in 15 minutes slots. To transform the power (kW) into energy (kWh) the value for a 14 minut slot is defined by 4 ( as each hour has 4 15minutes slots)  
The consumption of all participants is feed into a pandas dataframe object.  
The the data for the producers is charged.  
For each producer and consumer, the percentage of provided/consumed power, compared to the total power, is calculated.  
If the amount of produced energy in a 15 min time slot is higher than the consumed power in that timeslot, the calculation for the feee is based on the real consumption.  
If the total produced amount of energy is less than the total consumed energy, the percentage calculated previusly is applied to the fee calculation.  

The fee for the consumption is then defined, based on the previously calculated percentage, amongst the producers.
The result of the calculations are than displayed, and the dataframe is saved in a csv file named merged.csv
