from swimlane import Swimlane

def main():

  # Define communications tracker app and current app objects 
  swimlane = Swimlane(sw_context.config['InternalSwimlaneUrl'], access_token=sw_context.inputs['swimlane_api_pat'], verify_ssl=False)
  xpanse_app = swimlane.apps.get(id=sw_context.config['ApplicationId'])
  xpanse_record = xpanse_app.records.get(id=sw_context.config['RecordId'])
  communications_app = swimlane.apps.get(name="Communications Tracker")

  
  # Create SCT data
  sct_data = create_sct_data(xpanse_record)
  
  # Create SCT Record
  new_sct_record = create_sct_record(communications_app, sct_data)
  
  # Update SCT Record
  update_sct_record(new_sct_record)
  
  # Update Xpanse Record
  update_expanse_record(xpanse_record, new_sct_record)
  
  
# Creates a dictionary of data to write to the SCT record  
def create_sct_data(xpanse_record):  

  # Create variable for Subject
  expanse_service_id = xpanse_record['Xpanse Service Id']
  expanse_service_name = xpanse_record['Xpanse Service Name']

  sct_data = {
    'Subject': f'Xpanse - {expanse_service_id} - {expanse_service_name}'
  }

  return sct_data


# Created new Communications Record
def create_sct_record(communications_app, sct_data):
  new_sct_record = communications_app.records.create(**sct_data)
  
  return new_sct_record


# Update Communications Record
def update_sct_record(new_sct_record):
  new_sct_record['Communications Record Id'] = new_sct_record.id
  new_sct_record.patch()

  
# Update Xpanse Record
def update_expanse_record(xpanse_record, new_sct_record):

  xpanse_record['Record Id'] = xpanse_record
  xpanse_record['Communications Record Id'] = new_sct_record.id
  xpanse_record['Communications Tracking Id'] = new_sct_record.tracking_id
  xpanse_record['Communications Tracker'].add(new_sct_record)
  xpanse_record.patch()


if __name__ == '__main__':
  main()