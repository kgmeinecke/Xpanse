from swimlane import Swimlane
import pendulum
from swimlane.core.resources.usergroup import UserGroup


def main():
  
  # Swimlane App and Record Variables
  swimlane = Swimlane(sw_context.config['InternalSwimlaneUrl'], access_token=sw_context.inputs['swimlane_api_pat'], verify_ssl=False)
  
  xpanse_app = swimlane.apps.get(name='CDC - Xpanse - New Services')
  xpanse_record = xpanse_app.records.get(id=sw_context.config['RecordId'])
  
  alert_management_app = swimlane.apps.get(name="Alert & Incident Management")
  
  communications_app = swimlane.apps.get(name='Communications Tracker')
  sct_record = communications_app.records.get(id=xpanse_record['Communications Record Id'])
  
  current_user = swimlane.user
  url = 'This needs to be updated'
  
  # Sets vairable for SAIM Automated field.  Needed this to work with both the NMAP and Bypass NMAP integrations.
  auto = xpanse_record['Port Closed or Filtered']
  
  if auto == 'Unknown':
    saim_auto = False
  else:
    saim_auto = auto
  
  # Create SAIM Data
  saim_data = create_saim_data(xpanse_record, sct_record, current_user, url)
  
  # Create SAIM Record
  saim_record = create_saim_record(alert_management_app, saim_data)
  print('***Record Created***')
  
  # Update Xpanse Record
  update_xpanse_record(xpanse_record, saim_record, saim_auto)
  
  # Update SCT Record
  update_sct_record(sct_record, saim_record)
  
  # Update SAIM Record
  update_saim_record(saim_record, sct_record)
  

# Returns current time
def get_current_time():
  return pendulum.now('America/Denver')


# Returns current time minus 1 minute
def update_time(time):
  
  return time.subtract(minutes=1)


# Creates a dictionary of data to write to the SAIM record
def create_saim_data(xpanse_record, sct_record, current_user, url):
  
  xpanse_url = sw_context.inputs['xpanse_url']
  xpanse_id_url = f"https://{url}/assets/external-services?serviceId={xpanse_record['Xpanse Service Id']}&action:openAssetDetails=true"
  title = xpanse_record['Xpanse Service Name']
  now = get_current_time()
  min_ago = update_time(now)
  
  # This is to set the IPv4 address and Port in the NMAP section of SAIM case
  if xpanse_record['Xpanse IPv4']:
    ip_address = xpanse_record['Xpanse IPv4']
  else:
    ip_address = ''
  
  # This is to set the case status, resolution, and owner depending on if the SAIM ticket gets auto closed or not. If the 'Port Closed or Filtered' field is True in the Xpanse Record, the case is auto closed.
  if xpanse_record['Port Closed or Filtered'] == 'True':
    case_status = 'Closed'
    resolution = 'Resolved'
    case_owner = current_user
  
  else:
    case_status = 'New'
    resolution = 'Unknown'
    case_owner = None
  
  saim_data = {
    
    # Xpanse Fields
    'Xpanse Service Name': xpanse_record['Xpanse Service Name'],
    'Xpanse Service Id': xpanse_record['Xpanse Service Id'],
    'Xpanse Business Unit': xpanse_record['Xpanse Business Unit'],
    'Xpanse Service Type': xpanse_record['Xpanse Service Type'],
    'Xpanse IPv4': xpanse_record['Xpanse IPv4'],
    'Xpanse Port': xpanse_record['Xpanse Port'],
    'Xpanse Protocol': xpanse_record['Xpanse Protocol'],
    'Xpanse City': xpanse_record['Xpanse City'],
    'Xpanse State': xpanse_record['Xpanse State'],
    'Xpanse Country': xpanse_record['Xpanse Country'],
    'Xpanse IPv6': xpanse_record['Xpanse IPv6'],
    'Xpanse First Observed': xpanse_record['Xpanse First Observed'],
    'Xpanse Last Observed': xpanse_record['Xpanse Last Observed'],
    'Xpanse Vulnerability Score': xpanse_record['Xpanse Vulnerability Score'],
    'Xpanse Initial NMAP Results': xpanse_record['Xpanse Initial NMAP Results'],
    'Xpanse CVEs': list(xpanse_record['Xpanse CVEs']),
    'Xpanse Tags': list(xpanse_record['Xpanse Tags']),
    # SAIM Nmap Fields
    'Nmap Results': xpanse_record['Xpanse Initial NMAP Results'],
    'Nmap HTML': xpanse_record['Xpanse Initial NMAP Results'].replace("\n","<br>"),
    'Ports': xpanse_record['Xpanse Port'],
    'IP Address': ip_address,
    # SAIM Fields
    'Case Status': case_status,
    'Case Classification / Resolution': resolution,
    'Case Current Owner': case_owner,
    'Case Title': f'Xpanse: {title}',
    'Detailed Summary': f'<a href="{xpanse_url}" target="_blank">Xpanse - Dashboard</a><br><a href="{xpanse_id_url}" target="_blank">Xpanse - Service ID Search</a>',
    'Case Severity': 'Low',
    'Case Category': 'Improper Use/Policy Violation',
    'Case Source / Type': 'Xpanse - New Service',
    'SCT-ID': sct_record,
    'Source Record Id': sw_context.config['RecordId'],
    'Source Application Id': sw_context.config['ApplicationId'],
    # Fields needed for Metrics
    'Event Occurred On': min_ago,
    'Alert Received On': now,
  }

  return saim_data


# Creates Alert & Incident Management Record
def create_saim_record(alert_management_app, saim_data):
  
  saim_record = alert_management_app.records.create(**saim_data)
  
  return saim_record


# Updates Xpanse Record with time the SAIM Case is created
def update_xpanse_record(xpanse_record, saim_record, saim_auto):
  
  xpanse_record['SAIM Case Created On'] = get_current_time()
  xpanse_record['SAIM Tracking Id'] = saim_record.tracking_id
  xpanse_record['SAIM Reference'].add(saim_record)
  
  # Updates 'SAIM Automated' field to be the same as the 'Port Closed or Filtered' field
  xpanse_record['SAIM Automated'] = saim_auto
  xpanse_record.patch()

  
# Updates the Communications Record with the SAIM ID  
def update_sct_record(sct_record, saim_record):
  
  sct_record['Incident Tracking Id'] = saim_record
  sct_record.patch()
  

# Updates the SAIM Reference Sections with the Communications Tracker Record
def update_saim_record(saim_record, sct_record):
  
  saim_record['Communications Tracker'].add(sct_record)
  saim_record.patch()
  
                            
# Calls main function
if __name__ == '__main__':
  main()