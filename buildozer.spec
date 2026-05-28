name: Build APK

on:
  workflow_dispatch: # Ручний запуск

jobs:
  build:
    runs-on: ubuntu-22.04

    steps:
    - name: Checkout repository
      uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Setup Android SDK
      uses: android-actions/setup-android@v3
      with:
        log-accepted-licenses: false

    - name: Install system dependencies
      run: |
        sudo apt-get update
        sudo apt-get install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev tk-dev libgdbm-compat-dev libreoffice-dev

    - name: Install Buildozer and Cython
      run: |
        pip install --upgrade pip
        pip install "buildozer>=1.5.0" "cython<3.0.0" virtualenv Kivy

    - name: Build APK with Buildozer
      run: |
        # Запускаємо автоматичне підтвердження ліцензій перед стартом
        mkdir -p ~/.android
        touch ~/.android/repositories.cfg
        
        # Передаємо Buildozer команду на збірку
        buildozer android debug

    - name: Upload APK Artifact
      uses: actions/upload-artifact@v4
      with:
        name: VetTrack-AntiLost-APK
        path: bin/*.apk
