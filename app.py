from flask import Flask, request, jsonify
import searoute as sr
import math
import json
import os

app = Flask(__name__)

# Load ECA zones
ECA_POLYS = None

def load_eca():
    global ECA_POLYS
    if ECA_POLYS is None:
        with open('eca_polys.json') as f:
            ECA_POLYS = json.load(f)
    return ECA_POLYS

def pip(lng, lat, polygon):
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside

def is_eca(lng, lat):
    polys = load_eca()
    return any(pip(lng, lat, poly) for poly in polys)

def haversine_nm(lon1, lat1, lon2, lat2):
    R = 3440.065
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# Waypoints for fixing routes
GIBRALTAR = [-5.35, 35.97]
BOSPHORUS = [29.05, 41.02]

def is_med(lon, lat):
    return lon > -5.5 and lat < 47 and lat > 29

def is_bs(lon, lat):
    return 27 < lon < 42 and 40 < lat < 47

def is_ne(lon, lat):
    return lat > 47 or (lon < 15 and lat > 45)

def is_atlantic_iberia(lon, lat):
    return -10 < lon < -3 and 36 < lat < 44

def get_waypoints(origin, dest):
    olon, olat = origin
    dlon, dlat = dest
    wpts = [origin]
    
    orig_bs = is_bs(olon, olat)
    dest_bs = is_bs(dlon, dlat)
    orig_med = is_med(olon, olat)
    dest_med = is_med(dlon, dlat)
    orig_ne = is_ne(olon, olat)
    dest_ne = is_ne(dlon, dlat)
    orig_atl = is_atlantic_iberia(olon, olat)
    dest_atl = is_atlantic_iberia(dlon, dlat)

    if orig_bs and not dest_bs:
        wpts.append(BOSPHORUS)
    if (orig_med or orig_bs) and dest_ne:
        wpts.append(GIBRALTAR)
    elif (dest_med or dest_bs) and orig_ne:
        wpts.append(GIBRALTAR)
    if orig_med and dest_atl:
        wpts.append(GIBRALTAR)
    elif orig_atl and dest_med:
        wpts.append(GIBRALTAR)
    if dest_bs and not orig_bs:
        wpts.append(BOSPHORUS)
    wpts.append(dest)
    
    seen = []
    for w in wpts:
        if w not in seen:
            seen.append(w)
    return seen

def calc_route(origin, dest):
    waypoints = get_waypoints(origin, dest)
    total_ne = total_eca = 0
    for i in range(len(waypoints)-1):
        try:
            route = sr.searoute(waypoints[i], waypoints[i+1], units='naut')
            coords = route['geometry']['coordinates']
            for j in range(len(coords)-1):
                lon1, lat1 = coords[j]
                lon2, lat2 = coords[j+1]
                seg = haversine_nm(lon1, lat1, lon2, lat2)
                if is_eca((lon1+lon2)/2, (lat1+lat2)/2):
                    total_eca += seg
                else:
                    total_ne += seg
        except Exception as e:
            pass
    return round(total_ne), round(total_eca)

# Port coordinates lookup
PORT_COORDS = {
    'rotterdam':[4.5,51.9],'amsterdam':[4.9,52.4],'antwerp':[4.4,51.2],
    'hamburg':[9.97,53.54],'bremen':[8.8,53.1],'gothenburg':[11.9,57.7],
    'oslo':[10.7,59.9],'stockholm':[18.1,59.3],'helsinki':[25.0,60.2],
    'tallinn':[24.8,59.4],'riga':[24.1,56.9],'gdansk':[18.7,54.4],
    'kiel':[10.1,54.3],'dunkirk':[2.4,51.0],'le havre':[0.1,49.5],
    'brest':[-4.5,48.4],'london':[0.1,51.5],'southampton':[-1.4,50.9],
    'huelva':[-7.0,37.3],'algeciras':[-5.5,36.1],'cadiz':[-6.3,36.5],
    'barcelona':[2.2,41.4],'marseille':[5.4,43.3],'genoa':[8.9,44.4],
    'livorno':[10.3,43.5],'piraeus':[23.6,37.9],'thessaloniki':[22.9,40.6],
    'istanbul':[28.9,41.0],'gemlik':[29.15,40.43],'derince':[29.8,40.7],
    'aliaga':[26.9,38.8],'izmir':[27.1,38.4],'mersin':[34.6,36.8],
    'iskenderun':[36.17,36.59],'novorossiysk':[37.8,44.72],
    'constanta':[28.65,44.18],'odessa':[30.7,46.5],'varna':[27.9,43.2],
    'batumi':[41.6,41.6],'alexandria':[29.9,31.2],'port said':[32.3,31.3],
    'leixoes':[-8.7,41.2],'lisbon':[-9.1,38.7],'sines':[-8.9,37.9],
    'bilbao':[-3.0,43.4],'santander':[-3.8,43.5],
    'dubai':[55.3,25.3],'fujairah':[56.4,25.1],'aden':[45.0,12.8],
    'jeddah':[39.2,21.5],'singapore':[103.8,1.3],'shanghai':[121.5,31.2],
    'busan':[129.0,35.1],'houston':[-95.3,29.7],'new york':[-74.0,40.7],
    'oran':[-0.62,35.69],'algiers':[3.05,36.74],'tunis':[10.2,36.8],
    'augusta':[15.2,37.2],'taranto':[17.2,40.5],'fos sur mer':[4.86,43.43],
    'agio theodoroi':[23.1,37.9],'gonfreville':[0.2,49.5],
    'yalova':[29.3,40.6],'ventspils':[21.6,57.4],'primorsk':[28.6,60.4],
}

def find_port(name):
    if not name:
        return None
    n = name.lower().strip()
    if n in PORT_COORDS:
        return PORT_COORDS[n]
    for k, v in PORT_COORDS.items():
        if n in k or k in n:
            return v
    return None

@app.route('/distance', methods=['POST', 'OPTIONS'])
def distance():
    if request.method == 'OPTIONS':
        resp = jsonify({})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        return resp, 200
    
    data = request.json
    port_prev = data.get('portPrev', '')
    port_load = data.get('portLoad', '')
    port_disch = data.get('portDisch', '')
    
    load_coords = find_port(port_load)
    disch_coords = find_port(port_disch)
    prev_coords = find_port(port_prev) if port_prev else None
    
    result = {
        'ballast_noneca': 0, 'ballast_eca': 0,
        'laden_noneca': 0, 'laden_eca': 0,
        'load_found': load_coords is not None,
        'disch_found': disch_coords is not None
    }
    
    if load_coords and disch_coords:
        ne, eca = calc_route(load_coords, disch_coords)
        result['laden_noneca'] = ne
        result['laden_eca'] = eca
    
    if prev_coords and load_coords:
        ne, eca = calc_route(prev_coords, load_coords)
        result['ballast_noneca'] = ne
        result['ballast_eca'] = eca
    
    resp = jsonify(result)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
