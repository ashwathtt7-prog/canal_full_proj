import requests

# Login as customer
r = requests.post('http://localhost:8001/api/auth/login', json={'email':'customer1@oceanline.com','password':'customer123'})
token = r.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

# Get auctions
auctions = requests.get('http://localhost:8001/api/auctions/', headers=headers).json()
print('Auctions:')
for a in auctions:
    print(f"  ID={a['id'][:8]}.. status={a['status']} category={a['category']}")

# Get vessels  
vessels = requests.get('http://localhost:8001/api/reservations/vessels', headers=headers).json()
print('Customer vessels:')
for v in vessels:
    print(f"  ID={v['id'][:8]}.. name={v['name']} category={v['category']}")

if auctions:
    a = auctions[0]
    print(f"\nAuction category: {a['category']}")
    matching = [v for v in vessels if v['category'] == a['category']]
    print(f"Matching vessels: {len(matching)}")
    
    if matching:
        bid_data = {'vessel_id': matching[0]['id'], 'amount': 150000, 'alternate_date': None, 'notes': None}
        print(f"Sending bid: {bid_data}")
        bid = requests.post(f"http://localhost:8001/api/auctions/{a['id']}/bid", 
            json=bid_data, headers=headers)
        print(f"Bid response: {bid.status_code} {bid.text}")
    else:
        print("No matching vessels!")
        # Try with any neopanamax vessel
        all_vessels = requests.get('http://localhost:8001/api/reservations/vessels', headers=headers).json()
        print("All vessel categories:", set(v['category'] for v in all_vessels))
