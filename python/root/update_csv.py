import csv

rows = []

with open('api_inventory.csv', 'r') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

for row in rows:
    if row['API Route'] == '/':
        row['Referenced Files'] = 'cockpit.html'
        row['Implementation Status'] = 'IMPLEMENTED'
        row['Key_Files_Status'] = 'cockpit.html:IMPLEMENTED'
    elif row['API Route'] == '/health':
        row['Implementation Status'] = 'IMPLEMENTED'
    elif row['API Route'] == '/neural':
        row['Referenced Files'] = 'neural.html'
        row['Implementation Status'] = 'IMPLEMENTED'
        row['Key_Files_Status'] = 'neural.html:IMPLEMENTED'
    elif row['API Route'] == '/neural2':
        row['Referenced Files'] = 'neural_v2.html'
        row['Implementation Status'] = 'IMPLEMENTED'
        row['Key_Files_Status'] = 'neural_v2.html:IMPLEMENTED'
    elif row['API Route'] == '/network':
        row['Referenced Files'] = 'network_cockpit.html'
        row['Implementation Status'] = 'IMPLEMENTED'
        row['Key_Files_Status'] = 'network_cockpit.html:IMPLEMENTED'
    elif row['API Route'] == '/api/status':
        row['Key_Files_Status'] = "{'current.json': 'IMPLEMENTED'}"
    # Add more as audited

with open('api_inventory.csv', 'w', newline='') as f:
    fieldnames = ['API Route', 'HTTP Method', 'Category', 'Operational', 'Status_Code', 'Response_Size', 'Referenced Files', 'Implementation Status', 'External_Modules', 'File_Operations', 'Config_Files', 'Database_Files', 'Key_Files_Status', 'Notes', 'Corresponding_Task', 'Implementation_Report', 'Consistency_Status']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

print('CSV updated')