import math

import PySimpleGUI as sg
import requests


class GalaticPosition:
    @classmethod
    def FromDict(cls, d):
        return cls(d['x'], d['y'], d['z'])

    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def update(self, data: dict):
        self.x = data['x']
        self.y = data['y']
        self.z = data['z']

    def distance(self, pos):
        x = (xf - xi)**2
        y = (yf - yi)**2
        z = (zf - zi)**2
        return math.sqrt(x + y + z)
        return distance(self.x, pos.x, self.y, pos.y, self.z, pos.z)

    def __repr__(self):
        return str((self.x, self.y, self.z))
