import requests
import json
import revalidate
"""
Variables needed:
from_airport: string, airport code
to_airport: string, airport code
round_trip: bool
outbound_date: ISO date format
return_date: ISO date format, required if round_trip is true
fare_level: optional. Defaults to economy. Other options: "first", "premium_business", "business", "premium_economy", "economy"
			(P), First (F), Premium Business (J), Business (C), Premium Economy (S), Economy (Y).




"""

sabre_url = "https://api-crt.cert.havail.sabre.com/v4/offers/shop"
auth_token = ""



def get_flights(from_airport, to_airport,outbound_date,return_date,fare_level,validate_flights,direct_flights_only):
	sabre_fare_level = get_sabre_fare_level(fare_level)
	raw_response = make_api_sabre(from_airport, to_airport,outbound_date,return_date,sabre_fare_level,direct_flights_only)
	parsed_response = response_parser(raw_response,direct_flights_only)
	x = parsed_response
	if validate_flights:
		x = revalidate_flight(parsed_response, fare_level, from_airport, to_airport,outbound_date,return_date)
	return x


def make_api_sabre(from_airport, to_airport,outbound_date,return_date,sabre_fare_level,direct_flights_only):
	headers = {
	'accept': 'application/json',
	'Content-Type': 'application/json',
	'authorization': 'Bearer ' + auth_token
	}
	CabinPref = [{
	"Cabin":sabre_fare_level
	}]
	outbound_flight_info = {
		"DepartureDateTime": outbound_date + "T00:00:00",
		"DestinationLocation":{
			"LocationCode":to_airport
		},
		"OriginLocation":{
		"LocationCode": from_airport
		},
		"RPH": "0"
	}
	if return_date:
		return_date = return_date + "T00:00:00"
	inbound_flight_info = {
		"DepartureDateTime": return_date,
		"DestinationLocation":{
			"LocationCode":from_airport
		},
		"OriginLocation":{
		"LocationCode": to_airport
		},
		"RPH": "1" #RPH is order of flights. Since this is return it's 1
		}
	if return_date:
		OriginDestinationInformation = [
			outbound_flight_info,
			inbound_flight_info
		]
	else:
		OriginDestinationInformation = [
			outbound_flight_info
		]
	POS = {
	"Source":[{
		"PseudoCityCode": "F9CE",
		"RequestorID": {
			"CompanyName": {
			  "Code": "TN"
			},
			"ID": "1",
			"Type": "1"
		  }
		}]}
	TPA_Extensions = {
	"IntelliSellTransaction": {
		"RequestType": {
		  "Name": "200ITINS"
		}
	  }
	}
	TravelPreferences = {
	  "TPA_Extensions": {
		"DataSources": {
		  "ATPCO": "Enable",
		  "LCC": "Enable",
		  "NDC": "Enable"
		}
	  },
	  "CabinPref":CabinPref
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
	json_payload=json.dumps({
	"OTA_AirLowFareSearchRQ":{
	"DirectFlightsOnly":direct_flights_only,
	"AvailableFlightsOnly":True,
	"TravelPreferences":TravelPreferences,
	"OriginDestinationInformation":OriginDestinationInformation,
	"POS":POS,
	"TPA_Extensions":TPA_Extensions,
	"TravelPreferences":TravelPreferences,
	"TravelerInfoSummary":TravelerInfoSummary,
	"Version":"v4"}})
	print(json_payload)
	response = requests.request("POST", sabre_url, headers=headers, data=json_payload)
	# print(response.text)
	return response


def response_parser(raw_response,direct_flights_only):
	# print()
	data = json.loads(raw_response.text)
	groupedItineraryResponse = data["groupedItineraryResponse"]
	baggage_allowance = get_baggage_allowance(groupedItineraryResponse["baggageAllowanceDescs"])
	# print(type(groupedItineraryResponse))
	itineraries = groupedItineraryResponse["itineraryGroups"][0]["itineraries"]
	all_flight_info = []
	for itinerary in itineraries:
		try:
			pricing_info_base = itinerary["pricingInformation"][0]["fare"]["passengerInfoList"][0]["passengerInfo"]["passengerTotalFare"]
			flight_info_base = itinerary["pricingInformation"][0]["fare"]["passengerInfoList"][0]["passengerInfo"]["baggageInformation"] or ""
			seats_left = itinerary["pricingInformation"][0]["fare"]["passengerInfoList"][0]["passengerInfo"]["fareComponents"][0]["segments"][0]["segment"]["seatsAvailable"]
			booking_code_array = itinerary["pricingInformation"][0]["fare"]["passengerInfoList"][0]["passengerInfo"]["fareComponents"][0]["segments"]
		except Exception as e:
			continue
		legs = itinerary["legs"]
		# print(booking_code_array)
		leg_info = find_legs(legs,groupedItineraryResponse,booking_code_array)
		flight_info = {}
		if direct_flights_only:
			if (len(leg_info)-1) == 0:
				flight_info = {
					"is_validated":False,
					"price_info":{
						"total_price" : pricing_info_base["totalFare"],
						"base_fare": pricing_info_base["baseFareAmount"],
						"tax_ammount": pricing_info_base["totalTaxAmount"],
						"currency": pricing_info_base["currency"]
						},
					"flight_info":{
					"outbound_flight_info":{
							"airline": flight_info_base[0]["airlineCode"],
							"bag_allowance":baggage_allowance[(int(flight_info_base[0]["allowance"]["ref"])-1)],
							"seats_left":seats_left,
							"stops":len(leg_info[0])-1,
							"leg_info":leg_info[0]
						},
						"return_flight_info":{
							"airline": flight_info_base[1]["airlineCode"] if 1 < len(flight_info_base) else "",
							"bag_allowance":baggage_allowance[(int(flight_info_base[1]["allowance"]["ref"])-1)] if 1 < len(flight_info_base) else "",
							"stops":len(leg_info[0])-1 if 1<len(leg_info) else "",
							"leg_info":leg_info[1] if 1<len(leg_info) else ""
						}

					}}
				all_flight_info.append(flight_info)
		else:
			flight_info = {
				"is_validated":False,
				"price_info":{
					"total_price" : pricing_info_base["totalFare"],
					"base_fare": pricing_info_base["baseFareAmount"],
					"tax_ammount": pricing_info_base["totalTaxAmount"],
					"currency": pricing_info_base["currency"]
					},
				"flight_info":{
				"outbound_flight_info":{
						"airline": flight_info_base[0]["airlineCode"],
						"bag_allowance":baggage_allowance[(int(flight_info_base[0]["allowance"]["ref"])-1)],
						"seats_left":seats_left,
						"stops":len(leg_info[0])-1,
						"leg_info":leg_info[0]
					},
					"return_flight_info":{
						"airline": flight_info_base[1]["airlineCode"] if 1 < len(flight_info_base) else "",
						"bag_allowance":baggage_allowance[(int(flight_info_base[1]["allowance"]["ref"])-1)] if 1 < len(flight_info_base) else "",
						"stops":len(leg_info[0])-1 if 1<len(leg_info) else "",
						"leg_info":leg_info[1] if 1<len(leg_info) else ""
					}

				}}
			all_flight_info.append(flight_info)
	trips = {"trips":(all_flight_info)}
	return trips


def get_baggage_allowance(baggage_desc):
	bag_allowance = []
	for bag in baggage_desc:
		bag_allowance.append(bag["pieceCount"])
	return bag_allowance

def find_legs(legs,groupedItineraryResponse,booking_code_array):
	flight_info = groupedItineraryResponse["scheduleDescs"]
	leg_info = groupedItineraryResponse["legDescs"]
	legs_info = []
	segment = 0
	for leg in legs:
		booking_code = booking_code_array[segment]["segment"]["bookingCode"]
		leg_lookup = leg_info[int((leg["ref"])-1)]
		flights_info = []
		for flight in leg_lookup["schedules"]:
			# print(flight)
			individual_flight_schedule_info = flight_info[int(flight["ref"]-1)]
			if "dateAdjustment" in individual_flight_schedule_info["arrival"]:
				date_adjustment = individual_flight_schedule_info["arrival"]["dateAdjustment"]
			else:
				date_adjustment = 0
			flights_info.append({
				"flight_number":individual_flight_schedule_info["carrier"]["marketingFlightNumber"],
				"departure_airport":individual_flight_schedule_info["departure"]["airport"],
				"arrival_airport":individual_flight_schedule_info["arrival"]["airport"],
				"departure_time":individual_flight_schedule_info["departure"]["time"],
				"flight_time":individual_flight_schedule_info["elapsedTime"],
				"landing_time":individual_flight_schedule_info["arrival"]["time"],
				"booking_code":booking_code,
				"date_adjustment": date_adjustment})
		legs_info.append(flights_info)
		segment = segment + 1
	return legs_info
	
def get_sabre_fare_level(fare_level):
	sabre_lookup = {
		"first" : "F",
		"premium_business": "J",
		"business": "C",
		"premium_economy": "S",
		"economy": "Y"
	}
	sabre_fare_level = "economy"
	if fare_level in list(sabre_lookup.keys()):
		sabre_fare_level = sabre_lookup[fare_level]
	# print(sabre_fare_level)
	return sabre_fare_level

def revalidate_flight(parsed_response,fare_level,from_airport, to_airport,outbound_date,return_date):
	cabin_pref = get_sabre_fare_level(fare_level)
	is_validated_flight = revalidate.revalidate_response(parsed_response,cabin_pref,from_airport, to_airport, outbound_date,return_date)
	return is_validated_flight


