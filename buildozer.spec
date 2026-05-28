[app]
# Назва твого додатка на екрані телефона
title = VetTrack Anti-Lost

# Назва пакету для системи Android (без пробілів)
package.name = vettrack_antilost
package.domain = com.romanveterinary

# З якими файлами збирати додаток (включаємо Python та наш звук)
source.include_exts = py,png,jpg,kv,atlas,wav,mp3
source.dir = .

# Версія додатка
version = 1.0

# Бібліотеки, які Buildozer має зашити всередину APK
requirements = python3,kivy,bleak,asyncio

# Орієнтація екрану (строго вертикальна для смартфона)
orientation = portrait

# Системні вимоги та налаштування Android
osx.kivy_version = 2.3.1
fullscreen = 0
android.archs = arm64-v8a

# КРИТИЧНО ВАЖЛИВО: Дозволи на Bluetooth для Android 
# (без них радар на телефоні буде сліпим і система його заблокує)
android.permissions = BLUETOOTH, BLUETOOTH_ADMIN, BLUETOOTH_SCAN, BLUETOOTH_CONNECT, ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION

# Вказуємо, що додаток може працювати у фоні (щоб не вимикався в кишені)
android.manifest.launch_mode = singleTask
