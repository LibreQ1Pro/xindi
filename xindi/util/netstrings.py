"""Texts of the network pages in every language of the screen (the index is the ``lang`` value of the screen firmware).

Both sides use this table: ``netui.py`` sends the texts that depend on the state, and
``display_firmware/tools/net_i18n.py`` writes the fixed ones into the pages of the screen project, so the two cannot
drift apart."""

LANGUAGES = ("zh", "ru", "en", "ja", "fr", "de", "it", "es", "ko", "pt", "ar", "tr", "he")
DEFAULT = 2         # English, for a language code that is not in the list

TEXT = {
    "saved_networks": ("已保存的网络", "Сохранённые сети", "Saved Networks", "保存済みネットワーク", "Réseaux enregistrés",
                       "Gespeicherte Netze", "Reti salvate", "Redes guardadas", "저장된 네트워크", "Redes salvas",
                       "الشبكات المحفوظة", "Kayıtlı ağlar", "רשתות שמורות"),
    "network": ("网络", "Сеть", "Network", "ネットワーク", "Réseau", "Netzwerk", "Rete", "Red", "네트워크", "Rede",
                "الشبكة", "Ağ", "רשת"),
    "change_password": ("修改密码", "Изменить пароль", "Change Password", "パスワード変更", "Changer le mot de passe",
                        "Passwort ändern", "Cambia password", "Cambiar contraseña", "비밀번호 변경", "Alterar senha",
                        "تغيير كلمة المرور", "Parolayı değiştir", "שינוי סיסמה"),
    "forget_network": ("忘记网络", "Забыть сеть", "Forget Network", "ネットワークを削除", "Oublier le réseau",
                       "Netzwerk entfernen", "Elimina rete", "Olvidar red", "네트워크 삭제", "Esquecer rede",
                       "نسيان الشبكة", "Ağı unut", "שכח רשת"),
    "forget": ("忘记", "Забыть", "Forget", "削除", "Oublier", "Entfernen", "Elimina", "Olvidar", "삭제", "Esquecer",
               "نسيان", "Unut", "שכח"),
    "cancel": ("取消", "Отмена", "Cancel", "キャンセル", "Annuler", "Abbrechen", "Annulla", "Cancelar", "취소",
               "Cancelar", "إلغاء", "İptal", "ביטול"),
    "network_info": ("网络信息", "Сведения о сети", "Network Info", "ネットワーク情報", "Infos réseau", "Netzwerkinfo",
                     "Info di rete", "Info de red", "네트워크 정보", "Info da rede", "معلومات الشبكة", "Ağ bilgisi",
                     "מידע על הרשת"),
    "hidden_network": ("隐藏网络", "Скрытая сеть", "Hidden Network", "非公開ネットワーク", "Réseau masqué",
                       "Verstecktes Netzwerk", "Rete nascosta", "Red oculta", "숨겨진 네트워크", "Rede oculta",
                       "شبكة مخفية", "Gizli ağ", "רשת מוסתרת"),
    # short labels of the two buttons over the list of scanned networks
    "saved_short": ("已保存", "Сохр.", "Saved", "保存済み", "Enreg.", "Gespeich.", "Salvate", "Guardadas", "저장됨",
                    "Salvas", "المحفوظة", "Kayıtlı", "שמורות"),
    "hidden_short": ("隐藏", "Скрытая", "Hidden", "非公開", "Masqué", "Versteckt", "Nascosta", "Oculta", "숨김",
                     "Oculta", "مخفية", "Gizli", "מוסתרת"),
    # the row of the general settings that turns the setup guide (the first-start walkthrough) on, hidden (5 taps on "General")
    "setup_guide": ("开机引导", "Мастер настройки", "Setup Guide", "初期設定ガイド", "Guide de démarrage",
                    "Einrichtung", "Guida iniziale", "Guía de inicio", "시작 가이드", "Guia inicial",
                    "دليل الإعداد", "Kurulum kılavuzu", "מדריך הפעלה"),
    # state of a network / interface
    "saved": ("已保存", "Сохранена", "Saved", "保存済み", "Enregistré", "Gespeichert", "Salvata", "Guardada", "저장됨",
              "Salva", "محفوظة", "Kayıtlı", "שמורה"),
    "connected": ("已连接", "Подключено", "Connected", "接続済み", "Connecté", "Verbunden", "Connesso", "Conectado",
                  "연결됨", "Conectado", "متصل", "Bağlı", "מחובר"),
    "disconnected": ("未连接", "Не подключено", "Disconnected", "未接続", "Déconnecté", "Getrennt", "Disconnesso",
                     "Desconectado", "연결 안 됨", "Desconectado", "غير متصل", "Bağlı değil", "לא מחובר"),
    "unavailable": ("不可用", "Недоступно", "Unavailable", "利用不可", "Indisponible", "Nicht verfügbar",
                    "Non disponibile", "No disponible", "사용 불가", "Indisponível", "غير متاح", "Kullanılamıyor",
                    "לא זמין"),
    "off_state": ("已关闭", "Выключено", "Off", "オフ", "Désactivé", "Aus", "Disattivato", "Desactivado", "꺼짐",
                  "Desativado", "متوقف", "Kapalı", "כבוי"),
    "no_adapter": ("无适配器", "Нет адаптера", "No adapter", "アダプターなし", "Aucun adaptateur", "Kein Adapter",
                   "Nessun adattatore", "Sin adaptador", "어댑터 없음", "Sem adaptador", "لا يوجد محول",
                   "Adaptör yok", "אין מתאם"),
    "gateway": ("网关", "Шлюз", "GW", "GW", "Passerelle", "Gateway", "GW", "GW", "게이트웨이", "GW", "البوابة",
                "GW", "שער"),
    # buttons of one network
    "connect": ("连接", "Подключиться", "Connect", "接続", "Connecter", "Verbinden", "Connetti", "Conectar", "연결",
                "Conectar", "اتصال", "Bağlan", "התחבר"),
    "disconnect": ("断开连接", "Отключиться", "Disconnect", "切断", "Déconnecter", "Trennen", "Disconnetti",
                   "Desconectar", "연결 끊기", "Desconectar", "قطع الاتصال", "Bağlantıyı kes", "התנתק"),
    "autoconnect": ("自动连接: ", "Автоподключение: ", "Autoconnect: ", "自動接続: ", "Connexion auto : ",
                    "Autoverbinden: ", "Connessione auto: ", "Conexión auto: ", "자동 연결: ", "Conexão auto: ",
                    "الاتصال التلقائي: ", "Otomatik bağlan: ", "חיבור אוטומטי: "),
    "on": ("开", "вкл", "On", "オン", "activée", "an", "attiva", "activada", "켜짐", "ligada", "تشغيل", "açık",
           "פעיל"),
    "off": ("关", "выкл", "Off", "オフ", "désactivée", "aus", "disattiva", "desactivada", "꺼짐", "desligada",
            "إيقاف", "kapalı", "כבוי"),
    # "forget the network" question, two lines at the end
    "saved_password": ("保存的密码", "Сохранённый пароль", "The saved password", "保存されたパスワードは",
                       "Le mot de passe enregistré", "Das gespeicherte Passwort", "La password salvata",
                       "La contraseña guardada", "저장된 비밀번호가", "A senha salva", "سيتم حذف",
                       "Kayıtlı parola", "הסיסמה השמורה"),
    "will_be_deleted": ("将被删除。", "будет удалён.", "will be deleted.", "削除されます。", "sera supprimé.",
                        "wird gelöscht.", "verrà eliminata.", "se eliminará.", "삭제됩니다.", "será excluída.",
                        "كلمة المرور المحفوظة.", "silinecek.", "תימחק."),
    # title of the keyboard page while the name of a hidden network is typed
    "network_name": ("网络名称 (SSID)", "Имя сети (SSID)", "Network name (SSID)", "ネットワーク名 (SSID)",
                     "Nom du réseau (SSID)", "Netzwerkname (SSID)", "Nome rete (SSID)", "Nombre de red (SSID)",
                     "네트워크 이름 (SSID)", "Nome da rede (SSID)", "اسم الشبكة (SSID)", "Ağ adı (SSID)",
                     "שם הרשת (SSID)"),
    # label of the brightness slider on the screen sleep page
    "brightness": ("亮度", "Яркость", "Brightness", "明るさ", "Luminosité", "Helligkeit", "Luminosità", "Brillo",
                   "밝기", "Brilho", "السطوع", "Parlaklık", "בהירות"),
    # pages shown while the printer shuts down, restarts after a failure and boots (they have no host text)
    "shutting_down": ("正在关机", "Выключение", "SHUTTING DOWN", "シャットダウン中", "ARRÊT EN COURS", "WIRD HERUNTERGEFAHREN", "ARRESTO IN CORSO", "APAGANDO", "종료 중", "DESLIGANDO", "جارٍ إيقاف التشغيل", "KAPANIYOR", "מכבה"),
    "system_abnormal": ("系统启动异常！", "Система запустилась с ошибкой!", "THE SYSTEM STARTS ABNORMALLY !", "システムが正常に起動しませんでした！", "Le système a démarré anormalement !", "Das System ist nicht normal gestartet!", "Il sistema si è avviato in modo anomalo!", "¡El sistema se ha iniciado de forma anómala!", "시스템이 비정상적으로 시작되었습니다!", "O sistema iniciou de forma anormal!", "بدأ تشغيل النظام بشكل غير طبيعي!", "Sistem olağandışı başladı!", "המערכת הופעלה באופן חריג!"),
    "restart_hint": ("请关闭机器，稍等片刻后再重新启动。", "Выключите принтер, немного подождите и включите его снова.", "Please turn off the machine and wait for a while before restarting", "本体の電源を切り、しばらく待ってから再起動してください。", "Éteignez la machine et patientez un moment avant de la redémarrer.", "Schalten Sie das Gerät aus und warten Sie einen Moment, bevor Sie es neu starten.", "Spegni la macchina e attendi un po' prima di riavviarla.", "Apague la máquina y espere un momento antes de reiniciarla.", "기기를 끄고 잠시 기다린 후 다시 시작하세요.", "Desligue a máquina e aguarde um momento antes de reiniciar.", "يرجى إيقاف تشغيل الجهاز والانتظار قليلاً قبل إعادة التشغيل.", "Lütfen makineyi kapatın ve yeniden başlatmadan önce biraz bekleyin.", "כבה את המכונה והמתן מעט לפני שתפעיל אותה מחדש."),
    "booting_up": ("正在启动，请稍候……", "Загрузка, подождите…", "BOOTING UP, PLEASE WAIT......", "起動中です。しばらくお待ちください…", "Démarrage, veuillez patienter…", "Startvorgang läuft, bitte warten…", "Avvio in corso, attendere…", "Iniciando, espere…", "부팅 중입니다. 잠시만 기다려 주세요…", "Iniciando, aguarde…", "جارٍ التشغيل، يرجى الانتظار…", "Başlatılıyor, lütfen bekleyin…", "מאתחל, אנא המתן…"),
    # the buttons of the Klipper status page that restart Klipper / the firmware
    "restart_klipper": ("重启 Klipper", "Перезапуск Klipper", "Restart Klipper", "Klipperを再起動", "Redémarrer Klipper", "Klipper neu starten", "Riavvia Klipper", "Reiniciar Klipper", "Klipper 재시작", "Reiniciar o Klipper", "إعادة تشغيل Klipper", "Klipper'ı yeniden başlat", "הפעל מחדש את Klipper"),
    "restart_firmware": ("重启固件", "Перезапуск прошивки", "Restart Firmware", "ファームウェアを再起動", "Redémarrer le firmware", "Firmware neu starten", "Riavvia il firmware", "Reiniciar el firmware", "펌웨어 재시작", "Reiniciar o firmware", "إعادة تشغيل البرنامج الثابت", "Yazılımı yeniden başlat", "הפעל מחדש את הקושחה"),
}


def text(key, lang):
    """The text ``key`` in the screen language ``lang`` (English for an unknown code)."""
    row = TEXT[key]
    return row[lang] if 0 <= lang < len(row) else row[DEFAULT]
