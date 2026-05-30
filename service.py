import os
import time
import json
from jnius import autoclass, PythonJavaClass, java_method

PythonService = autoclass('org.kivy.android.PythonService')
service_context = PythonService.mService
BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
MediaPlayer = autoclass('android.media.MediaPlayer')
AudioManager = autoclass('android.media.AudioManager')

# Файли залишаються тими ж
files_dir = service_context.getFilesDir().getAbsolutePath()
CONFIG_FILE = os.path.join(files_dir, "anti_lost_config.json")
STATE_FILE = os.path.join(files_dir, "live_state.json")

last_seen_time = time.time()
last_seen_rssi = -100

class BLEScanCallback(PythonJavaClass):
    __javainterfaces__ = ['android/bluetooth/BluetoothAdapter$LeScanCallback']
    __javacontext__ = 'app'

    def __init__(self, target_mac):
        super().__init__()
        self.target_mac = target_mac

    @java_method('(Landroid/bluetooth/BluetoothDevice;I[B)V')
    def onLeScan(self, device, rssi, scanRecord):
        global last_seen_time, last_seen_rssi
        if device and device.getAddress() == self.target_mac:
            last_seen_time = time.time()
            last_seen_rssi = rssi

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f: return json.load(f)
        except: pass
    return {"mac_address": "", "rssi_threshold": -85, "ping_interval": 2, "timeout_limit": 5, "alarm_duration": 2}

def write_state(status, rssi):
    try:
        with open(STATE_FILE, "w") as f: json.dump({"status": status, "rssi": rssi}, f)
    except: pass

def main():
    global last_seen_time, last_seen_rssi
    config = load_config()
    target_mac = config.get("mac_address", "").strip()
    
    adapter = BluetoothAdapter.getDefaultAdapter()
    adapter.startLeScan(BLEScanCallback(target_mac))
    
    player = MediaPlayer()
    # Спробуємо програти стандартний звук тривоги
    try:
        from android.media import RingtoneManager
        uri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM)
        player.setDataSource(service_context, uri)
        player.prepare()
        player.setLooping(True)
    except: pass

    alarm_playing = False
    disconnect_time = None

    while True:
        current_time = time.time()
        config = load_config()
        
        is_lost = (current_time - last_seen_time) > 3.0 or last_seen_rssi < config["rssi_threshold"]
        
        if is_lost:
            if disconnect_time is None: disconnect_time = current_time
            elapsed = current_time - disconnect_time
            
            if elapsed >= config["timeout_limit"]:
                if not alarm_playing:
                    try: player.start(); alarm_playing = True
                    except: pass
            status = "🚨 ТРИВОГА!"
        else:
            status = "🟢 СТАБІЛЬНО"
            if alarm_playing:
                try: player.pause(); player.seekTo(0); alarm_playing = False
                except: pass
            disconnect_time = None

        write_state(status, last_seen_rssi)
        time.sleep(config["ping_interval"])

if __name__ == '__main__':
    main()
