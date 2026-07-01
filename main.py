import traceback

try:
    import json
    import os
    import math
    from kivy.app import App
    from kivy.uix.screenmanager import ScreenManager, Screen
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.label import Label
    from kivy.uix.slider import Slider
    from kivy.uix.button import Button
    from kivy.uix.textinput import TextInput
    from kivy.uix.scrollview import ScrollView
    from kivy.uix.togglebutton import ToggleButton
    from kivy.core.window import Window
    from kivy.utils import platform
    from kivy.clock import Clock, mainthread

    if platform not in ('android', 'ios'):
        Window.size = (400, 720)

    if platform == "android":
        from jnius import autoclass, PythonJavaClass, java_method
        BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
        
        class BLEScanCallback(PythonJavaClass):
            __javainterfaces__ = ['android/bluetooth/BluetoothAdapter$LeScanCallback']
            __javacontext__ = 'app'

            def __init__(self, ui_callback):
                super().__init__()
                self.ui_callback = ui_callback

            @java_method('(Landroid/bluetooth/BluetoothDevice;I[B)V')
            def onLeScan(self, device, rssi, scanRecord):
                if device:
                    address = device.getAddress()
                    name = device.getName()
                    self.ui_callback(address, name, rssi)

    # --- БЛОК ПЕРЕКЛАДІВ ТА ІНСТРУКЦІЙ ---
    LANG = {
        "uk": {
            "app_title": "VET-TRACK: ANTI-LOST",
            "ready": "ГОТОВИЙ ДО ЗАПУСКУ ФОНУ",
            "no_dev": "ПРИСТРІЙ НЕ ВИБРАНО",
            "rssi_title": "СИЛА СИГНАЛУ (RSSI / ВІДСТАНЬ)",
            "ping_title": "ІНТЕРВАЛ ОПИТУВАННЯ",
            "delay_title": "ЗАТРИМКА ТРИВОГИ",
            "dur_title": "ТРИВАЛІСТЬ СИРЕНИ",
            "start_bg": "ЗАПУСТИТИ ФОН",
            "stop_bg": "ЗУПИНИТИ ФОН",
            "find_bt": "ПОШУК ПРИСТРОЮ (ОБЕРІТЬ МЕТУ)",
            "find_wifi": "ПОШУК WI-FI",
            "settings": "НАЛАШТУВАННЯ",
            "inst_btn": "📖 ІНСТРУКЦІЯ КОРИСТУВАЧА",
            "save_cfg": "ЗБЕРЕГТИ КОНФІГУРАЦІЮ",
            "scan_bt": "ЗАПУСТИТИ РАДАР ЕФІРУ",
            "stop_search": "ЗУПИНИТИ ПОШУК",
            "hot": "ГАРЯЧЕ!\nВІН ТУТ!",
            "warm": "ТЕПЛО\nБЛИЗЬКО",
            "cold": "ХОЛОДНО\nДАЛЕКО",
            "wifi_hot": "ГАРЯЧЕ!\nРОУТЕР ТУТ!",
            "wifi_warm": "ТЕПЛО\nУ ЦІЙ КІМНАТІ",
            "wait_sig": "ШУКАЮ ПРИСТРОЇ НАВКОЛО...",
            "target": "МЕТА",
            "signal": "Сигнал",
            "inst_title": "ІНСТРУКЦІЯ",
            "back": "ПОВЕРНУТИСЯ",
            "mac_lbl": "Bluetooth MAC-адреса:",
            "mel_lbl": "Власна мелодія (пусто = стандартна):",
            "browse": "ОГЛЯД",
            "radar_lbl": "БЛЮТУЗ РАДАР (Клікни на пристрій):",
            "threshold": "Поріг",
            "every": "Кожні",
            "wait": "Очікування",
            "turn_off": "Вимкнення через",
            "sec": "сек",
            "min": "хв",
            "m": "м",
            "inst_text": """Цей додаток перетворює ваш телефон або планшет на охоронний радар для будь-якого Bluetooth-пристрою (фітнес-браслет, навушники, годинник тощо). Програма працює у фоновому режимі.

• Крок 1: Вибір пристрою через Пошук
Натисніть кнопку "ПОШУК ПРИСТРОЮ" на головному екрані. Програма почне бачити всі девайси навколо у реальному часі. Знайдіть свій браслет, подивіться на його сигнал (Гаряче/Тепло/Холодно) і просто натисніть на нього. Програма сама збереже його і поверне вас на головну сторінку.

• Сила сигналу (Поріг RSSI)
Верхній повзунок регулює орієнтовну відстань між девайсом та телефоном. Що ближче до -60 dBm, то на меншій відстані спрацює тривога.

• Інтервал опитування
Це частота, з якою телефон перевіряє наявність девайса.

• Затримка тривоги
Захищає від помилкових спрацьовувань: якщо зв'язок розірвався на мить, сирена не увімкнеться.

• Тривалість сирени
Захищає телефон від повного розряду батареї у разі остаточної втрати девайса.

🔋 Економія батареї та Фонова робота
Для економії заряду не використовуйте радар постійно (витрата 2-8% на годину). 
⚠️ УВАГА: Щоб програма стабільно працювала при вимкненому екрані, обов'язково зайдіть у налаштування батареї телефону та дозвольте додатку VetTrack роботу "Без обмежень" (Unrestricted)."""
        },
        "en": {
            "app_title": "VET-TRACK: ANTI-LOST",
            "ready": "READY FOR BACKGROUND",
            "no_dev": "NO DEVICE SELECTED",
            "rssi_title": "SIGNAL STRENGTH (RSSI / DISTANCE)",
            "ping_title": "PING INTERVAL",
            "delay_title": "ALARM DELAY",
            "dur_title": "SIREN DURATION",
            "start_bg": "START BACKGROUND",
            "stop_bg": "STOP BACKGROUND",
            "find_bt": "FIND DEVICE (CHOOSE TARGET)",
            "find_wifi": "FIND WI-FI",
            "settings": "SETTINGS",
            "inst_btn": "📖 USER MANUAL",
            "save_cfg": "SAVE CONFIGURATION",
            "scan_bt": "START ETHER RADAR",
            "stop_search": "STOP SEARCH",
            "hot": "HOT!\nIT'S HERE!",
            "warm": "WARM\nNEARBY",
            "cold": "COLD\nFAR AWAY",
            "wifi_hot": "HOT!\nROUTER IS HERE!",
            "wifi_warm": "WARM\nIN THIS ROOM",
            "wait_sig": "SCANNING FOR DEVICES...",
            "target": "TARGET",
            "signal": "Signal",
            "inst_title": "INSTRUCTIONS",
            "back": "GO BACK",
            "mac_lbl": "Bluetooth MAC address:",
            "mel_lbl": "Custom melody (empty = default):",
            "browse": "BROWSE",
            "radar_lbl": "BLUETOOTH RADAR (Click a device):",
            "threshold": "Threshold",
            "every": "Every",
            "wait": "Wait",
            "turn_off": "Turn off after",
            "sec": "sec",
            "min": "min",
            "m": "m",
            "inst_text": """This app turns your phone or tablet into a security radar for any Bluetooth device (fitness band, headphones, smartwatch, etc.). The app runs in the background.

• Step 1: Select Device via Find Screen
Tap "FIND DEVICE" on the main screen. The app will scan and display all nearby devices in real-time. Find your tracker, check its signal level (Hot/Warm/Cold), and simply tap on it. The app will save it and automatically return you to the main screen.

• Signal Strength (RSSI Threshold)
Adjusts the approximate distance. Closer to -60 dBm means the alarm will trigger at a shorter distance.

• Ping Interval
How often your phone scans for the paired device.

• Alarm Delay
Prevents false alarms: if the connection drops momentarily, the siren will not sound.

• Siren Duration
Prevents your phone from draining its battery completely if the device is permanently lost.

🔋 Battery Saving & Background Work
Do not use the radar constantly (consumes 2-8% per hour). To reduce drain, set a longer Ping Interval.
⚠️ WARNING: For the app to work reliably when the screen is off, you must go to your phone's battery settings and set VetTrack to "Unrestricted" background usage."""
        },
        "pt": {
            "app_title": "VET-TRACK: ANTI-LOST",
            "ready": "PRONTO PARA FUNDO",
            "no_dev": "NENHUM DISPOSITIVO",
            "rssi_title": "FORÇA DO SINAL (RSSI / DISTÂNCIA)",
            "ping_title": "INTERVALO DE PING",
            "delay_title": "ATRASO DO ALARME",
            "dur_title": "DURAÇÃO DA SIRENE",
            "start_bg": "INICIAR FUNDO",
            "stop_bg": "PARAR FUNDO",
            "find_bt": "BUSCAR DISPOSITIVO (ALVO)",
            "find_wifi": "ENCONTRAR WI-FI",
            "settings": "CONFIGURAÇÕES",
            "inst_btn": "📖 MANUAL DO USUÁRIO",
            "save_cfg": "SALVAR CONFIGURAÇÃO",
            "scan_bt": "INICIAR RADAR",
            "stop_search": "PARAR BUSCA",
            "hot": "QUENTE!\nAQUI!",
            "warm": "MORNO\nPERTO",
            "cold": "FRIO\nLONGE",
            "wifi_hot": "QUENTE!\nROTEADOR AQUI!",
            "wifi_warm": "MORNO\nNESTA SALA",
            "wait_sig": "BUSCANDO DISPOSITIVOS...",
            "target": "ALVO",
            "signal": "Sinal",
            "inst_title": "INSTRUÇÕES",
            "back": "VOLTAR",
            "mac_lbl": "Endereço MAC Bluetooth:",
            "mel_lbl": "Melodia (vazio = padrão):",
            "browse": "PROCURAR",
            "radar_lbl": "RADAR BLUETOOTH (Clique num disp.):",
            "threshold": "Limite",
            "every": "A cada",
            "wait": "Espera",
            "turn_off": "Desliga após",
            "sec": "seg",
            "min": "min",
            "m": "m",
            "inst_text": """Este aplicativo transforma seu celular ou tablet em um radar de segurança para qualquer dispositivo Bluetooth (pulseira fitness, fones de ouvido, smartwatch, etc.). Funciona em segundo plano.

• Passo 1: Selecione o Dispositivo via Busca
Toque em "BUSCAR DISPOSITIVO" na tela principal. O aplicativo irá escanear e exibir todos os dispositivos próximos em tempo real. Encontre seu rastreador, verifique o sinal (Quente/Morno/Frio) e simplesmente toque nele. O aplicativo irá salvar e voltar automaticamente para a tela principal.

• Força do Sinal (Limite RSSI)
Ajusta a distância aproximada. Mais perto de -60 dBm significa que o alarme disparará a uma distância menor.

• Intervalo de Ping
Frequência com que o telefone procura o dispositivo.

• Atraso do Alarme
Evita alarmes falsos se a conexão cair momentaneamente.

• Duração da Sirene
Evita que a bateria acabe completamente se o dispositivo for perdido.

🔋 Economia de Bateria e Segundo Plano
Não use o radar constantemente (consome 2-8% por hora).
⚠️ AVISO: Para que o aplicativo funcione de forma confiável com a tela desligada, você deve ir nas configurações de bateria do seu telefone e permitir que o VetTrack funcione "Sem restrições" (Unrestricted)."""
        }
    }

    def get_config_path():
        return os.path.join(App.get_running_app().user_data_dir, "anti_lost_config.json")

    def get_state_path():
        return os.path.join(App.get_running_app().user_data_dir, "live_state.json")

    def load_full_config():
        default_config = {
            "mac_address": "",
            "device_name": "Невідомий пристрій",
            "rssi_threshold": -85,
            "ping_interval": 2,
            "timeout_limit": 5,
            "alarm_duration": 2,
            "melody_path": "",
            "language": "uk"
        }
        config_file = get_config_path()
        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    data = json.load(f)
                    default_config.update(data)
            except Exception:
                pass
        return default_config

    def save_full_config(data):
        config = load_full_config()
        config.update(data)
        with open(get_config_path(), "w") as f:
            json.dump(config, f)

    def get_t(key):
        config = load_full_config()
        lang = config.get("language", "uk")
        return LANG.get(lang, LANG["uk"]).get(key, key)

    def calc_distance(rssi):
        tx_power = -59
        n = 2.5
        if rssi == 0:
            return 0.0
        distance = math.pow(10, (tx_power - rssi) / (10 * n))
        return round(distance, 1)

    # --- ЕКРАНИ ДОДАТКА ---

    class MainScreen(Screen):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.layout = BoxLayout(orientation='vertical', padding=30, spacing=15)

            self.title_label = Label(text="VET-TRACK: ANTI-LOST", font_size='24sp', bold=True, size_hint_y=0.1)
            self.layout.add_widget(self.title_label)

            self.status_label = Label(text="", font_size='14sp', bold=True, color=(0.5, 0.5, 0.5, 1), size_hint_y=0.1)
            self.layout.add_widget(self.status_label)

            self.target_label = Label(text="", font_size='22sp', bold=True, color=(0.2, 0.8, 0.2, 0.2), size_hint_y=0.1)
            self.layout.add_widget(self.target_label)

            config = load_full_config()

            box_rssi = BoxLayout(orientation='vertical', size_hint_y=0.15)
            self.rssi_title = Label(text="СИЛА СИГНАЛУ", font_size='14sp', bold=True)
            box_rssi.add_widget(self.rssi_title)
            self.rssi_slider = Slider(min=-95, max=-60, value=config["rssi_threshold"], step=1)
            self.rssi_slider.bind(value=self.on_rssi_change)
            self.rssi_info = Label(text="", font_size='12sp', color=(0.7, 0.7, 0.7, 1))
            box_rssi.add_widget(self.rssi_slider)
            box_rssi.add_widget(self.rssi_info)
            self.layout.add_widget(box_rssi)

            box_ping = BoxLayout(orientation='vertical', size_hint_y=0.15)
            self.ping_title = Label(text="ІНТЕРВАЛ ОПИТУВАННЯ", font_size='14sp', bold=True)
            box_ping.add_widget(self.ping_title)
            self.ping_slider = Slider(min=1, max=10, value=config["ping_interval"], step=1)
            self.ping_slider.bind(value=self.on_ping_change)
            self.ping_info = Label(text="", font_size='12sp', color=(0.7, 0.7, 0.7, 1))
            box_ping.add_widget(self.ping_slider)
            box_ping.add_widget(self.ping_info)
            self.layout.add_widget(box_ping)

            box_time = BoxLayout(orientation='vertical', size_hint_y=0.15)
            self.delay_title = Label(text="ЗАТРИМКА ТРИВОГИ", font_size='14sp', bold=True)
            box_time.add_widget(self.delay_title)
            self.time_slider = Slider(min=2, max=30, value=config["timeout_limit"], step=1)
            self.time_slider.bind(value=self.on_time_change)
            self.time_info = Label(text="", font_size='12sp', color=(0.7, 0.7, 0.7, 1))
            box_time.add_widget(self.time_slider)
            box_time.add_widget(self.time_info)
            self.layout.add_widget(box_time)

            box_dur = BoxLayout(orientation='vertical', size_hint_y=0.15)
            self.dur_title = Label(text="ТРИВАЛІСТЬ СИРЕНИ", font_size='14sp', bold=True)
            box_dur.add_widget(self.dur_title)
            self.duration_slider = Slider(min=1, max=5, value=config["alarm_duration"], step=1)
            self.duration_slider.bind(value=self.on_duration_change)
            self.duration_info = Label(text="", font_size='12sp', color=(0.7, 0.7, 0.7, 1))
            box_dur.add_widget(self.duration_slider)
            box_dur.add_widget(self.duration_info)
            self.layout.add_widget(box_dur)

            box_btns = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=0.1)
            self.btn_start = Button(font_size='14sp', bold=True, background_color=(0.2, 0.8, 0.2, 1))
            self.btn_start.bind(on_press=self.start_service)
            self.btn_stop = Button(font_size='14sp', bold=True, background_color=(0.8, 0.2, 0.2, 1))
            self.btn_stop.bind(on_press=self.stop_service)
            box_btns.add_widget(self.btn_start)
            box_btns.add_widget(self.btn_stop)
            self.layout.add_widget(box_btns)

            box_find_btns = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=0.1)
            self.btn_find = Button(font_size='12sp', bold=True, background_color=(0.2, 0.6, 0.8, 1))
            self.btn_find.bind(on_press=self.go_to_find)
            self.btn_find_wifi = Button(font_size='12sp', bold=True, background_color=(0.8, 0.6, 0.2, 1))
            self.btn_find_wifi.bind(on_press=self.go_to_wifi_find)
            box_find_btns.add_widget(self.btn_find)
            box_find_btns.add_widget(self.btn_find_wifi)
            self.layout.add_widget(box_find_btns)

            self.btn_settings = Button(font_size='14sp', background_color=(0.3, 0.3, 0.3, 1), size_hint_y=0.1)
            self.btn_settings.bind(on_press=self.go_to_settings)
            self.layout.add_widget(self.btn_settings)

            self.add_widget(self.layout)
            Clock.schedule_interval(self.update_live_ui, 0.5)
            self.service_running = False

        def on_enter(self):
            self.title_label.text = get_t("app_title")
            
            config = load_full_config()
            if config.get("mac_address"):
                mac = config.get("mac_address")
                name = config.get("device_name", "Device")
                self.target_label.text = f"{get_t('target')}: {name}\n[{mac}]"
                self.target_label.color = (0.2, 0.8, 0.2, 1)
            else:
                self.target_label.text = get_t("no_dev")
                self.target_label.color = (0.5, 0.5, 0.5, 0.5)

            if not self.service_running:
                self.status_label.text = get_t("ready")
                self.status_label.color = (0.5, 0.5, 0.5, 1)

            self.rssi_title.text = get_t("rssi_title")
            self.ping_title.text = get_t("ping_title")
            self.delay_title.text = get_t("delay_title")
            self.dur_title.text = get_t("dur_title")
            self.btn_start.text = get_t("start_bg")
            self.btn_stop.text = get_t("stop_bg")
            self.btn_find.text = get_t("find_bt")
            self.btn_find_wifi.text = get_t("find_wifi")
            self.btn_settings.text = get_t("settings")
            
            self.on_rssi_change(None, self.rssi_slider.value)
            self.on_ping_change(None, self.ping_slider.value)
            self.on_time_change(None, self.time_slider.value)
            self.on_duration_change(None, self.duration_slider.value)

        def update_live_ui(self, dt):
            if not self.service_running:
                return
            state_file = get_state_path()
            if os.path.exists(state_file):
                try:
                    with open(state_file, "r") as f:
                        state_data = json.load(f)
                        status_text = state_data.get("status", "ОЧІКУВАННЯ...")
                        rssi_val = state_data.get("rssi", -100)
                        self.status_label.text = status_text
                        
                        if "ТРИВОГА" in status_text or "ВТРАЧАЮ" in status_text or "ALARM" in status_text:
                            self.status_label.color = (1, 0.2, 0.2, 1)
                        elif "СТАБІЛЬНИЙ" in status_text or "STABLE" in status_text:
                            self.status_label.color = (0.2, 0.8, 0.2, 1)
                        else:
                            self.status_label.color = (0.8, 0.8, 0.2, 1)

                        alpha = max(0.1, min(1.0, (rssi_val + 100) / 50.0))
                        config = load_full_config()
                        mac = config.get("mac_address", "...")
                        name = config.get("device_name", "Device")
                        dist = calc_distance(rssi_val)
                        
                        t_lbl = get_t("target")
                        s_lbl = get_t("signal")
                        m_lbl = get_t("m")
                        self.target_label.text = f"{t_lbl}: {name}\n[{mac}]\n{s_lbl} {rssi_val} dBm (~{dist} {m_lbl})"
                        self.target_label.color = (0.2, 0.8, 0.2, alpha)
                except Exception:
                    pass

        def on_rssi_change(self, instance, value):
            dist = calc_distance(value)
            self.rssi_info.text = f"{get_t('threshold')}: {int(value)} dBm (~{dist} {get_t('m')})"
            
        def on_ping_change(self, instance, value): self.ping_info.text = f"{get_t('every')}: {int(value)} {get_t('sec')}"
        def on_time_change(self, instance, value): self.time_info.text = f"{get_t('wait')}: {int(value)} {get_t('sec')}"
        def on_duration_change(self, instance, value): self.duration_info.text = f"{get_t('turn_off')}: {int(value)} {get_t('min')}"

        def start_service(self, instance):
            save_full_config({
                "rssi_threshold": self.rssi_slider.value,
                "ping_interval": self.ping_slider.value,
                "timeout_limit": self.time_slider.value,
                "alarm_duration": self.duration_slider.value
            })
            config = load_full_config()
            if not config.get("mac_address"):
                self.status_label.text = get_t("no_dev")
                self.status_label.color = (1, 0.2, 0.2, 1)
                return

            self.rssi_slider.disabled = True
            self.ping_slider.disabled = True
            self.time_slider.disabled = True
            self.duration_slider.disabled = True
            self.btn_settings.disabled = True
            self.btn_find.disabled = True
            self.btn_find_wifi.disabled = True

            if platform == 'android':
                try:
                    from jnius import autoclass
                    service = autoclass("com.romanveterinary.vettrack_antilost.ServiceScanner")
                    mActivity = autoclass("org.kivy.android.PythonActivity").mActivity
                    service.start(mActivity, "")
                    self.service_running = True
                    self.status_label.text = "СЛУЖБА ПРАЦЮЄ У ФОНІ / RUNNING"
                    self.status_label.color = (0.2, 0.8, 0.2, 1)
                except Exception as e:
                    self.status_label.text = f"Error: {str(e)}"
                    self.status_label.color = (1, 0.2, 0.2, 1)

        def stop_service(self, instance):
            self.status_label.text = "ЗУПИНЕНО / STOPPED"
            self.status_label.color = (0.5, 0.5, 0.5, 1)
            self.service_running = False
            
            self.rssi_slider.disabled = False
            self.ping_slider.disabled = False
            self.time_slider.disabled = False
            self.duration_slider.disabled = False
            self.btn_settings.disabled = False
            self.btn_find.disabled = False
            self.btn_find_wifi.disabled = False
            
            self.on_enter()

            try:
                state_file = get_state_path()
                if os.path.exists(state_file):
                    os.remove(state_file)
            except:
                pass

            if platform == 'android':
                try:
                    from jnius import autoclass
                    service = autoclass("com.romanveterinary.vettrack_antilost.ServiceScanner")
                    mActivity = autoclass("org.kivy.android.PythonActivity").mActivity
                    service.stop(mActivity)
                except Exception:
                    pass

        def go_to_settings(self, instance):
            self.manager.current = 'settings'
            
        def go_to_find(self, instance):
            self.manager.current = 'find_device'

        def go_to_wifi_find(self, instance):
            self.manager.current = 'find_wifi'


    # --- НОВИЙ МОДЕРНІЗОВАНИЙ ЕКРАН ЖИВОГО ПОШУКУ ТА ВИБОРУ ---
    class FindScreen(Screen):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.found_devices = {}  # Словник: {mac: {button_widget, smoothed_rssi, name}}
            self.bluetooth_adapter = None
            self.scan_callback = None
            if platform == "android":
                self.bluetooth_adapter = BluetoothAdapter.getDefaultAdapter()

            layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
            
            self.title_label = Label(font_size='18sp', bold=True, size_hint_y=0.1)
            layout.add_widget(self.title_label)

            # Контейнер для списку пристроїв з прокруткою
            self.scroll_view = ScrollView(size_hint=(1, 0.75))
            self.devices_container = BoxLayout(orientation='vertical', spacing=8, size_hint_y=None)
            self.devices_container.bind(minimum_height=self.devices_container.setter('height'))
            self.scroll_view.add_widget(self.devices_container)
            layout.add_widget(self.scroll_view)

            self.btn_back = Button(font_size='16sp', bold=True, background_color=(0.8, 0.2, 0.2, 1), size_hint_y=0.15)
            self.btn_back.bind(on_press=self.stop_search)
            layout.add_widget(self.btn_back)

            self.add_widget(layout)

        def on_enter(self):
            self.title_label.text = get_t("find_bt")
            self.btn_back.text = get_t("stop_search")
            self.devices_container.clear_widgets()
            self.devices_container.height = 0
            self.found_devices.clear()

            # Запуск безперервного живого сканування всього ефіру
            if self.bluetooth_adapter:
                self.scan_callback = BLEScanCallback(self.on_device_found)
                self.bluetooth_adapter.startLeScan(self.scan_callback)

        @mainthread
        def on_device_found(self, address, name, rssi):
            dev_name = name if name else "Device / Невідомий"
            
            if address not in self.found_devices:
                # Якщо пристрій з'явився вперше, створюємо для нього інтерактивну кнопку
                btn = Button(text="", size_hint=(1, None), height=110, font_size='14sp', halign='center', valign='middle')
                btn.bind(on_press=lambda inst, addr=address, n=dev_name: self.select_device(addr, n))
                self.devices_container.add_widget(btn)
                self.devices_container.height += 118
                
                self.found_devices[address] = {
                    "button": btn,
                    "smoothed_rssi": rssi,
                    "name": dev_name
                }
            else:
                # Застосовуємо математичний амортизатор індивідуально для кожного пристрою
                old_rssi = self.found_devices[address]["smoothed_rssi"]
                self.found_devices[address]["smoothed_rssi"] = (0.2 * rssi) + (0.8 * old_rssi)

            smooth_val = int(self.found_devices[address]["smoothed_rssi"])
            dist = calc_distance(smooth_val)
            btn = self.found_devices[address]["button"]
            
            # Розрахунок статусу та зміна кольору кнопки (Гаряче/Тепло/Холодно)
            if smooth_val >= -65:
                status_text = get_t("hot").replace('\n', ' ')
                btn.background_color = (1, 0.2, 0.2, 1) # Червоний
            elif smooth_val >= -80:
                status_text = get_t("warm").replace('\n', ' ')
                btn.background_color = (1, 0.8, 0.2, 1) # Жовтий
            else:
                status_text = get_t("cold").replace('\n', ' ')
                btn.background_color = (0.2, 0.6, 1, 1) # Синій

            btn.text = f"{dev_name}\n[{address}] | {smooth_val} dBm (~{dist} {get_t('m')})\n{status_text}"

        def select_device(self, address, name):
            # Клік на пристрій зберігає його як ціль і повертає на головний екран
            save_full_config({
                "mac_address": address,
                "device_name": name
            })
            self.stop_search(None)

        def stop_search(self, instance):
            if self.bluetooth_adapter and self.scan_callback:
                self.bluetooth_adapter.stopLeScan(self.scan_callback)
                self.scan_callback = None
            self.manager.current = 'main'


    class WifiFindScreen(Screen):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            layout = BoxLayout(orientation='vertical', padding=30, spacing=20)
            self.title_label = Label(font_size='20sp', bold=True, size_hint_y=0.1)
            layout.add_widget(self.title_label)
            self.distance_label = Label(font_size='30sp', bold=True, color=(0.5, 0.5, 0.5, 1), size_hint_y=0.6)
            layout.add_widget(self.distance_label)
            self.details_label = Label(font_size='16sp', color=(0.7, 0.7, 0.7, 1), size_hint_y=0.1)
            layout.add_widget(self.details_label)
            btn_back = Button(font_size='16sp', bold=True, background_color=(0.8, 0.2, 0.2, 1), size_hint_y=0.2)
            btn_back.bind(on_press=self.stop_search)
            layout.add_widget(btn_back)
            self.add_widget(layout)

        def on_enter(self):
            self.title_label.text = get_t("find_wifi")
            self.distance_label.text = get_t("wait_sig")
            self.btn_back.text = get_t("stop_search")
            self.check_event = Clock.schedule_interval(self.check_wifi_signal, 1.0)

        def check_wifi_signal(self, dt):
            if platform != "android":
                self.details_label.text = "Android Only"
                return
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Context = autoclass('android.content.Context')
                wifi_manager = PythonActivity.mActivity.getSystemService(Context.WIFI_SERVICE)
                wifi_info = wifi_manager.getConnectionInfo()
                network_id = wifi_info.getNetworkId()
                
                if network_id == -1:
                    self.distance_label.text = "..."
                    self.details_label.text = "Connect to Wi-Fi first"
                    return

                rssi = wifi_info.getRssi()
                ssid = wifi_info.getSSID().replace('"', '') 
                
                self.title_label.text = f"Wi-Fi: {ssid}"
                self.details_label.text = f"{get_t('signal')} {rssi} dBm"

                if rssi >= -50:
                    self.distance_label.text = get_t("wifi_hot")
                    self.distance_label.color = (1, 0.2, 0.2, 1)
                elif rssi >= -65:
                    self.distance_label.text = get_t("wifi_warm")
                    self.distance_label.color = (1, 0.8, 0.2, 1)
                else:
                    self.distance_label.text = get_t("cold")
                    self.distance_label.color = (0.2, 0.6, 1, 1)
            except Exception:
                pass

        def stop_search(self, instance):
            if hasattr(self, 'check_event'):
                self.check_event.cancel()
            self.manager.current = 'main'

    class SettingsScreen(Screen):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
            
            box_lang = BoxLayout(orientation='horizontal', size_hint_y=0.1, spacing=10)
            btn_uk = Button(text="🇺🇦 UKR", font_size='16sp', background_color=(0.3, 0.5, 0.8, 1))
            btn_en = Button(text="🇬🇧 ENG", font_size='16sp', background_color=(0.8, 0.3, 0.3, 1))
            btn_pt = Button(text="🇵🇹 POR", font_size='16sp', background_color=(0.2, 0.6, 0.2, 1))
            
            btn_uk.bind(on_press=lambda x: self.change_language("uk"))
            btn_en.bind(on_press=lambda x: self.change_language("en"))
            btn_pt.bind(on_press=lambda x: self.change_language("pt"))
            
            box_lang.add_widget(btn_uk)
            box_lang.add_widget(btn_en)
            box_lang.add_widget(btn_pt)
            layout.add_widget(box_lang)

            self.title_label = Label(font_size='20sp', bold=True, size_hint_y=0.1)
            layout.add_widget(self.title_label)
            
            self.mac_lbl = Label(font_size='14sp', size_hint_y=0.05, halign='left')
            layout.add_widget(self.mac_lbl)
            self.mac_input = TextInput(text="", multiline=False, font_size='14sp', size_hint_y=0.1)
            layout.add_widget(self.mac_input)

            self.mel_lbl = Label(font_size='14sp', size_hint_y=0.05)
            layout.add_widget(self.mel_lbl)
            box_melody = BoxLayout(orientation='horizontal', size_hint_y=0.1, spacing=5)
            self.melody_input = TextInput(text="", multiline=False, font_size='12sp', size_hint_x=0.7)
            self.btn_choose_melody = Button(font_size='14sp', background_color=(0.4, 0.4, 0.4, 1), size_hint_x=0.3)
            self.btn_choose_melody.bind(on_press=self.choose_melody)
            box_melody.add_widget(self.melody_input)
            box_melody.add_widget(btn_choose_melody)
            layout.add_widget(box_melody)

            box_bottom = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=0.15)
            self.btn_inst = Button(font_size='14sp', background_color=(0.6, 0.4, 0.8, 1))
            self.btn_inst.bind(on_press=self.go_to_inst)
            self.btn_save = Button(font_size='14sp', bold=True, background_color=(0.2, 0.8, 0.2, 1))
            self.btn_save.bind(on_press=self.save_config)
            
            box_bottom.add_widget(self.btn_inst)
            box_bottom.add_widget(self.btn_save)
            layout.add_widget(box_bottom)

            self.add_widget(layout)
            
        def on_enter(self):
            self.load_config()
            self.update_texts()
            
        def update_texts(self):
            self.title_label.text = get_t("settings")
            self.mac_lbl.text = get_t("mac_lbl")
            self.mel_lbl.text = get_t("mel_lbl")
            self.btn_choose_melody.text = get_t("browse")
            self.btn_inst.text = get_t("inst_btn")
            self.btn_save.text = get_t("save_cfg")

        def change_language(self, lang_code):
            save_full_config({"language": lang_code})
            self.update_texts()

        def choose_melody(self, instance):
            try:
                from plyer import filechooser
                filechooser.open_file(on_selection=self.handle_selection, filters=[("Audio", "*.mp3", "*.wav")])
            except:
                pass

        @mainthread
        def handle_selection(self, selection):
            if selection:
                self.melody_input.text = selection[0]

        def go_to_inst(self, instance):
            self.manager.current = 'instruction'

        def save_config(self, instance):
            save_full_config({
                "mac_address": self.mac_input.text.strip(),
                "melody_path": self.melody_input.text.strip()
            })
            self.manager.current = 'main'

        def load_config(self):
            config = load_full_config()
            self.mac_input.text = config.get("mac_address", "")
            self.melody_input.text = config.get("melody_path", "")

    class InstructionScreen(Screen):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
            self.title_label = Label(font_size='22sp', bold=True, size_hint_y=0.1)
            layout.add_widget(self.title_label)
            
            sv = ScrollView(size_hint_y=0.8)
            self.text_label = Label(font_size='14sp', size_hint_y=None, halign='left', valign='top')
            self.text_label.bind(width=lambda *x: self.text_label.setter('text_size')(self.text_label, (self.text_label.width, None)),
                                 texture_size=lambda *x: self.text_label.setter('height')(self.text_label, self.text_label.texture_size[1]))
            sv.add_widget(self.text_label)
            layout.add_widget(sv)
            
            self.btn_back = Button(font_size='16sp', bold=True, background_color=(0.3, 0.3, 0.3, 1), size_hint_y=0.1)
            self.btn_back.bind(on_press=self.go_back)
            layout.add_widget(self.btn_back)
            layout.add_widget(BoxLayout(size_hint_y=0.02)) # мінімальний відступ
            self.add_widget(layout)
            
        def on_enter(self):
            self.title_label.text = get_t("inst_title")
            self.btn_back.text = get_t("back")
            self.text_label.text = get_t("inst_text")
            
        def go_back(self, instance):
            self.manager.current = 'settings'

    class AntiLostApp(App):
        def build(self):
            if platform == "android":
                from android.permissions import request_permissions, Permission
                request_permissions([
                    Permission.BLUETOOTH,
                    Permission.BLUETOOTH_ADMIN,
                    Permission.BLUETOOTH_SCAN,
                    Permission.BLUETOOTH_CONNECT,
                    Permission.ACCESS_FINE_LOCATION,
                    Permission.ACCESS_COARSE_LOCATION,
                    Permission.READ_EXTERNAL_STORAGE,  
                    Permission.READ_MEDIA_AUDIO,
                    Permission.VIBRATE,
                    'android.permission.ACCESS_WIFI_STATE',
                    'android.permission.ACCESS_NETWORK_STATE'
                ])

            self.title = "VetTrack Anti-Lost"
            sm = ScreenManager()
            sm.add_widget(MainScreen(name='main'))
            sm.add_widget(SettingsScreen(name='settings'))
            sm.add_widget(FindScreen(name='find_device'))
            sm.add_widget(WifiFindScreen(name='find_wifi'))
            sm.add_widget(InstructionScreen(name='instruction'))
            return sm

    if __name__ == "__main__":
        AntiLostApp().run()

except Exception as e:
    from kivy.app import App
    from kivy.uix.label import Label
    from kivy.uix.scrollview import ScrollView
    from kivy.core.window import Window

    class ErrorApp(App):
        def build(self):
            sv = ScrollView()
            error_text = traceback.format_exc()
            lbl = Label(
                text=f"FATAL ERROR:\n\n{error_text}", 
                text_size=(Window.width * 0.9, None), 
                size_hint_y=None, 
                color=(1, 0.2, 0.2, 1),
                valign='top'
            )
            lbl.bind(texture_size=lbl.setter('size'))
            sv.add_widget(lbl)
            return sv

    ErrorApp().run()
