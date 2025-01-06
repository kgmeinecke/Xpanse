from swimlane import Swimlane
import pendulum
from swimlane.core.resources.usergroup import UserGroup


def main():
  
  # Swimlane App and Record Variables
  swimlane = Swimlane(sw_context.config['InternalSwimlaneUrl'], access_token=sw_context.inputs['swimlane_api_pat'], verify_ssl=False)
  
  xpanse_app = swimlane.apps.get(name='CDC - Xpanse - New Alerts')
  xpanse_record = xpanse_app.records.get(id=sw_context.config['RecordId'])
  
  alert_management_app = swimlane.apps.get(name="Alert & Incident Management")
  
  communications_app = swimlane.apps.get(name='Communications Tracker')
  sct_record = communications_app.records.get(id=xpanse_record['Communications Record Id'])
  
  # Create SAIM Data
  saim_data = create_saim_data(xpanse_record, sct_record)
  
  # Create SAIM Record
  saim_record = create_saim_record(alert_management_app, saim_data)
  print('***Record Created***')
  
  # Update Xpanse Record
  update_xpanse_record(xpanse_record, saim_record)
  
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
def create_saim_data(xpanse_record, sct_record):
  
  xpanse_url = sw_context.inputs['xpanse_url']
  title = xpanse_record['Xpanse Alert Name']
  now = get_current_time()
  min_ago = update_time(now)
  
  saim_data = {
    
    # Xpanse Fields
    'Xpanse Alert Name': xpanse_record['Xpanse Alert Name'],
    'Xpanse Alert Id': xpanse_record['Xpanse Alert Id'],
    'Xpanse Alert Business Unit': xpanse_record['Xpanse Alert Business Unit'],
    'Xpanse Alert Type': xpanse_record['Xpanse Alert Type'],
    'Xpanse Alert Severity': xpanse_record['Xpanse Alert Severity'],
    'Xpanse Alert Last Observed': xpanse_record['Xpanse Alert Last Observed'],
    'Xpanse Alert IPv4': xpanse_record['Xpanse Alert IPv4'],
    'Xpanse Alert Port': xpanse_record['Xpanse Alert Port'],
    'Xpanse Alert Protocol': xpanse_record['Xpanse Alert Protocol'],
    'Xpanse Alert IPv6': xpanse_record['Xpanse Alert IPv6'],
    'Xpanse Alert Tags': list(xpanse_record['Xpanse Alert Tags']),
    'Xpanse Alert Description': xpanse_record['Xpanse Alert Description'],
    'Xpanse Alert Remediation': xpanse_record['Xpanse Alert Remediation'],
    'Xpanse MITRE Tactics': list(xpanse_record['Xpanse MITRE Tactics']),
    'Xpanse MITRE Techniques': list(xpanse_record['Xpanse MITRE Techniques']),
    
    # SAIM Fields
    'Case Status': 'New',
    'Case Classification / Resolution': 'Unknown',
    'Case Current Owner': None,
    'Case Title': f'Xpanse: {title}',
    'Detailed Summary': f'<a href="{xpanse_url}" target="_blank">Xpanse - Dashboard</a>',
    'Case Severity': 'High',
    'Case Category': 'Improper Use/Policy Violation',
    'Case Source / Type': 'Xpanse - New Alert',
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
def update_xpanse_record(xpanse_record, saim_record):
  
  xpanse_record['SAIM Case Created On'] = get_current_time()
  xpanse_record['SAIM Tracking Id'] = saim_record.tracking_id
  xpanse_record['SAIM Reference'].add(saim_record)
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