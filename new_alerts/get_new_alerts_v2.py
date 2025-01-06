from datetime import datetime, timezone
from swimlane.core.search import EQ
from swimlane import Swimlane
import pendulum
import requests
import hashlib
import secrets
import string
import json


def main():
  
  #Swimlane vairables
  swimlane = Swimlane(sw_context.config['InternalSwimlaneUrl'], access_token=sw_context.inputs['swimlane_api_pat'], verify_ssl=False)
  xpanse_app = swimlane.apps.get(name='CDC - Xpanse - New Alerts')
  
  # Key Store vairables
  api_host = sw_context.inputs['xpanse_api_host']
  api_key = sw_context.inputs['xpanse_api_key']
  api_secret = sw_context.inputs['xpanse_api_secret']
  
  proxies = {'https': sw_context.inputs['swimlane_proxies']}
  
  # Sets up the api_endpoint, data, and headers for advanced authentication
  api_endpoint, headers, data = advanced_authentication(api_host, api_key, api_secret)
  
  # Makes api call to Xpanse
  response = make_request(api_endpoint, headers, data, proxies)
  
  if response:
    alerts = response.json()['reply']['alerts'] 
    
    sorted_alerts = sort_alerts(alerts)
    
    for alert in sorted_alerts:
      
      tags = alert['tags']
      alert_id = alert['alert_id']
      
      remove_tags = filter_tags(tags)
      
      if not remove_tags:
        old_alert = check_existing_records_for_alert_id(alert_id, xpanse_app)
      
        if not old_alert:
          field_data = get_field_data(alert)
          #print(field_data)
          create_record(xpanse_app, field_data)
          print(f'$$$ RECORD CREATED $$$')
        else:
          print('*** NO RECORD CREATED - OLD ID ***')
      else:
        print('%%% NO RECORD CREATED - REMOVE TAG %%%')
  else:
    print('### REQUEST RETURNED NONE ###')
    
        
# Generates API_endpoint, Headers, and data for the API call
def advanced_authentication(api_host, api_key, api_secret):
  
  api_endpoint = f'https://{api_host}/public_api/v2/alerts/get_alerts_multi_events/'
  
  headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
    }

  # Generate a 64 bytes random string
  nonce = "".join([secrets.choice(string.ascii_letters + string.digits) for _ in range(64)])
    
  # Get the current timestamp as milliseconds.
  timestamp = int(datetime.now(timezone.utc).timestamp()) * 1000
    
  # Generate the auth key:
  auth_key = "%s%s%s" % (api_secret, nonce, timestamp)
    
  # Convert to bytes object
  auth_key = auth_key.encode("utf-8")
    
  # Calculate sha256:
  api_key_hash = hashlib.sha256(auth_key).hexdigest()
    
  # Generate HTTP call headers
  headers["x-xdr-timestamp"] = str(timestamp)
  headers["x-xdr-nonce"] = nonce
  headers["x-xdr-auth-id"] = api_key
  headers["Authorization"] = api_key_hash

  # Filters data for Red Assets and excluedes "HTTP" and sorts by first_observed
  data = {
    "request_data": {
      "search_from": 0,
      "search_to": 100,
      "filters": [
        {
        "field" : "status",
        "operator" : "in",
        "value": ["new", "under_investigation", "reopened"]
        },
        {
        "field" : "severity",
        "operator" : "in",
        "value": ["high"]  
        },
        {
        "field": "attack_surface_rule_id",
        "operator" : "in",
        "value": ["RedisServer", "RDPServer"]  
        #"value": ["MemcachedServer", "RedisServer", "RDPServer"]   
        }
      ],
    }
  }

  return (api_endpoint, headers, data)


# Makes API call to Xpanse
def make_request(api_endpoint, headers, data, proxies):
    
  try:
    response = requests.post(url=api_endpoint, headers=headers, json=data, proxies=proxies)
    
    if response.status_code == 200:
      return response
    else:
      print(f'Request failed')
  except requests.exceptions.RequestException as e:
    print(f'Error: {e}')
    
  return None


# Sorts the alert_list by the value of 'last_observed' in DESC order so the results order will match the Xpanse Dashboard
def sort_alerts(alerts):
    return sorted(alerts, key=lambda x: x['last_observed'], reverse=True)


# Returns current time
def get_current_time():
  return pendulum.now('America/Denver')


# Returns EPOCH time in milliseconds for Mountain time n_hours hours ago and rounds the time to 00:00:00.  EX: if 24 hours ago is Apr 21st 2024 10:11:00, it will round to Apr 21st 2024 00:00:00
def get_n_hours_ago(n_hours):
  return int(pendulum.now('America/Denver').subtract(hours=n_hours).start_of('day').timestamp() * 1000)


# Convert Epoch time to Mountain Time:
def convert_to_moutain_time(time):
    return pendulum.from_timestamp(time / 1000, tz='UTC').in_timezone('America/Denver')
  

# Returns a True if and tags are in the filter_out list, else returns False
def filter_tags(tags):
    
    filter_out = ['BU:Charter Enterprise – Infrastructure', 'BU:Charter Enterprise – Unconfirmed']

    return True if any(tag in filter_out for tag in tags) else False

  
# Checks existing records for xpanse alert_id and return True if a record exists with that service_id, otherwise returns False
def check_existing_records_for_alert_id(alert_id, xpanse_app):
  
  # This records search returns a list with the record_id(s) if the service_id already exists in a record, otherwise it returns an empty list
  records = xpanse_app.records.search(
    ('Xpanse Alert Id', EQ, alert_id)
    )
  
  return True if records else False


def get_field_data(alert):
  
  current_time = get_current_time()
    
  field_data = {
    'Record Created At': current_time,
  }
    
  # Alert Name
  try:
    field_data['Xpanse Alert Name'] = alert.get('name', None)
  except Exception as e:
    print(f'DEBUG - Alert Name Error: {e}')
    pass
  # Alert Id
  try:
    field_data['Xpanse Alert Id'] = alert.get('alert_id', None)
  except Exception as e:
    print(f'DEBUG - Alert ID Error: {e}')
    pass
  # Business Unit
  try:
    business_units = alert.get('business_unit_hierarchies', [])
    if business_units:
      field_data['Xpanse Alert Business Unit'] = business_units[0][0].get('name', None)
  except Exception as e:
    print(f'DEBUG - Business Unit Error: {e}')
    pass
  # Alert Type
  try:
    field_data['Xpanse Alert Type'] = alert.get('attack_surface_rule_name', None)
  except Exception as e:
    print(f'DEBUG - Alert Type Error: {e}')
    pass
  # IPv4 Address
  try:
    ips = alert.get('ipv4_addresses', None)
    if ips:
      field_data['Xpanse Alert IPv4'] = ips[0]
  except Exception as e:
    print(f'DEBUG - IPv4 Error: {e}')
    pass
  # Port Number
  try:
    field_data['Xpanse Alert Port'] = alert.get('port_number', None)
  except Exception as e:
    print(f'DEBUG - Port Error: {e}')
    pass
  # Protocol
  try:
    field_data['Xpanse Alert Protocol'] = alert.get('port_protocol', None)
  except Exception as e:
    print(f'DEBUG - Protocol Error: {e}')
    pass
  # IPv6 Address
  try:
    field_data['Xpanse Alert IPv6'] = alert.get('ipv6_addresses', None)
  except Exception as e:
    print(f'DEBUG - IPv6 Error: {e}')
    pass
  # Last Observed
  try:
    last_observed = alert.get('last_observed', None)
    field_data['Xpanse Alert Last Observed'] = convert_to_moutain_time(last_observed)
    field_data['Xpanse Alert First Observed Epoch'] = last_observed
  except Exception as e:
    print(f'DEBUG - Last Observed Error: {e}')
    pass
  # Severity
  try:
    field_data['Xpanse Alert Severity'] = alert.get('severity', None)
  except Exception as e:
    print(f'DEBUG - Severity Error: {e}')
    pass 
  # Description
  try:
    field_data['Xpanse Alert Description'] = alert.get('description', None)
  except Exception as e:
    print(f'DEBUG - Description Error: {e}')
    pass
  # Tags
  try:
    alert_tags = alert.get('tags', [])
    if alert_tags:
      field_data['Xpanse Alert Tags'] = alert_tags
  except Exception as e:
    print(f'DEBUG - Alert Tags Error: {e}')
    pass
  # Remediation
  try:
    field_data['Xpanse Alert Remediation'] = alert.get('remediation_guidance', None)
  except Exception as e:
    print(f'DEBUG - Remediation Error: {e}')
    pass
  # MITRE Tactics
  try:
    mitre_tactics = alert.get('mitre_tactic_id_and_name', [])
    if mitre_tactics:
      field_data['Xpanse MITRE Tactics'] = mitre_tactics
  except Exception as e:
    print(f'DEBUG - MITRE Tactics Error: {e}')
    pass
  # MITRE Techniques
  try:
    mitre_techniques = alert.get('mitre_technique_id_and_name', [])
    if mitre_techniques:
      field_data['Xpanse MITRE Techniques'] = mitre_techniques
  except Exception as e:
    print(f'DEBUG - MITRE Tactics Error: {e}')
    pass
           
  return field_data


# Creates Xpanse Record
def create_record(xpanse_app, field_data):
  
  new_record = xpanse_app.records.create(**field_data)


# Calls main function
if __name__ == '__main__':
  main()