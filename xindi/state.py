"""
Global state of the program.

The C++ code keeps almost all of its state in global variables which are
shared between translation units with ``extern`` declarations.  To keep the
port a faithful transliteration, all of those globals live in this single
module and the ported code accesses them as ``g.<name>`` (``from . import
state as g``).  Variables are grouped by the C++ file that defines them and
keep their original names and initial values (C++ zero-initialises globals
without an explicit initialiser).
"""


class Struct(object):
    """Plain C struct replacement."""

    def __init__(self, **fields):
        self.__dict__.update(fields)

    def __repr__(self):
        return "Struct(%r)" % self.__dict__


def mks_wifi_status_result_t():
    """struct mks_wifi_status_result_t (mks_wpa_cli.h) as filled from NetworkManager; char arrays become str."""
    return Struct(ack="", bssid="", freq=0, ssid="", id=0, mode="", pairwise_cipher="",
                  group_cipher="", key_mgmt="", wpa_state="", ip_address="", address="", uuid="")


# ---------------------------------------------------------------------------
# main.cpp
# ---------------------------------------------------------------------------
ep = None                               # MakerbaseClient *ep
is_download_to_screen = False
find_screen_tft_file = False

# ---------------------------------------------------------------------------
# ui.cpp
# ---------------------------------------------------------------------------
tty_fd = -1

current_page_id = 0                     # id of the page currently shown
previous_page_id = 0                    # id of the previous page
next_page_id = 0                        # id of the next page

event_id = 0
page_id = 0
widget_id = 0
type_id = 0

level_mode = 0                          # levelling mode

show_preview_complete = False
show_preview_gimage_completed = False

printing_keyboard_enabled = False
auto_level_button_enabled = True
manual_level_button_enabled = True

printing_wifi_keyboard_enabled = False

# levelling while printing
level_mode_printing_extruder_target = 0
level_mode_printing_heater_bed_target = 0

level_mode_printing_is_printing_level = False

# NOTE: declared as bool[3] in ui.cpp but indexes 0..4 are used by the code
# (out of bounds writes in C++).  Five entries are used here.
page_wifi_list_ssid_button_enabled = [False, False, False, False, False]

# page print filament
page_print_filament_extrude_restract_button = False
page_filament_extrude_button = False

page_filament_unload_button = False

printer_bed_leveling = True

# 4.4.1 CLL "do not show again" button on the filament confirmation pop-ups
preview_pop_1_on = True
preview_pop_2_on = True

# 4.4.2 CLL screen sleep feature
previous_caselight_value = False

# 4.4.2 CLL local / USB buttons on the file list page
file_mode = "Local"

manual_count = 0

adjust_mode = "Filament"                # decides which page the "adjust" button opens
set_mode = "Level_mode"                 # decides which page the "settings" button opens

move_fan_setting = False                # True while the fan slider is being dragged
load_target = 0

load_mode = False                       # True: loading filament, False: unloading

qr_refreshed = False                    # QR code needs to be regenerated only after wifi / connection / server changes

# 4.4.22 (from the binary)
printer_muted = False                   # silent mode: print speed 50%, reset when a print starts
timelapse_enabled = False               # state of Moonraker's timelapse plugin, shown on the preview page
file_list_refreshed = False             # the file list (and its pictures) is up to date: keep the position

# ---------------------------------------------------------------------------
# event.cpp
# ---------------------------------------------------------------------------
current_speed_factor = 0.0
current_extruder_factor = 0.0
current_extruder_temperature = 0
current_extruder_target = 0
current_heater_bed_temperature = 0
current_heater_bed_target = 0
current_hot_temperature = 0
current_hot_target = 0
current_out_pin_fan0_value = 0.0
current_out_pin_fan3_value = 0.0
current_out_pin_fan2_value = 0.0

str_manual_level_offset = ""

# compensation value
page_set_zoffset_number = 0.0

# input shaping results
page_syntony_shaper_freq_x = ""
page_syntony_shaper_freq_y = ""
page_syntony_finished = False

# PID tuning
page_pid_finished = False

wifi_ip_address = ""

# power off after the print
page_printing_shutdown_enable = False

page_about_successed = False

# 800 hours
mks_total_printed_minutes = 0

# wifi
current_connected_ssid_name = ""

# out-of-box experience (first start guide)
mks_oobe_enabled = False
current_mks_oobe_enabled = False

# levelling
start_pre_auto_level = False
start_pre_manual_level = False

all_level_saving = False

# "saving" page
is_refresh_page_saving = False

temp_idle_state = ""

jump_to_print = False

printer_auto_level_heater_bed_target = 0

printer_ready = False

# 4.4.1 CLL fix conflict between filament runout detection and unloading
previous_filament_sensor_state = False

# 4.4.1 CLL levelling changes
previous_zoffset = ""

# 4.4.2 CLL levelling no longer needs manual z-offset
step_1 = False
step_2 = False
step_3 = False
step_4 = False

# 4.4.2 CLL support for the hall effect filament width sensor
filament_detected = True

bed_offset = 0.0

unhomed_move_mode = 0   # last move button pressed (used when homing is required): 1 x+, 2 x-, 3 y+, 4 y-, 5 z+, 6 z-

# These flags fix conflicts between the gcode response handler and the refresh
# functions: the gcode handler only sets a flag and refresh_page_show() changes
# the page.
jump_to_move_pop_1 = False
jump_to_move_pop_2 = False
jump_to_detect_error = False
jump_to_level_error = False
jump_to_filament_pop_1 = False
jump_to_print_low_temp = False
jump_to_memory_warning = False
jump_to_resume_print = False

error_message = ""

main_picture_detected = False   # whether the picture of the cached file exists
main_picture_refreshed = False  # whether the picture on the main page was already refreshed

connection_method = 0           # 0: LAN connection, 1: internet connection (QR code)

serverConfigs = {}              # std::map<int, Server_config>
selected_server = ""

current_server_page = 0
total_server_count = 0
target_soc_version = ""

open_qr_refreshed = False       # first refresh after boot doesn't regenerate the QR picture
open_reprint_asked = False      # ask for power loss recovery once after entering the main page

mks_ethernet = 0

input_path = ""
input_size = 0
start_path = False

# ---------------------------------------------------------------------------
# mks_printer.cpp
# ---------------------------------------------------------------------------
# mks ini data
mks_led_status = False
mks_beep_status = False
mks_fila_status = False
mks_language_status = 0
mks_extruder_target = 0
mks_heater_bed_target = 0
mks_hot_target = 0
mks_babystep_value = ""
mks_adxl_offset = ""
mks_version_soc = ""
mks_version_mcu = ""
mks_version_ui = ""

# webhooks
printer_webhooks_state = ""
printer_webhooks_state_message = ""
current_webhooks_state_message = ""

# gcode_move
printer_gcode_move_speed_factor = 0.0
printer_gcode_move_speed = 0.0
printer_gcode_move_extrude_factor = 0.0
printer_gcode_move_homing_origin = [0.0, 0.0, 0.0, 0.0]     # [X, Y, Z, E] gcode offsets (Z shows babystepping)
printer_gcode_move_position = [0.0, 0.0, 0.0, 0.0]
printer_gcode_move_gcode_position = [0.0, 0.0, 0.0, 0.0]

# toolhead
printer_toolhead_homed_axes = ""
printer_toolhead_print_time = 0.0
printer_toolhead_extimated_print_time = 0.0
printer_toolhead_position = [0.0, 0.0, 0.0, 0.0]
printer_toolhead_axis_minimum = [0.0, 0.0, 0.0, 0.0]
printer_toolhead_axis_maximum = [0.0, 0.0, 0.0, 0.0]

# x, y, z coordinates
x_position = 0.0
y_position = 0.0
z_position = 0.0
# gcode z coordinate
gcode_z_position = 0.0

e_position = 0.0

# extruder
printer_extruder_temperature = 0
printer_extruder_target = 0

# heater bed
printer_heater_bed_temperature = 0
printer_heater_bed_target = 0

# chamber ("hot")
printer_hot_temperature = 0
printer_hot_target = 0

# fan
printer_fan_speed = 0.0

# heater fan
printer_heater_fan_speed = 0.0

# heater_fan my_nozzle_fan1
printer_heater_fan_my_nozzle_fan1_speed = 0.0

# output_pin fan0
printer_out_pin_fan0_value = 0.0

# output_pin fan2
printer_out_pin_fan2_value = 0.0

printer_out_pin_fan3_value = 0.0

printer_out_pin_beep_value = 0.0

# idle_timeout
printer_idle_timeout_state = ""
printer_printing_time = 0.0

# print stats
printer_print_stats_filename = ""
printer_print_stats_total_duration = 0.0
printer_print_stats_print_duration = 0.0
printer_print_stats_filament_used = 0.0
printer_print_stats_state = ""          # this state is very useful
printer_print_stats_message = ""        # error detected, error message

# display status
printer_display_status_message = ""
printer_display_status_progress = 0

# bed_mesh
auto_level_dist = 0.05000000074505806   # float 0.05
auto_level_finished = False
auto_level_enabled = False

manual_level_dist = 0.05000000074505806  # float 0.05
manual_level_count = 15
manual_level_finished = False

printer_bed_mesh_mesh_min = [0.0, 0.0]
printer_bed_mesh_mesh_max = [0.0, 0.0]
printer_bed_mesh_profiles_mks_points = [[0.0] * 5 for _ in range(5)]
printer_bed_mesh_profiles_mks_mesh_params_tension = 0.0
printer_bed_mesh_profiles_mks_mesh_params_mesh_x_pps = 0.0
printer_bed_mesh_profiles_mks_mesh_params_algo = ""
printer_bed_mesh_profiles_mks_mesh_params_min_x = 0.0
printer_bed_mesh_profiles_mks_mesh_params_min_y = 0.0
printer_bed_mesh_profiles_mks_mesh_params_x_count = 0.0
printer_bed_mesh_profiles_mks_mesh_params_y_count = 0.0
printer_bed_mesh_profiles_mks_mesh_params_mesh_y_pps = 0.0
printer_bed_mesh_profiles_mks_mesh_params_max_x = 0.0
printer_bed_mesh_profiles_mks_mesh_params_max_y = 0.0

page_set_zoffset_x_y_position = [
    [30, 30],               # 1
    [30, 93.33],            # 2
    [30, 156.66],           # 3
    [30, 219.99],           # 4
    [93.33, 30],            # 5
    [93.33, 93.33],         # 6
    [93.33, 156.66],        # 7
    [93.33, 219.99],        # 8
    [156.66, 30],           # 9
    [156.66, 93.33],        # 10
    [156.66, 156.66],       # 11
    [156.66, 219.99],       # 12
    [219.99, 30],           # 13
    [219.99, 93.33],        # 14
    [219.99, 156.66],       # 15
    [219.99, 219.99],       # 16
]

page_set_zoffset_z_position = [0.0] * 16

fresh_page_set_zoffset_data = False
refresh_page_auto_finish_data = False
page_set_zoffset_index = 0

# pause resume
printer_pause_taget = 0

printer_pause_resume_is_paused = False

printer_set_offset = 0.009999999776482582       # float 0.01
printer_z_offset = 0.0
printer_intern_z_offset = 0.0
printer_extern_z_offset = 0.0

printer_move_dist = 10.0
printer_filament_extruder_target = 0
printer_filament_extruedr_dist = 50

# filament switch sensor fila
filament_switch_sensor_fila_filament_detected = False
filament_switch_sensor_fila_enabled = False

# output_pin caselight
printer_caselight_value = 0.0

# probe
printer_probe_x_zoffset = 0.0
printer_probe_y_zoffset = 0.0
printer_probe_z_zoffset = 0.0

# printer info software version
printer_info_software_version = ""

# server history totals
total_jobs = 0
total_time = 0.0
total_print_time = 0.0
total_filament_used = 0.0

# oobe
oobe_printer_set_offset = 0.05000000074505806   # float 0.05

# ---------------------------------------------------------------------------
# mks_file.cpp
# ---------------------------------------------------------------------------
# Python only: the ColPic text of the last converted picture.  The original
# writes it to /home/mks/tjc (gene4.py) and reads the file back; the port keeps
# it in memory.  None = "the file does not exist" (nothing converted yet).
tjc_data = None
# Get gcode metadata
file_filename = ""                      # file name
file_current_filename = ""              # current file name
file_previous_filename = ""             # previous file name

file_filament_total = 0.0               # filament usage
file_estimated_time = 0.0               # estimated print time

# Directory
file_path_stack = []                    # path stack
file_root_path = ""                     # gcodes root directory
file_previous_path = ""                 # previous path
file_current_path = ""                  # path of the current file
file_print_path = ""                    # path of the file to print

# file management (std::set<std::string>; kept as Python sets, iterated sorted)
server_files_list = set()               # gcode file list
server_files_get_directroy = set()      # directories below the path

newfiles = set()
deletedfiles = set()
updatedfiles = set()

page_files_dirname_list = set()
page_files_filename_list = set()
page_files_dirname_filename_list = set()

page_files_last_printing_files_dir = ""

page_files_is_last_print_files_dir = False

# file list page
filelist_changed = False

page_files_pages = 0
page_files_current_pages = 0
page_files_folder_layers = 0

page_files_list_name = ["", "", "", "", "", "", "", "", ""]                     # file names shown in the list
page_files_list_show_name = ["", "", "", "", "", "", "", "", ""]                # file list names
page_files_list_show_type = ["[n]", "[n]", "[n]", "[n]", "[n]", "[n]", "[n]", "[n]", "[n]"]   # entry type: [f], [d], [c] or [n]

page_files_refresh_status = False

page_files_path_stack = []              # path stack (std::stack, top == last element)
page_files_root_path = ""               # Klippy root directory
page_files_previous_path = ""           # previous path
page_files_path = ""                    # path of the files
page_files_print_files_path = ""        # path of the file to print

file_metadata_estimated_time = 0
file_metadata_filename = ""
file_metadata_filament_total = 0.0
file_metadata_object_height = 0
file_metadata_filament_name = ""
file_metadata_filament_type = ""

file_metadata_filament_weight_total = 0.0
file_metadata_gimage = ""
file_metadata_simage = ""
mks_file_parse_finished = False

thumbnail_relative_path = ""
thumbnail_path = ""

cache_clicked = False

# ---------------------------------------------------------------------------
# mks_gcode.cpp
# ---------------------------------------------------------------------------
filament_message = ""

# 4.4.3 CLL web print information subscription
output_metadata = None

# ---------------------------------------------------------------------------
# MakerbaseParseMessage.cpp
# ---------------------------------------------------------------------------
get_status_flag = False

message = ""
is_get_message = False
# Python only: the websocket thread queues the messages, json_parse() takes
# them one by one (the original keeps only the last one in `message`, so a
# message that arrives while the previous one is parsed is lost)
import queue as _queue
message_queue = _queue.Queue()
response_type_id = 0
response = None
res = None

# ---------------------------------------------------------------------------
# network.py (NetworkManager)
# ---------------------------------------------------------------------------
wlan_state_str = ""

# ---------------------------------------------------------------------------
# MakerbaseWiFi.cpp
# ---------------------------------------------------------------------------
status_result = mks_wifi_status_result_t()
ssid_list = []
level_list = []
page_wifi_ssid_list = ["", "", "", "", ""]
page_wifi_ssid_list_pages = 0
page_wifi_current_pages = 0
get_wifi_name = ""

# ---------------------------------------------------------------------------
# mks_update.cpp
# ---------------------------------------------------------------------------
copy_fd = 0

detected_soc_data = False
detected_mcu_data = False
detected_ui_data = False
# CLL detection of Q1 SOC and UI updates
detected_q1_soc_data = False
detected_q1_ui_data = False
# CCW 4.4.14 detection of Q1 patch packages
detected_q1_patch_data = False
# base_path: mks_update._base_path() (the gcode directory is found at run time)

detected_printer_cfg = False
detected_gcode_cfg = False
detected_MKS_THR_cfg = False

detected_gcode = False

# 4.4.3 CLL updates from .deb files
detected_soc_deb = False

tft_buff = 4096
tft_start = 0
tft_end = 0
tft_s = b""
tft_data = b""
tft_len = 0
filesize = 0

tft_index = 0

# ---------------------------------------------------------------------------
# send_jpg.cpp
# ---------------------------------------------------------------------------
get_0xfe = False
get_0x06 = False
get_0x05 = False
get_0xfd = False
get_0x04 = False
get_0x24 = False

have_64_jpg = [False] * 6
have_64_png_path = [""] * 6
begin_show_64_jpg = False
send_jpg_status = False                 # 4.4.22: pictures being sent, refresh_page_show() waits
begin_show_160_jpg = False
begin_show_192_jpg = False
show_192_jpg_complete = True
jpg_160_path = ""

sent_jpg_to_tjc_start_time = 0          # "static int start_time" inside sent_jpg_to_tjc()

# ---------------------------------------------------------------------------
# mks_preview.cpp
# ---------------------------------------------------------------------------
gimage_is_showed = False
simage_is_showed = False

# ---------------------------------------------------------------------------
# mks_init.cpp
# ---------------------------------------------------------------------------
serial_by_id = ""

# ---------------------------------------------------------------------------
# MakerbaseParseIni.cpp
# ---------------------------------------------------------------------------
mksini = None
printer_cfg = None
mksversion = None
