import os
import time
import json
import traceback
from jnius import autoclass, PythonJavaClass, java_method

# 1. Отримуємо глибокий доступ до ядра Android
PythonService = autoclass('org.kivy.android.PythonService')
service_context = PythonService.mService

BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
Intent = autoclass('android.content.Intent')
MediaPlayer = autoclass('android.media.MediaPlayer')

# 2. Знаходимо наш спільний з main.py конфіг
files_dir = service_context.getFilesDir().getAbsolutePath()
CONFIG_FILE = os.path.join(files_dir, "anti_lost_config.json")

# Глобальні змінні пам'яті радара
last_seen_time = time.time()
last_seen_rssi = -100

# 3. Нативний сканер Bluetooth (працює без екрана)
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

def main():
    global last_seen_time, last_seen_rssi
    
    config = load_config()
    target_mac = config.get("mac_address", "").strip()
    
    if not target_mac:
        print("SERVICE ERROR: MAC address not configured!")
        return

    # Запуск сканера
    adapter = BluetoothAdapter.getDefaultAdapter()
    if not adapter:
        return

    scan_callback = BLEScanCallback(target_mac)
    adapter.startLeScan(scan_callback)
    
    # 4. Налаштування звукового плеєра Android
    player = MediaPlayer()
    alarm_playing = False
    disconnect_start_time = None
    
    try:
        melody = config.get("melody_path", "").strip()
        if melody and os.path.exists(melody):
            player.setDataSource(melody)
        else:
            # Беремо стандартну сирену, якщо своя не вибрана
            app_dir = os.path.dirname(__file__)
            player.setDataSource(os.path.join(app_dir, "sonar.wav"))
        player.prepare()
        player.setLooping(True)
    except Exception as e:
        print(f"Аудіо помилка: {e}")

    # 5. Головний безкінечний цикл служби
    while True:
        current_time = time.time()
        config = load_config() # Оновлюємо налаштування "на льоту"
        
        target_rssi = config["rssi_threshold"]
        timeout_limit = config["timeout_limit"]
        max_alarm_duration = config["alarm_duration"] * 60
        
        # Якщо пристрій "замовк" на 2 секунди
        device_missing = (current_time - last_seen_time) > 2.0
        
        if device_missing or last_seen_rssi < target_rssi:
            if disconnect_start_time is None:
                disconnect_start_time = current_time
                
            elapsed = current_time - disconnect_start_time
            
            # ЧАС ТРИВОГИ!
            if elapsed >= timeout_limit:
                if not alarm_playing:
                    # А. Відправляємо системний крик для Notify / MacroDroid
                    try:
                        intent = Intent()
                        intent.setAction("com.romanveterinary.LOST_ALARM")
                        service_context.sendBroadcast(intent)
                    except Exception:
                        pass
                        
                    # Б. Вмикаємо динамік телефону
                    try:
                        player.start()
                        alarm_playing = True
                    except:
                        pass
                        
                # Вмикаємо запобіжник (щоб не кричало вічно і не посадило батарею)
                if alarm_playing and elapsed >= (timeout_limit + max_alarm_duration):
                    try:
                        player.pause()
                        alarm_playing = False
                    except:
                        pass
        else:
            # Пристрій поруч, все добре
            if alarm_playing:
                try:
                    player.pause()
                    player.seekTo(0)
                    alarm_playing = False
                except:
                    pass
            disconnect_start_time = None

        # Засинаємо на вказаний інтервал, щоб зекономити процесор
        time.sleep(config["ping_interval"])

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"Service FATAL ERROR: {e}")
