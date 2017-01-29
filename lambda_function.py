import urllib2
import json
import math
import datetime
import random

#stores data for bus stops and building locations
numClosest = 5
stops = json.load(urllib2.build_opener().open("https://s3.amazonaws.com/umd-busses/stop_dict.txt"))
buildings = json.load(urllib2.urlopen("https://s3.amazonaws.com/umd-busses/buildings_stops.txt"))

def lambda_handler(event, context):

    if(event['session']['application']['applicationId'] !=
        "amzn1.ask.skill.825acea3-c627-42ce-99ae-a8eb7a9c8115"):
        raise ValueError("Invalid Application ID")
    if event['session']['new']:
    	on_session_started({"requestId":event["request"]["requestId"]}, event['session'])

    if event['request']['type'] == "LaunchRequest":
    	return on_launch(event["request"], event["session"])
    elif event['request']['type'] == "IntentRequest":
    	return on_intent(event["request"], event["session"])
    elif event["request"]["type"] == "SessionEndedRequest":
        return on_session_ended(event["request"], event["session"])

def on_session_started(session_started_request, session):
    print "Starting new session"


def on_launch(launch_request, session):
    return get_welcome_response()

def on_intent(intent_request, session):
    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    #handler for each intent (time to x stop, how to next building, etc)
    if intent_name == "NextBusIntent":
        return get_next_bus(intent)
    elif intent_name == "WhichBusIntent":
        return get_which_bus(intent)
    elif intent_name == "BusJokesIntent":
        return get_bus_jokes()
    elif intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()
    elif intent_name =="AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
		return handle_session_end_request()

def on_session_ended(session_ended_request, session):
    print "Session ended"

def handle_session_end_request():
	card_title = "Get to the Bus!"
	speech_output = "Good luck catching your bus!"
	end_session = True

	return build_response({}, build_speechlet_response(card_title, speech_output, None, end_session))

def get_welcome_response():
    card_title = "Terrapin Transit"
    speech_output = "Welcome to the Terrapin Transit skill."
    session_attributes = ""
    reprompt_text = "Ask me bout the buses"
    end_session = False

    return build_response(session_attributes, build_speechlet_response(card_title, speech_output, reprompt_text, end_session))

    #Helper Methods for Harry's Methods
    ###################################
def dist(lat1, lon1, lat2, lon2):
    r = 6378000
    angle1 = math.radians(lat1)
    angle2 = math.radians(lat2)
    latdiff = math.radians(lat2 - lat1)
    londiff = math.radians(lon2 - lon1)

    a = math.sin(latdiff / 2) * math.sin(latdiff / 2) + math.cos(angle1) * math.cos(angle2) * math.sin(londiff / 2) * math.sin(londiff / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = r * c

    return d


def closestStops(lat, lon, num):
    distances = []
    for stop in stops.keys():
        pair = (float(stops[stop]["lat"]), float(stops[stop]["lon"]))
        #Distance formula
        if lat != pair[0] and lon != pair[1]:
            distance = dist(lat, lon, pair[0], pair[1])
            if len(distances) < num:
                distances.append((distance, stop))
                distances.sort()
            else:
                if distance < distances[-1][0]:
                    distances[-1] = (distance, stop)
                    distances.sort()

    return distances

def sharedRoutes(start, dest):
    api = urllib2.build_opener()

    routelist = "109,114,115,117,125,127,128,131,132,133,701,702,703,104,105,108,110,111,113,116,118,122,124,126,129,130"

    #Look through all routes and find start and dest, store route ids that are shared
    routeids = []
    i = 0
    data = api.open("http://api.umd.io/v0/bus/routes/" + routelist)
    routedata = json.load(data)
    for route in routedata:
        if str(routedata[i]["directions"][0]["direction_id"]).lower() == "loop":
            stop = routedata[i]["directions"][0]["stops"]
            if (start in stop and dest in stop) and (stop.index(start) < stop.index(dest)):
                routeids.append(routedata[i]["route_id"])
        else:
            stop = routedata[i]["directions"][0]["stops"]
            if (start in stop and dest in stop) and (stop.index(start) < stop.index(dest)):
                routeids.append(routedata[i]["route_id"])
            stop = routedata[i]["directions"][1]["stops"]
            if (start in stop and dest in stop) and (stop.index(start) < stop.index(dest)):
                routeids.append(routedata[i]["route_id"])

        i+=1
    return routeids

    ###################


def get_next_bus(intent):
    card_title = "Next Bus"
    end_session = False
    session_attributes = ""
    speech_output = ""
    reprompt_text = ""

    try:
        stop_title = intent['slots']['BusStop']['value']
        route = intent['slots']['Route']['value']
    except:
        speech_output = "I'm sorry, I had understanding the route or stop you said."
        return build_response(session_attributes, build_speechlet_response(card_title, speech_output, reprompt_text, end_session))

    stop_name = validate_title(stop_title)

    try:
        route_endpoint = "http://api.umd.io/v0/bus/routes/" + str(route) + "/arrivals/" + str(stops[stop_name]["id"])
        route = json.load(urllib2.urlopen(route_endpoint))

        #find the times for the closest and second closest stops
        first = route["predictions"]["direction"]["prediction"][0]["minutes"]
        second = route["predictions"]["direction"]["prediction"][1]["minutes"]

        speech_output = "The first bus will arrive in " + first + " minutes, and the second bus will arrive in " + second + " minutes"
        reprompt_text = ""
    except KeyError:
        speech_output = "I couldn't find any times for you."
        reprompt_text = "Try again with another stop."

    return build_response(session_attributes, build_speechlet_response(card_title, speech_output, reprompt_text, end_session))

def get_which_bus(intent):
    card_title = "Which Bus"
    end_session = False
    speech_output = "I'm sorry, I couldn't find a route between these stops."
    reprompt_text = "Try to find a route again with another two stops."

    try:
        dest_title = intent['slots']['BusStop']['value']
        start_title = intent['slots']['StartStop']['value']

        dest = validate_title(dest_title)
        start = validate_title(start_title)

        destid = stops[dest]["id"]
        startid = stops[start]["id"]
    except KeyError:
        return build_response(session_attributes, build_speechlet_response(card_title, speech_output, reprompt_text, end_session))

    routeids = sharedRoutes(startid, destid)
    origstart = start
    #if start == "start" or is blank set it to start location

    api = urllib2.build_opener()

    #Loop through all shared routes and find fastest bus
    fastestDest = 1000
    timeDest = 0
    fastestStart = 1000
    minutesStart = 0
    busStart = ""
    route = ""
    distance = 0
    i = 0;
    r_id = 0
    while True:

        for route_id in routeids:
            if route_id != 0:
                data = api.open("http://api.umd.io/v0/bus/routes/"+route_id+"/arrivals/"+startid)
                predictdata = json.load(data)

                try:
                    for predict in predictdata["predictions"]["direction"]["prediction"]:
                        curr = predict["minutes"]
                        if int(curr) < int(fastestStart):
                            fastestStart = int(curr)
                            minutesStart = int(curr)
                            busStart = predict["vehicle"]
                            route = predictdata["predictions"]["routeTitle"]
                            r_id = route_id
                except KeyError:
                    continue
        if fastestStart == 1000:
            if i == numClosest:
                speech_output = "There aren't any routes to " + dest + " from " + origstart
                return build_response(session_attributes, build_speechlet_response(card_title, speech_output, reprompt_text, end_session))

            distances = closestStops(float(stops[start]["lat"]), float(stops[start]["lon"]), numClosest)
            start = distances[i][1]
            if (start == dest):
                distance = distances[i][0]
                i = -1
                break
            print start
            i+=1
            routeids = sharedRoutes(startid, destid)
        else:
            break

    if i != -1:
        data = api.open("http://api.umd.io/v0/bus/routes/"+str(r_id)+"/arrivals/"+destid)
        predictdata = json.load(data)

        try:
            for predict in predictdata["predictions"]["direction"]["prediction"]:
                if predict["vehicle"] == busStart:
                    curr = predict["minutes"]
                    if int(curr) < int(fastestDest):
                        fastestDest = curr
                        timeDest = predict["epochTime"]
        except KeyError:
            speech_output = "There aren't any routes to " + dest + " from " + origstart
            return build_response(session_attributes, build_speechlet_response(card_title, speech_output, reprompt_text, end_session))


        #Import datetime
        destTime = (datetime.datetime.fromtimestamp(float(timeDest)/1000) - datetime.timedelta(hours=5)).strftime("%H %M")
        time = destTime.split()
        hour = time[0]
        minute = time[1]
        day = ""
        if int(minute) < 10:
            minute = "0" + str(minute)
        if int(hour) == 0:
            hour = "12"
            day = " AM"
        elif int(hour) > 12:
            hour = str(int(hour) % 12)
            day = " PM"
        else:
            hour = hour
            day = " AM"

        destTime = str(hour) + " " + minute + day

        if i > 0:
            speech_output = "I couldn't find any routes with these stops. Instead, go to " + start + ", a " + str(route) + " bus will arrive in " + str(minutesStart) + " minutes, and you will arrive at " + dest + " at " + destTime
        else:
            speech_output = "A" + str(route) +" bus will arrive at " + start + " in " + str(minutesStart) + " minutes and you will arrive at " + dest + " at " + destTime

    else:
        speech_output = "There aren't any optimal routes to " + dest + " from " + origstart + ". You should probably just walk there, it's only " + str(round((distance * 0.000621371), 2)) + " miles away"

    return build_response(session_attributes, build_speechlet_response(card_title, speech_output, reprompt_text, end_session))

def get_bus_jokes():
    jokes = json.load(urllib2.urlopen("https://s3.amazonaws.com/umd-busses/jokes.txt"))
    key = random.choice(jokes.keys())
    speech_output = key+"                                                  "+jokes[key]
    card_title = "bus joke"
    session_attributes = ""
    reprompt_text = ""
    end_session = False
    return build_response(session_attributes, build_speechlet_response(card_title, speech_output, reprompt_text, end_session))

def build_speechlet_response(title, speech, reprompt, end_session):
	return {
		"outputSpeech": {
			"type": "PlainText",
			"text": speech
		},
		"card": {
			"type": "Simple",
			"title": title,
			"content": speech
		},
		"reprompt": {
			"outputSpeech": {
				"type": "PlainText",
				"text": reprompt
			}
		},
		"shouldEndSession": end_session
	}

def build_response(session_attributes, speechlet):
	return {
		"version": "1.0",
		"session_attributes": session_attributes,
		"response": speechlet
	}

def validate_title(stop_title):
    if (stop_title == "home"):
        return "preinkert drive at lot mv"
    if (stop_title.lower() in stops):
        return stop_title.lower()

    if (stop_title.lower() in buildings):
        return buildings[stop_title.lower()]

    for stop in stops:
        if stop_title.lower() in stop:
            return stop

    return "No stop found"
