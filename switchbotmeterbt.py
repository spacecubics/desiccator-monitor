import sys
import os
import subprocess
import time
from bluepy.btle import Scanner, DefaultDelegate
from influxdb import InfluxDBClient


INFLUXDB_HOST = 'localhost'
INFLUXDB_PORT = 8086
INFLUXDB_DBNAME = 'tempDB'

def store_in_influxdb(macaddr, temperature, humidity, battery, rssi):
    client = InfluxDBClient(host=INFLUXDB_HOST, port=INFLUXDB_PORT, database=INFLUXDB_DBNAME)
    data = [{
        "measurement": "switchbot_metrics",
        "tags": {"mac": macaddr},
        "fields": {
            "temperature": temperature,
            "humidity": humidity,
            "battery": battery,
            "rssi": rssi
        }
    }]
    client.write_points(data)
    client.close()

class SwitchbotScanDelegate(DefaultDelegate):
    def __init__(self, macaddrs):
        super().__init__()
        self.sensorValues = {}
        self.macaddrs = macaddrs

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if dev.addr in self.macaddrs:
            for (adtype, desc, value) in dev.getScanData():
                if desc == '16b Service Data':
                    self._decodeSensorData(dev, value)

    def _decodeSensorData(self, dev, value):
        valueBinary = bytes.fromhex(value[4:16])
        deviceType = chr(valueBinary[0] & 0b01111111)
        battery = valueBinary[2] & 0b01111111
        tint = valueBinary[4] & 0b01111111
        tdec = valueBinary[3] & 0b00001111
        temperature = tint + tdec / 10
        isTemperatureAboveFreezing = valueBinary[4] & 0b10000000
        if not isTemperatureAboveFreezing:
            temperature = -temperature
        humidity = valueBinary[5] & 0b01111111

        self.sensorValues[dev.addr] = {
            'DeviceType': deviceType,
            'Temperature': temperature,
            'Humidity': humidity,
            'Battery': battery,
            'RSSI': dev.rssi
        }
        store_in_influxdb(dev.addr, temperature, humidity, battery, dev.rssi)

class SwitchbotMeterPlugin():
    def __init__(self):
        self.params = {}
        self.params['pluginname'] = os.path.basename(__file__)
        self.params['macaddrs'] = [str.lower(macaddr) for macaddr in os.getenv('macaddr').split()]
        self.params['hcidev'] = int(os.getenv('hcidev', 0))
        self.params['scantimeout'] = float(os.getenv('scantimeout', 5.0))

    def fetch(self):
        scanner = Scanner(self.params['hcidev']).withDelegate(SwitchbotScanDelegate(self.params['macaddrs']))
        try:
            scanner.scan(self.params['scantimeout'])
        except Exception as e:
            subprocess.call(f'btmgmt --index {self.params["hcidev"]} power off && btmgmt --index {self.params["hcidev"]} power on', shell=True)
            scanner.scan(self.params['scantimeout'])

        for macaddr in self.params['macaddrs']:
            try:
                data = scanner.delegate.sensorValues[macaddr]
                print(f"{macaddr}: {data}")
            except KeyError:
                pass

def main():
    plugin = SwitchbotMeterPlugin()
    while True:
        plugin.fetch()
        time.sleep(1)

if __name__ == '__main__':
    main()
    #sudo env macaddr="EC:4B:05:BD:B8:6D" ~/zephyrproject/.venv/bin/python3 "/home/yuma/ドキュメント/19switchbotのデバイスアドレスを取得する/switchbotmeterbt.py"
