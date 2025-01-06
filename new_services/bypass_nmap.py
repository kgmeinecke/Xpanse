from swimlane import Swimlane


# Main Function
def main():
  swimlane = Swimlane(sw_context.config['InternalSwimlaneUrl'], access_token=sw_context.inputs['swimlane_api_pat'], verify_ssl=False)
  xpanse_app = swimlane.apps.get(name='CDC - Xpanse - New Services')
  xpanse_record = xpanse_app.records.get(id=sw_context.config['RecordId'])

  update_xpanse_record(xpanse_record)
  
  
# Updates Xpanse Record 
def update_xpanse_record(xpanse_record):
  xpanse_record['Xpanse Initial NMAP Results'] = 'No NMAP Scan was run'
  xpanse_record['Port Closed or Filtered'] = 'Unknown'
  xpanse_record['SAIM Automated'] = False
  xpanse_record['Create SAIM'] = True
  xpanse_record.patch()

  
# Call the main function
if __name__ == '__main__':
  main()