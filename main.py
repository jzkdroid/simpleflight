from flask import Flask
from get_flights_parser import get_flights
from flask import jsonify
from flask import request

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

@app.route("/get_flights")
def get_flight_data():
	raw_data = request.json
	data = raw_data["trip"]
	from_airport = data.get('from_airport')
	to_airport = data.get('to_airport')
	outbound_date = data.get('outbound_date')
	return_date = data.get('return_date')
	fare_level = data.get('fare_level', "null")
	validate_flights = data.get('validate_flights', False)
	direct_flights_only = data.get('direct_flights_only', False)
	validate_flights
	x = get_flights(from_airport,to_airport, outbound_date,return_date,fare_level,validate_flights,direct_flights_only)
	return jsonify(x)



	