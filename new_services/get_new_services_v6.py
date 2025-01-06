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
  xpanse_app = swimlane.apps.get(name='CDC - Xpanse - New Services')
  
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
    new_services = response.json()['reply']['external_services']
    
    i = 0
    
    for service in reversed(new_services):
      
      if i > 4:
        print('Max 5 tickets already created')
        break
      
      tags = service['tags']
      first_observed = service['first_observed']
      service_id = service['service_id']
      
      remove_tags = filter_tags(tags)
      
      if not remove_tags:
      
        # Check if service was first_observed less than 48 hours ago
        less_than_48_hours = check_last_48_hours(first_observed)
      
        if less_than_48_hours:
          
          # Check if there is already a record for the service_id
          old_id = check_existing_records_for_service_id(service_id, xpanse_app)
        
          if not old_id:
          
            # Gets field_data for record creation
            field_data = get_filtered_data(service)
          
            # Creates a new record
            create_record(xpanse_app, field_data)
            i += 1
            print('***RECORD CREATED***')
          else:
            print('***NO RECORD CREATED - OLD ID ***')
        else:
          print('***NO RECORD CREATED > 48***')
      else:
        print('***NO RECORD CREATED - REMOVE TAG ***')
  else:
    print('***REQUEST RETURNED NONE***')
    

# Generates API_endpoint, Headers, and data for the API call
def advanced_authentication(api_host, api_key, api_secret):
  
  api_endpoint = f'https://{api_host}/public_api/v1/assets/get_external_services/'
  
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
    "search_to": 500,
    "filters": [
      {
      "field" : "service_name",
      "operator" : "not_contains",
      "value": "HTTP"  
      },
    ],
    "sort": {
      "keyword": "DESC",
      "field": "first_observed",
      }
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


# Returns current time
def get_current_time():
  return pendulum.now('America/Denver')


# Returns EPOCH time in milliseconds for Mountain time 48 hours ago
def get_48_hours_ago():
  return int(pendulum.now('America/Denver').subtract(hours=72).timestamp() * 1000)


# Converts Epoch time to Mountain Time:
def convert_to_moutain_time(time):
  return pendulum.from_timestamp(time / 1000, tz='UTC').in_timezone('America/Denver')


# Returns a True if and tags are int the filter_out list, else returns False
def filter_tags(tags):
    
    filter_out = ['BU:Charter Enterprise – Infrastructure', 'BU:Charter Enterprise – Unconfirmed']

    return True if any(tag in filter_out for tag in tags) else False


# Returns a True if  first_observed is less than 48 hours ago, else returns False
def check_last_48_hours(first_observed):
  
  day_ago = get_48_hours_ago()

  return first_observed > day_ago
  


# Checks existing records for xpanse service_id and return True if a record exists with that service_id, otherwise returns False
def check_existing_records_for_service_id(service_id, xpanse_app):
  
  # This records search returns a list with the record_id(s) if the service_id already exists in a record, otherwise it returns an empty list
  records = xpanse_app.records.search(
    ('Xpanse Service Id', EQ, service_id)
    )
  
  return True if records else False


# Returns a dictionary with the feild_data needed for record creation
def get_filtered_data(service):
  
  current_time = get_current_time()
  
    
  field_data = {
    'Record Created At': current_time
  }
    
  # Service Name
  try:
    service_name = service.get('service_name', None)
    field_data['Xpanse Service Name'] = service_name
  except Exception as e:
    print(f'DEBUG - Error: {e}')
    pass
  # Service ID
  try:
    service_id = service.get('service_id', None)
    field_data['Xpanse Service Id'] = service_id
  except Exception as e:
    print(f'DEBUG - Error: {e}')
    pass
  # Service Type
  try:
    service_type = service.get('service_type', None)
    field_data['Xpanse Service Type'] = service_type
  except Exception as e:
    print(f'DEBUG - Error: {e}')
    pass
  # First Observed
  try:
    first_observed = service.get('first_observed', None)
    field_data['Xpanse First Observed'] = convert_to_moutain_time(first_observed)
    field_data['Xpanse First Observed Epoch'] = first_observed
  except Exception as e:
    print(f'DEBUG - Error: {e}')
    pass
  # Last Observed
  try:
    last_observed = service.get('last_observed', None)
    field_data['Xpanse Last Observed'] = convert_to_moutain_time(last_observed)
    field_data['Xpanse Last Observed Epoch'] = last_observed
  except Exception as e:
    print(f'DEBUG - Error: {e}')
    pass
  # IPv4 Address
  try:
    ips = service.get('ip_address', [])
    if ips:
      ip = ips[0]
      field_data['Xpanse IPv4'] = ip
  except Exception as e:
    print(f'DEBUG - Error: {e}')
    pass
  # Port
  try:
    port = service.get('port', None)
    field_data['Xpanse Port'] = port
  except Exception as e:
    print(f'DEBUG - Error: {e}')
    pass
  # Protocol
  try:
    protocol = service.get('protocol', None)
    field_data['Xpanse Protocol'] = protocol
  except Exception as e:
    print(f'DEBUG - Error: {e}')
    pass
  # IPv6 Address
  try:
    ipv6s = service.get('ipv6_address', [])
    if ipv6s:
      ipv6 = ipv6s[0]
      field_data['Xpanse IPv6'] = ipv6
  except Exception as e:
    print(f'DEBUG - Error: {e}')
    pass
  # City
  try:
    locations = service.get('geolocations', [])
    if locations:
      city = locations[0].get('city', None)
      field_data['Xpanse City'] = city
  except Exception as e:
    print(f'DEBUG - Error: {e}')
    pass
  # State
  try:
    locations = service.get('geolocations', [])
    if locations:
      state = locations[0].get('regionCode', None)
      field_data['Xpanse State'] = state
  except Exception as e:
    print(f'DEBUG - Error: {e}')
    pass
  # Country
  try:
    locations = service.get('geolocations', [])
    if locations:
      country = locations[0].get('countryCode', None)
      field_data['Xpanse Country'] = country
  except Exception as e:
    print(f'DEBUG - Error: {e}')
    pass
  # Bussiness Unit
  try:
    business_units = service.get('business_units', [])
    if business_units:
      bu = business_units[0][0].get('name', None)
      field_data['Xpanse Business Unit'] = bu
  except Exception as e:
    print(f'DEBUG - Error: {e}')
    pass
  # Vulnerabilty Score
  try:
    score = service.get('externally_inferred_vulnerability_score', None)
    field_data['Xpanse Vulnerability Score'] = score
  except Exception as e:
    print(f'DEBUG - Error: {e}')
    pass
  # CVEs
  try:
    cve_scores = service.get('externally_inferred_cves', [])
    if cve_scores:
      field_data['Xpanse CVEs'] = cve_scores
  except Exception as e:
    print(f'DEBUG - Error: {e}')
    pass
  # Tags
  try:
    tags = service.get('tags', [])
    if tags:
      field_data['Xpanse Tags'] = tags
  except Exception as e:
    print(f'DEBUG - Tags Error: {e}')
    pass
           
  return field_data


# Creates Xpanse Record
def create_record(xpanse_app, field_data):
  
  new_record = xpanse_app.records.create(**field_data)
  
  
# Calls main function
if __name__ == '__main__':
  main()