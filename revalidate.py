import json
import requests
from datetime import datetime, timedelta

sabre_url = "https://api-crt.cert.havail.sabre.com/v4/shop/flights/revalidate"
auth_token = "T1RLAQLTVBLaX6y2wmWiXMq1qqMglDsjAHL6fTqRG9lfrn70SRB1F2TJW5gvnfZtgOTD46VKAADgzA7hGAIb6ACED4l/W/0hh6yXhnQOM7r+SUHnXZjpfZcHV2TtRh1WatvAkaI83bapgMV4cBJDHSs7MWZhLiZzOvIot0vv9MJ7pS8MkFLK1UkCgsvsrY+euBEvGhkjzpMM9XcTyWkCifIE2DfcyItcD8lcjoo/+hU/1IjrL1HmZOKpl21w1LjMxyFihgUhekSr4z4pJcdQvmmERJUg5U2r6dLbtaj38++NGZKMLkKgvQA7rV7zIUUAZrrzVWXsnDGtiE5ZHnmlucssGTBltmVVBMd1mHGSdlHwhSJ0kGJYK9c*"




def revalidate_response(parsed_response,fare_level,from_airport, to_airport, outbound_date,return_date):
	# print(parsed_response)
	revalidated_array = []
	for single_trip in parsed_response["trips"]:
		# print(single_trip)
		cabin_pref = fare_level
		from_airport = from_airport
		to_airport = to_airport
		outbound_flights = single_trip["flight_info"]["outbound_flight_info"]["leg_info"]
		outbound_airline = single_trip["flight_info"]["outbound_flight_info"]["airline"]
		return_flights = single_trip["flight_info"]["return_flight_info"]["leg_info"]
		return_airline = single_trip["flight_info"]["return_flight_info"]["airline"]
		outbound_date = outbound_date
		return_date = return_date
		revalidate_json = generate_revalidate_json(cabin_pref,from_airport,to_airport,outbound_flights,outbound_airline,return_flights,return_airline,outbound_date,return_date)
		print(single_trip["flight_info"]["outbound_flight_info"]["stops"])
		if single_trip["flight_info"]["outbound_flight_info"]["stops"] != 0:
			print(revalidate_json)
		data = revalidate_with_sabre(revalidate_json)
		is_valid = revalidate_contains_flights(data)
		if is_valid:
			modified_single_trip = overwrite_costs(single_trip, data)
			revalidated_array.append(modified_single_trip)
			# print(single_trip)
	trips = {
		"trips":revalidated_array
	}
	return trips

def generate_revalidate_json(cabin_pref,from_airport,to_airport,outbound_flights,outbound_airline,return_flights,return_airline,outbound_date,return_date):
	TravelPreferences = {
			"TPA_Extensions": {
				"DataSources": {
					"ATPCO": "Enable",
					"LCC": "Enable",
					"NDC": "Enable"
				}
			},
			"CabinPref": [
				{
					"Cabin": cabin_pref
				}
			]
	}
	outbound_flight_array = flight_array_generator(outbound_flights,outbound_airline,outbound_date,cabin_pref)
	OutBoundFlightInfo = {
		"RPH": "0",
		"DepartureDateTime": outbound_date +"T"+ outbound_flights[0]["departure_time"][:8],
		"OriginLocation": {
			"LocationCode": from_airport
		},
		"DestinationLocation": {
			"LocationCode": to_airport
		},
		"TPA_Extensions": {
			"Flight": outbound_flight_array
		}
	}
	InboundFlightInfo = {}
	return_flight_array = []
	if return_date:
		return_flight_array = flight_array_generator(return_flights,return_airline,return_date,cabin_pref)
		InboundFlightInfo = {
			"RPH": "1",
			"DepartureDateTime": return_date +"T"+ return_flights[0]["departure_time"][:8],
			"OriginLocation": {
				"LocationCode": to_airport
			},
			"DestinationLocation": {
				"LocationCode": from_airport
			},
			"TPA_Extensions": {
				"Flight": return_flight_array
			}
		}
	POS = {
		"Source": [
				{
					"PseudoCityCode": "F9CE",
					"RequestorID": {
						"CompanyName": {
							"Code": "TN"
						},
						"ID": "1",
						"Type": "1"
					}
				}
			]
		}
	TPA_Extensions = {
		"IntelliSellTransaction": {
				"RequestType": {
					"Name": "200ITINS"
				}
			}
		}
	TravelerInfoSummary = {
		"AirTravelerAvail": [
				{
					"PassengerTypeQuantity": [
						{
							"Code": "ADT",
							"Quantity": 1
						}
					]
				}
			],
			"SeatsRequested": [
				1
			]
		}
	if return_date:
		OriginDestinationInformation = [
			OutBoundFlightInfo,
			InboundFlightInfo
		]
	else:
		OriginDestinationInformation = [
			OutBoundFlightInfo
		]	
	json_payload = json.dumps({
		"OTA_AirLowFareSearchRQ":{
			"AvailableFlightsOnly": True,
			"Version": "v4",
			"TravelPreferences": TravelPreferences,
			"OriginDestinationInformation": OriginDestinationInformation,
			"POS": POS,
			"TPA_Extensions": TPA_Extensions,
			"TravelerInfoSummary": TravelerInfoSummary
		}
	})
	return json_payload


def revalidate_with_sabre(payload):
	headers = {
	'accept': 'application/json',
	'Content-Type': 'application/json',
	'authorization': 'Bearer ' + auth_token
	}
	raw_response = requests.request("POST", sabre_url, headers=headers, data=payload)
	data = json.loads(raw_response.text)
		# print(data)data
	return data

def revalidate_contains_flights(data):
	if int(data["groupedItineraryResponse"]["statistics"]["itineraryCount"]) > 0:
		return True
	return False




def flight_array_generator(flight_info,airline,date,fare_level):
	start_date = datetime.strptime(date, '%Y-%m-%d').date()
	land_date = start_date
	flight_array = []
	for flight in flight_info:
		land_date = start_date + timedelta(days=flight["date_adjustment"])
		start_date_time = datetime.combine(start_date,datetime.strptime(flight["departure_time"][:8], '%H:%M:%S').time())
		land_date_time = datetime.combine(start_date,datetime.strptime(flight["landing_time"][:8], '%H:%M:%S').time())
		temp_outbound_flight_dict = {
			"Number": flight["flight_number"],
			# 2023-08-11T00:00:00
			"DepartureDateTime":start_date_time.strftime('%Y-%m-%dT%H:%M:%S'),
			"ArrivalDateTime":land_date_time.strftime('%Y-%m-%dT%H:%M:%S'),
			"Type": "A",
			"ClassOfService": flight["booking_code"],
			"OriginLocation": {
				"LocationCode": flight["departure_airport"]
				},
			"DestinationLocation": {
				"LocationCode": flight["arrival_airport"]
			},
			"Airline":{
				"Marketing": airline
			}
		}
		flight_array.append(temp_outbound_flight_dict)
		start_date = land_date
	return flight_array


def overwrite_costs(single_trip, data):
	# print(single_trip)
	# print(data)
	fare_dict = data["groupedItineraryResponse"]["itineraryGroups"][0]["itineraries"][0]["pricingInformation"][0]["fare"]["passengerInfoList"][0]["passengerInfo"]["passengerTotalFare"]
	single_trip["price_info"]["total_price"] = fare_dict["totalFare"]
	single_trip["price_info"]["base_fare"] = fare_dict["baseFareAmount"]
	single_trip["price_info"]["tax_ammount"] = fare_dict["totalTaxAmount"]
	single_trip["is_validated"] = True
	return(single_trip)

