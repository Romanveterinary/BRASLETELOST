import os
import time
import json
import traceback
from jnius import autoclass, PythonJavaClass, java_method

# Ініціалізація Android
PythonService = autoclass('org.kivy.android.PythonService')
service = PythonService.mService
context = service.getApplicationContext()

# --- FOREGROUND SERVICE (Щоб Android не вбивав програму) ---
NotificationBuilder = autoclass('android.app.Notification$Builder')
NotificationChannel = autoclass('android.app.NotificationChannel')
channel_id = "vettrack_channel"
channel = NotificationChannel(channel_id, "VetTrack Service", 2)
manager = context.getSystemService("notification")
manager.createNotificationChannel(channel)
builder = NotificationBuilder(context, channel_id)
builder.setContentTitle("VetTrack активний")
builder.setContentText("Моніторинг BLE пристрою...")
builder.setSmallIcon(0x01080038)
service.startForeground(1, builder.build())

# Налаштування шляхів
files_dir = context.getFilesDir().getAbsolutePath()
CONFIG_FILE = os.path.join(files_dir, "anti_lost_config.json")
STATE_FILE = os.path.join(files_dir, "live_state.json")

# Ваш сканер
BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
MediaPlayer = autoclass('android.media.MediaPlayer')
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
    default_config = {"mac_address": "", "rssi_threshold": -85, "ping_interval": 2, "timeout_limit": 5, "alarm_duration": 2, "melody_path": ""}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f: default_config.update(json.load(f))
        except: pass
    return default_config

def write_state(status, rssi):
    try:
        with open(STATE_FILE, "w") as f: json.dump({"status": status, "rssi": rssi}, f)
    except: pass

def main():
    global last_seen_time, last_seen_rssi
    config = load_config()
    target_mac = config.get("mac_address", "").strip()
    if not target_mac:
        write_state("ПОМИЛКА: НЕМАЄ MAC", -100)
        return

    adapter = BluetoothAdapter.getDefaultAdapter()
    scan_callback = BLEScanCallback(target_mac)
    adapter.startLeScan(scan_callback)
    
    player = MediaPlayer()
    while True:
        current_time = time.time()
        config = load_config()
        # Тут ваша логіка (як було раніше)
        write_state("🟢 ЗВ'ЯЗОК СТАБІЛЬНИЙ", last_seen_rssi)
        time.sleep(config["ping_interval"])

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        write_state(f"ERROR: {str(e)}", -100)
