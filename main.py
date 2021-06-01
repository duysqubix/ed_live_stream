import logging
import math
import time
import numpy as np
from enum import IntEnum

import requests
from colorama import Fore

logging.basicConfig(level=logging.INFO)

REFRESH_TIME = 10
SYSTEM_CHUNK = 200
HOME_WORLD = "Khun"


class Rarity(IntEnum):
    very_common = 0
    common = 1
    uncommon = 2
    rare = 3
    very_rare = 4
    
    def colorize(self, msg):
        
        if self == Rarity.uncommon:
            return Fore.BLUE + msg + Fore.RESET
        
        if self == Rarity.rare:
            return Fore.RED + msg + Fore.RESET
        
        if self == Rarity.very_rare:
            return Fore.YELLOW + msg + Fore.RESET
        return msg
    
RARITY = {
    "O (Blue-White) Star" : [Rarity.very_common, Rarity.very_rare],
    "B (Blue-White) Star" : [Rarity.very_common, Rarity.rare],
    "B (Blue-White super giant) Star" : [Rarity.very_rare, Rarity.very_rare],
    "A (Blue-White) Star": [Rarity.very_common, Rarity.uncommon],
    
}

def chunk(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]

class GalaticPosition:
    @classmethod
    def FromDict(cls, d):
        return cls(d['x'], d['y'], d['z'])

    def __init__(self, x, y, z):
        self.coords = np.array((x,y,z))
    
    @property
    def x(self):
        return self.coords[0]
    
    @property
    def y(self):
        return self.coords[1]
    
    @property
    def z(self):
        return self.coords[2]
    
    def update(self, data: dict):
        self.coords[0] = data['x']
        self.coords[1] = data['y']
        self.coords[2] = data['z']

    def distance(self, pos,r=None):
        if pos != self:
            dist = np.linalg.norm(pos.coords-self.coords)
            return dist if not r else round(dist, r)
        
        return 0
        
    def __repr__(self):
        return str(self.coords)
    
    def __eq__(self, pos):
        return all(pos.coords == self.coords)


class HomeWorld(GalaticPosition):
    def __init__(self, name):
        self.name = name
        resp = requests.get("https://www.edsm.net/api-v1/systems", params={"systemName": name, "showCoordinates": 1})
        coords = resp.json()[0]['coords']
        
        super().__init__(coords['x'], coords['y'], coords['z'])
    
    def __repr__(self):
        return str(self.name.capitalize())
        

class Commander:
    def __init__(self, cmd_name, api_key):
        self.cmd_name = cmd_name
        self.api_key = api_key
        self.position = GalaticPosition(0, 0, 0)
        self.home = HomeWorld(HOME_WORLD)
        self.cur_system = None
        self.timestamp = None
        self.total_distance = None
        self.bare_packet = {"commanderName": cmd_name, "apiKey": api_key}

    def calc_total_distance_traveled(self):
        url = "https://www.edsm.net/api-logs-v1/get-logs"
        resp = requests.get(url, params=commander.bare_packet)

        systems = [x['system'] for x in resp.json()['logs']]

        if not systems:
            raise Exception("No systems visted.. Travel some commander")

        # reverse system list to begin with first system
        systems.reverse()

        tot_distance = 0.00
        for chunk_system in chunk(systems, SYSTEM_CHUNK):
            data = {"systemName[]": chunk_system, "showCoordinates": 1}
            resp = requests.get("https://www.edsm.net/api-v1/systems", params=data)
            coords = list()

            sortd_systems = {x['name']: np.array((x['coords']['x'], x['coords']['y'], x['coords']['z'])) for x in resp.json()}

            for sys in chunk_system:
                coords.append(sortd_systems[sys])

            for i in range(1,len(coords)):
                p1 = coords[i]
                p2 = coords[i-1]
                tdist = np.linalg.norm(p2-p1)
                tot_distance += tdist
                
        self.total_distance = tot_distance

    def get_last_position(self):
        url = "https://www.edsm.net/api-logs-v1/get-position"
        data = {**self.bare_packet, "showCoordinates": 1}

        resp = requests.get(url, params=data)

        data = resp.json()
        if self.cur_system != data['system']:

            if self.cur_system is None:
                # update tot_distance
                self.calc_total_distance_traveled()
                
            else:
                dist = self.position.distance(GalaticPosition.FromDict(data['coordinates']))
                self.total_distance += dist
            
            self.position.update(data['coordinates'])
            self.cur_system = data['system']
            self.timestamp = data['date']

            return True, data['firstDiscover']
        return False, data['firstDiscover']

    def get_cur_system_info(self):
        return self.get_system_info(self.cur_system)

    def get_system_info(self, sys_name):
        if not self.cur_system:
            print("Current location not found")
            return

        url = "https://www.edsm.net/api-v1/system"
        data = {
            "systemName": sys_name,
            "showInformation": 1,
            "showPrimaryStar": 1
        }

        resp = requests.get(url, params=data)
        return resp.json()

    def distance_to_sol(self, position=None, r=2):
        if not position:
            position = self.position

        dist = distance(position.x, 0, position.y, 0, position.z, 0)
        return round(dist, 2)

    def live_stream(self):
        report = \
       "\tSystem: {} ({}: {} ly)\n" \
       "\tStar: {} ({})\n" \
       "\tTotal Dist: {} ly\n\n" \
       "\t{}" \
       "------------------------------------------------------------"

        loop = True

        try:
            while loop:
                changed, first_discover = self.get_last_position()
                if changed:

                    sys_info = self.get_cur_system_info()

                    to_home = self.home.distance(self.position, r=2)
                    sys_name = self.cur_system
                    
                        
                    logging.debug(sys_info)
                    star_name = sys_info['name']
                    star_type = sys_info['primaryStar'].get("type") or "Unknown"
                    scoopable = sys_info['primaryStar'].get("isScoopable") or False
                    info = sys_info['information']

                    info_content = "No Information\n"
                    
                    if first_discover:
                        sys_name = Fore.YELLOW + sys_name + Fore.RESET
                    
                    if scoopable:
                        scoopable = Fore.GREEN+str(scoopable)+Fore.RESET

                    if info:
                        info_content = ""
                        for k, v in info.items():
                            info_content += f"\t{k}:\t{v}\n"
                    fin_report = report.format(sys_name, self.home, to_home, star_type,
                                               scoopable,
                                               round(self.total_distance,2), info_content)

                    print(fin_report)
                time.sleep(REFRESH_TIME)
        except KeyboardInterrupt:
            print("Exiting...")


name = "CMD UYSOFSPADES"
api_key = "3c62e2ed9b7f841e2fc103acae2fb9e0e9b7d770"
commander = Commander(name, api_key)
