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
}


def text(key, lang):
    """The text ``key`` in the screen language ``lang`` (English for an unknown code)."""
    row = TEXT[key]
    return row[lang] if 0 <= lang < len(row) else row[DEFAULT]
