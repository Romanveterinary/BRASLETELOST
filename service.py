import os
import time
import json
import traceback
from jnius import autoclass, PythonJavaClass, java_method

# --- ВАЖЛИВЕ ДОПОВНЕННЯ ДЛЯ FOREGROUND ---
PythonService = autoclass('org.kivy.android.PythonService')
service_context = PythonService.mService
context = service_context.getApplicationContext()

# Створюємо повідомлення в шторці (ОБОВ'ЯЗКОВО для роботи в фоні на Android)
NotificationBuilder = autoclass('android.app.Notification$Builder')
NotificationChannel = autoclass('android.app.NotificationChannel')
channel_id = "vettrack_channel"
channel = NotificationChannel(channel_id, "VetTrack Service", 2)
manager = context.getSystemService("notification")
manager.createNotificationChannel(channel)

builder = NotificationBuilder(context, channel_id)
builder.setContentTitle("VetTrack Anti-Lost")
builder.setContentText("Моніторинг BLE пристрою...")
builder.setSmallIcon(0x01080038)
service_context.startForeground(1, builder.build())
# ------------------------------------------

BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
Intent = autoclass('android.content.Intent')
MediaPlayer = autoclass('android.media.MediaPlayer')

files_dir = service_context.getFilesDir().getAbsolutePath()
CONFIG_FILE = os.path.join(files_dir, "anti_lost_config.json")
STATE_FILE = os.path.join(files_dir, "live_state.json") # Наша "поштова скринька"

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
        if device:
            address = device.getAddress()
            if address == self.target_mac:
                last_seen_time = time.time()
                last_seen_rssi = rssi

def load_config():
    default_config = {
        "mac_address": "",
        "rssi_threshold": -85,
        "ping_interval": 2,
        "timeout_limit": 5,
        "alarm_duration": 2,
        "melody_path": ""
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                default_config.update(data)
        except Exception:
            pass
    return default_config

# Функція запису поточного стану для графічного інтерфейсу
def write_state(status_text, rssi_val):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump({"status": status_text, "rssi": rssi_val}, f)
    except:
        pass

def main():
    global last_seen_time, last_seen_rssi
    
    # Очищуємо старий стан при запуску
    write_state("РАДАР ЗАПУЩЕНО, ШУКАЮ...", -100)
    
    config = load_config()
    target_mac = config.get("mac_address", "").strip()
    
    if not target_mac:
        write_state("ПОМИЛКА: НЕМАЄ MAC-АДРЕСИ", -100)
        return

    adapter = BluetoothAdapter.getDefaultAdapter()
    if not adapter:
        write_state("ПОМИЛКА: BLUETOOTH ВИМКНЕНО", -100)
        return

    scan_callback = BLEScanCallback(target_mac)
    adapter.startLeScan(scan_callback)
    
    player = MediaPlayer()
    alarm_playing = False
    disconnect_start_time = None
    
    try:
        melody = config.get("melody_path", "").strip()
        if melody and os.path.exists(melody):
            player.setDataSource(melody)
        else:
            app_dir = os.path.dirname(__file__)
            player.setDataSource(os.path.join(app_dir, "sonar.wav"))
        player.prepare()
        player.setLooping(True)
    except Exception as e:
        pass

    while True:
        current_time = time.time()
        config = load_config() 
        
        target_rssi = config["rssi_threshold"]
        timeout_limit = config["timeout_limit"]
        max_alarm_duration = config["alarm_duration"] * 60
        
        device_missing = (current_time - last_seen_time) > 2.0
        
        current_status = "НЕВІДОМО"
        
        if device_missing or last_seen_rssi < target_rssi:
            if disconnect_start_time is None:
                disconnect_start_time = current_time
                
            elapsed = current_time - disconnect_start_time
            
            if elapsed >= timeout_limit:
                current_status = "🚨 ТРИВОГА! ЗВ'ЯЗОК ВТРАЧЕНО 🚨"
                if not alarm_playing:
                    try:
                        intent = Intent()
                        intent.setAction("com.romanveterinary.LOST_ALARM")
                        service_context.sendBroadcast(intent)
                    except Exception:
                        pass
                        
                    try:
                        player.start()
                        alarm_playing = True
                    except:
                        pass
                        
                if alarm_playing and elapsed >= (timeout_limit + max_alarm_duration):
                    try:
                        player.pause()
                        alarm_playing = False
                    except:
                        pass
            else:
                time_left = int(timeout_limit - elapsed)
                current_status = f"ВТРАЧАЮ ЗВ'ЯЗОК! Сирена через {time_left} сек"
        else:
            current_status = "🟢 ЗВ'ЯЗОК СТАБІЛЬНИЙ"
            if alarm_playing:
                try:
                    player.pause()
                    player.seekTo(0)
                    alarm_playing = False
                except:
                    pass
            disconnect_start_time = None

        # Записуємо свіжий стан у нашу скриньку
        write_state(current_status, last_seen_rssi)

        time.sleep(config["ping_interval"])

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        write_state(f"FATAL ERROR: {e}", -100)
