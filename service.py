import os
import time
import json
from jnius import autoclass, PythonJavaClass, java_method

PythonService = autoclass('org.kivy.android.PythonService')
service_context = PythonService.mService
BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
MediaPlayer = autoclass('android.media.MediaPlayer')
AudioManager = autoclass('android.media.AudioManager')
Vibrator = service_context.getSystemService(autoclass('android.content.Context').VIBRATOR_SERVICE)

# Шляхи до файлів
files_dir = service_context.getFilesDir().getAbsolutePath()
CONFIG_FILE = os.path.join(files_dir, "anti_lost_config.json")
STATE_FILE = os.path.join(files_dir, "live_state.json")

# Глобальні змінні
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

def play_alarm(player):
    # Встановлюємо гучність на максимум
    audio_manager = service_context.getSystemService(autoclass('android.content.Context').AUDIO_SERVICE)
    audio_manager.setStreamVolume(AudioManager.STREAM_ALARM, audio_manager.getStreamMaxVolume(AudioManager.STREAM_ALARM), 0)
    
    player.start()
    # Вібро (патерн: 0мс затримки, 500мс вібро, 500мс пауза)
    if Vibrator:
        Vibrator.vibrate(500)

def main():
    global last_seen_time, last_seen_rssi
    
    # Завантажуємо конфіг
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f: config = json.load(f)
    
    target_mac = config.get("mac_address", "").strip()
    adapter = BluetoothAdapter.getDefaultAdapter()
    adapter.startLeScan(BLEScanCallback(target_mac))
    
    # Ініціалізація плеєра
    player = MediaPlayer()
    player.setAudioStreamType(AudioManager.STREAM_ALARM)
    try:
        from android.media import RingtoneManager
        uri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM)
        player.setDataSource(service_context, uri)
        player.prepare()
        player.setLooping(True)
    except: pass

    alarm_playing = False
    
    while True:
        time.sleep(2)
        is_lost = (time.time() - last_seen_time) > 3.0
        
        if is_lost:
            if not alarm_playing:
                play_alarm(player)
                alarm_playing = True
            # Запис статусу
            with open(STATE_FILE, "w") as f: json.dump({"status": "🚨 ТРИВОГА!", "rssi": last_seen_rssi}, f)
        else:
            if alarm_playing:
                player.pause()
                player.seekTo(0)
                alarm_playing = False
            with open(STATE_FILE, "w") as f: json.dump({"status": "🟢 СТАБІЛЬНО", "rssi": last_seen_rssi}, f)

if __name__ == '__main__':
    main()
