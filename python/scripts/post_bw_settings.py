import urllib.request, json
url='http://127.0.0.1:5000/api/bandwidth-settings'
data=json.dumps({"budget_bytes_per_minute":50000000,"warning_threshold":0.75,"critical_threshold":0.9,"abort_on_critical":True,"log_decisions":True,"window_seconds":60}).encode('utf-8')
req=urllib.request.Request(url,data=data,headers={'Content-Type':'application/json'})
with urllib.request.urlopen(req) as res:
    print(res.status)
    print(res.read().decode())
