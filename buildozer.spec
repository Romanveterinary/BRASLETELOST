[app]
title = VetTrack Anti-Lost
package.name = vettrack_antilost
package.domain = com.romanveterinary
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,wav,mp3,json
version = 1.0
requirements = python3,kivy==2.3.1,jnius,android,plyer
orientation = portrait
fullscreen = 0

# Це критична лінія для запуску фонової служби
services = scanner:service.py:foreground

# Оновлені дозволи для роботи з Bluetooth на Android 12+
android.permissions = BLUETOOTH, BLUETOOTH_ADMIN, BLUETOOTH_SCAN, BLUETOOTH_CONNECT, ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION, ACCESS_BACKGROUND_LOCATION, WAKE_LOCK, FOREGROUND_SERVICE, REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, READ_EXTERNAL_STORAGE, READ_MEDIA_AUDIO

android.api = 33
android.minapi = 24
android.archs = arm64-v8a
android.manifest.launch_mode = singleTask

[buildozer]
log_level = 2
warn_on_root = 1
