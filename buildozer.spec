[app]

# (string) Title of your application
title = VetTrack Anti-Lost

# (string) Package name
package.name = vettrack_antilost

# (string) Package domain (needed for android packaging)
package.domain = com.romanveterinary

# (string) Source code where the main.py lives
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,wav,mp3,json

# (string) Application version
version = 1.0

# (list) Application requirements (ДОДАНО PLYER)
requirements = python3,kivy==2.3.1,jnius,android,plyer

# (str) Supported orientations
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# --- РЕЄСТРАЦІЯ ФОНОВОЇ СЛУЖБИ ---
services = ServiceScanner:service.py:foreground

# (list) Permissions (ДОДАНО ФОНОВІ ДОЗВОЛИ ТА ДОСТУП ДО ФАЙЛІВ)
android.permissions = BLUETOOTH, BLUETOOTH_ADMIN, BLUETOOTH_SCAN, BLUETOOTH_CONNECT, ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION, ACCESS_BACKGROUND_LOCATION, WAKE_LOCK, REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, READ_EXTERNAL_STORAGE, READ_MEDIA_AUDIO

# (int) Target Android API
android.api = 33

# (str) Android SDK build-tools version to use
android.build_tools_version = 33.0.0

# (int) Minimum API your APK will support
android.minapi = 24

# (list) The Android architectures to build for
android.archs = arm64-v8a

# (str) Intent launch mode
android.manifest.launch_mode = singleTask

# (bool) Copy library instead of making a symlink
p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
