from wox import Wox,WoxAPI
# -*- coding: utf-8 -*-
import urllib2,json,os.path

ha_ip = "127.0.0.1"
ha_port = "8123"
ha_password = "my_password"
url = 'http://' + ha_ip + ':' + ha_port + '/api/states?api_password=' + ha_password
icon_color = 'white'
domains = []
services = []

def post_data(url, postdata):
    # create the request object and set some headers
    req = urllib2.Request(url)
    req.add_header('Content-type','application/json')
    data = json.dumps(postdata)
    #print data
    # make the request and print the results
    if postdata:
        res = urllib2.urlopen(req,data)
    else:
        res = urllib2.urlopen(req)
    return json.load(res)

def removeNonAscii(s): return "".join(filter(lambda x: ord(x)<128, s))

def get_domains():
    global domains
    if not domains:
        data = post_data('http://' + ha_ip + ':' + ha_port + '/api/bootstrap' + '?api_password=' + ha_password,"")
        generator = ( item['domain'] for item in data['services'] )
        for d in generator:
            domains.append(str(d))
    else:
        pass
    return domains

def get_services():
    global services
    if not services:
        entities = get_entity("")
        services = []
        generator = ( item['entity_id'] for item in entities )
        for e in generator:
            if not get_type(str(e)) in services:
                services.append(get_type(str(e)))
    else:
        pass
    global domains
    domains = services
    return services

def get_entity(type=""):
    entities = []
    try:
        if type.endswith("s"):
            type = type.rstrip("s")
        states = post_data(url,"")
        #returns all states
        if type == "":
            entities = states
        #returns states filtered by service
        elif type in get_services():
            for i in range(0, len(states)):
                if states[i]["entity_id"].startswith(type + "."):
                    entities.append(states[i])
        else:
            #raise ValueError("Invalid service provided")
            entities = states
    except:
        entities = -1
    return entities

def get_attributes(service,num):
    attributes = []
    for i in range(len(service[num]["attributes"].keys())):
        key = list(service[num]["attributes"].keys())[i].replace("_"," ")
        value = service[num]["attributes"].values()[i]
        try:
            value = removeNonAscii(value)
        except:
            value = value
        if key != "friendly name" and key != "unit of measurement":
            attributes.append("{0}: {1}".format(key ,value).replace("\n", ""))
        joined_attributes = ', '.join(attributes)
        if joined_attributes == "":
            joined_attributes = "N/A"
    return joined_attributes.strip()

def get_type(entity_id):
    return str(entity_id.split(".")[0])

def get_icon(entity_id,state):
    try:
        ico = './icons/icons_' + icon_color + "/" + get_type(entity_id)
        if state == "on" or state == "off" or state == "paused" or state == "playing":
            ico += "_" + state + ".png"
        else:
            ico += ".png"
        if not os.path.isfile(ico):
            ico = './icons/home-assistant.png'
    except:
        ico = './icons/home-assistant.png'
    return ico

class homeassistant(Wox):
    #Active, toggle, trigger service
    def activate(self, service, title, query, arg):
        action = "toggle"
        if get_type(service) == "media_player":
            action = "media_play_pause"
        if query != title:
            action = None
            if arg in get_services():
                WoxAPI.change_query("ha " + arg + " " + title + " ",True)
            else:
                WoxAPI.change_query("ha " + title + " ",True)
        try:
            if action != None:
                post_data('http://' + ha_ip + ':' + ha_port + '/api/services/' + str(get_type(service)) + '/' + str(action) + '?api_password=' + ha_password,{ "entity_id": str(service) })
                #WoxAPI.start_loadingbar(self)
                #time.sleep(0.8)
                #WoxAPI.stop_loadingbar(self)
                #if query.endswith("trigger"):
                    #WoxAPI.change_query("dimming " + fn,True)
                #else:
                #WoxAPI.change_query("ha " + fn,True)
        except:
            pass

    def adjust_brightness(self, entity_id, percentage, delay=4):
        brightness = 255 * int(percentage) / 100
        post_data('http://' + ha_ip + ':' + ha_port + '/api/services/light/turn_on?api_password=' + ha_password,{ "entity_id": entity_id, "brightness": brightness, "transition": delay })

    def context_menu(self, data):
        results = []
        results.append({
            "Title": "test",
            "SubTitle": "test",
            #"IcoPath":ico,
            "JsonRPCAction": {
                #change query to show only service type
                "method": "Wox.ChangeQuery",
                "parameters": ["ha" + " " + keywords, False],
                # hide the query wox or not
                "dontHideAfterAction": True
            }
        })
        return results

    def query(self, query):
        results = []
        argument = ""
        argument = query.split()
        #---handle connection errors
        if len(argument) >= 1:
            for keywords in get_services():
                title = keywords
                subtext = keywords
                ico = './icons/icons_' + icon_color + "/filter.png"
                if query.strip().lower() in keywords.lower():
                    #---add filters to results
                    if argument[0] not in get_services():
                        results.append({
                            "Title": "Filter by: [" + keywords + "]",
                            "SubTitle": "show " + keywords + " services only",
                            "IcoPath":ico,
                            "JsonRPCAction": {
                                "method": "Wox.ChangeQuery",
                                "parameters": ["ha" + " " + keywords, True],
                                "dontHideAfterAction": True
                            }
                        })
            service = get_entity(argument[0])
            if service == -1:
                WoxAPI.change_query("ha connection error",True)
            for x in range(0, len(service)):
                entity_id = service[x]["entity_id"]
                try:
                    title = service[x]["attributes"]["friendly_name"]
                except:
                    title = entity_id
                state = service[x]["state"]
                try:
                    unit_of_measurement = service[x]["attributes"]["unit_of_measurement"]
                    state += unit_of_measurement
                except:
                    pass
                ico = get_icon(entity_id,state)
                subtext = get_attributes(service,x)
                #----Check if user is refrencing a service keyword and filters it out of query
                if argument[0].rstrip("s") in get_services():
                    if query.replace(argument[0],"",1).strip().lower() in title.lower():
                        results.append({
                            "Title": title + " is " + '\"' + state + '\"',
                            "SubTitle": subtext,
                            "IcoPath":ico,
                            "JsonRPCAction":{
                              "method": "activate",
                              "parameters":[entity_id,title,query,argument[0]],
                              "dontHideAfterAction":True,
                            }
                        })
                else:
                    #----check if query matches any results
                    if query.lower().strip() in title.lower():
                        results.append({
                            "Title": title + " is " + '\"' + state + '\"',
                            "SubTitle": subtext,
                            "IcoPath":ico,
                            "JsonRPCAction":{
                              "method": "activate",
                              "parameters":[entity_id,title,query,argument[0]],
                              "dontHideAfterAction":True
                            }
                        })
                #----Check to see if only one match and if exact match of title (No false positives when using filters)
                if query.lower().strip().startswith(title.lower()) or query.lower().replace(argument[0],"",1).strip().startswith(title.lower()):
                    results = []
                    #----Add entry for every attribute
                    if not query.lower().replace(title.lower(),"",1).strip().startswith("info".lower()):
                        if get_type(entity_id) == "light":
                            ico = get_icon(entity_id, state)
                            percentage = query.lower().replace(title.lower(),"",1).strip()
                            results.append({
                                "Title": "Adjust Brightness",
                                "SubTitle": "Adjust brightness level to " + query.replace(title.lower(),"",1).lower().strip() + "%",
                                "IcoPath":ico,
                                "JsonRPCAction":{
                                  "method": "adjust_brightness",
                                  "parameters":[entity_id,percentage],
                                  "dontHideAfterAction":True
                                }
                            })
                            results.append({
                                "Title": "Toggle",
                                "SubTitle": "Toggle " + title,
                                "IcoPath":ico,
                                "JsonRPCAction":{
                                  "method": "activate",
                                  "parameters":[entity_id,title,query,argument[0]],
                                  "dontHideAfterAction":True
                                }
                            })
                        else:
                            results.append({
                                "Title": "Action",
                                "SubTitle": "Activate default action for " + get_type(entity_id),
                                "IcoPath":ico,
                                "JsonRPCAction":{
                                  "method": "activate",
                                  "parameters":[entity_id,title,query,argument[0]],
                                  "dontHideAfterAction":True
                                }
                            })
                        if subtext != "N/A":
                            ico = './icons/icons_' + icon_color + '/info.png'
                            results.append({
                                "Title": "Info",
                                "SubTitle": "Show detailed information",
                                "IcoPath":ico,
                                "JsonRPCAction": {
                                    "method": "Wox.ChangeQuery",
                                    "parameters": ["ha " + query + " info" , True],
                                    "dontHideAfterAction": True
                                }
                            })
                    if query.lower().replace(title.lower(),"",1).strip().startswith("info".lower()):
                        results = []
                        for g in range(len(service[x]["attributes"].keys())):
                            key = list(service[x]["attributes"].keys())[g].replace("_"," ")
                            value = service[x]["attributes"].values()[g]
                            try:
                                value = removeNonAscii(value)
                            except:
                                value = value
                            ico = './icons/icons_' + icon_color + '/info.png'
                            if key != "friendly name" and key != "unit of measurement":
                                if query.lower().replace(title.lower(),"",1).replace("info","",1).lower().strip().lower() in str(value).lower().strip().lower():
                                    results.append({
                                        "Title": value,
                                        "SubTitle": key,
                                        "IcoPath": ico,
                                        "JsonRPCAction": {
                                            "method": "Wox.ChangeQuery",
                                            "parameters": [str(key) + ": " + str(value), True],
                                            "dontHideAfterAction": True
                                        }
                                    })
        #----No user input except action word
        else:
            for keywords in get_services():
                title = keywords
                subtext = keywords
                ico = './icons/icons_' + icon_color + "/filter.png"
                results.append({
                    "Title": "Filter by: [" + keywords + "]",
                    "SubTitle": "show " + keywords + " services only",
                    "IcoPath":ico,
                    "JsonRPCAction": {
                        #change query to show only service type
                        "method": "Wox.ChangeQuery",
                        "parameters": ["ha" + " " + keywords, False],
                        # hide the query wox or not
                        "dontHideAfterAction": True
                    }
                })

        if len(results) == 0:
            if query in get_services():
                subtext = "No Entities for " + query
            else:
                subtext = "No matches for: " + query
            ico = './icons/icons_' + icon_color + '/info.png'
            results.append({
                "Title": "No results found",
                "SubTitle": subtext,
                "IcoPath":ico,
            })
        return results

if __name__ == "__main__":
    homeassistant()
