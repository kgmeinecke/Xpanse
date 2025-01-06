from swimlane import Swimlane
import requests
import re


# Main Function
def main():
  # Swimlane App and Record Variables
  swimlane = Swimlane(sw_context.config['InternalSwimlaneUrl'], access_token=sw_context.inputs['swimlane_api_pat'], verify_ssl=False)
  xpanse_app = swimlane.apps.get(name='CDC - Xpanse - New Services')
  xpanse_record = xpanse_app.records.get(id=sw_context.config['RecordId'])
  
  # IPV4, Port, Protocol Variables
  ipv4 = xpanse_record['Xpanse IPv4']
  ports = xpanse_record['Xpanse Port']
  protocol = xpanse_record['Xpanse Protocol']
  
  url_1 = ''
  url_2 = ''
  ip = ''
  
  # URL and regx pattern variables
  if ipv4 and ports and protocol == 'TCP':
    url = f'http://{url_1}?ip=={ipv4}&ports={ports}'
    pattern = r"PORT\s+STATE\s+\SERVICE\s+VERSION\s*(.*?)\n"
  
  elif ipv4 and ports and protocol == 'UDP':
    url = f'http://{url_2}?ip={ipv4}&ports={ports}'
    pattern = r"PORT\s+STATE\s+\SERVICE\s*(.*?)\n"
  
  # Proxie Variables
  proxies = {'http': f'http://{ip}'} 
  
  # Default variables
  final_nmap_results = None
  port_state = False
  
  # Calls the nmap_scan_request function with the url and proxies defined above
  if ipv4 and ports:
    nmap_results = nmap_scan_request(url, proxies)
    
  # Calls function to clean up NMAP results, then calls function to see if the port is 'closed' or 'filtered', then calls function to update the xpanse record with the NMAP results
    if nmap_results:
      final_nmap_results = nmap_results_clean_up(nmap_results)
      
      port_state = search_for_filtered_closed_ports(final_nmap_results, pattern)
      
      update_xpanse_record(xpanse_record, final_nmap_results, port_state)
    
    # Calls function to update xpanse record to set fields, 'Create SAIM' = True and 'Port Closed or Filtered' = False
    else:
      update_xpanse_record(xpanse_record, final_nmap_results, port_state)
      
  # Calls function to update xpanse record to set fields, 'Create SAIM' = True and 'Port Closed or Filtered' = False
  else:
    update_xpanse_record(xpanse_record, final_nmap_results, port_state)
    
    
# Function to perform and NMAP scan for the IP, and Port Defined above. Returns None if the request doesn't return a 200 status code
def nmap_scan_request(url, proxies, timeout=300):
  try:
    response = requests.post(url, proxies=proxies, timeout=timeout)
    
    if response.status_code ==  200:
      return response
    else:
      print(f'Request failed - {response.status_code} - {response.headers}')
  
  except requests.exceptions.Timeout:
    print(f'Request timed out after {timeout} seconds')    
  except requests.exceptions.RequestException as e:
    print(f'Error: {e}')
    
  return None


# Removes the first line from the NMAP results
def nmap_results_clean_up(nmap_results):
  return '\n'.join(nmap_results.text.split('\n')[1:])


# Searches through NMAP results and returns True for a state equal to 'filtered' or 'closed', else returns False
def search_for_filtered_closed_ports(final_nmap_results, pattern):
  
  port_info_match = re.search(pattern, final_nmap_results)
  
  if port_info_match:
    port_info = port_info_match.group(1).strip()
    port_data = port_info.split()
    state = port_data[1]
    
    if state in ['closed', 'filtered']:
      return True  
  
  return False
  

# Updates Xpanse Record with NMAP results
def update_xpanse_record(xpanse_record, final_nmap_results, port_state):
  xpanse_record['Xpanse Initial NMAP Results'] = final_nmap_results
  xpanse_record['Port Closed or Filtered'] = port_state
  xpanse_record['Create SAIM'] = True
  xpanse_record.patch()


# Call the main function
if __name__ == '__main__':
  main()