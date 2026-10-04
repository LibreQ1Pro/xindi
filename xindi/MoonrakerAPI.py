"""Port of src/MoonrakerAPI.cpp / include/MoonrakerAPI.h

Builders for the Moonraker JSON-RPC requests (https://moonraker.readthedocs.io).
"""

from . import state as g
from .cpp import json_dump, json_parse
from .MakerbaseCommand import method2command, method2id

# JSON message used by the makerbase client to identify the connection
STRING_IDENTIFY_CONNECTION = "{\"jsonrpc\":\"2.0\",\"method\":\"server.connection.identify\",\"params\":{\"client_name\":\"makerbase-client\",\"version\":\"0.0.1\",\"type\":\"web\",\"url\":\"http://makerbase.com/test\"},\"id\":4656}"
STRING_GET_KLIPPY_HOST_INFORMATION = "{\"jsonrpc\":\"2.0\",\"method\":\"printer.info\",\"id\":5445}"


def string2json(response):
    return json_parse(response)


def create_json_without_params(cmd):
    g.response_type_id = cmd
    api = {}
    api["jsonrpc"] = "2.0"
    api["method"] = method2command.get(cmd, "")
    api["id"] = method2id.get(cmd, 0)
    return json_dump(api)


def create_json(cmd, params):
    g.response_type_id = cmd
    api = {}
    api["jsonrpc"] = "2.0"
    api["method"] = method2command.get(cmd, "")
    api["params"] = params
    api["id"] = method2id.get(cmd, 0)
    return json_dump(api)


def json_get_klippy_host_information():
    return create_json_without_params(0x03)


def json_emergency_stop():
    return create_json_without_params(0x04)


def json_host_restart():
    return create_json_without_params(0x05)


def json_firmware_restart():
    return create_json_without_params(0x06)


def json_list_available_printer_objects():
    return create_json_without_params(0x11)


def json_query_printer_object_status(objects):
    params = {}
    params["objects"] = objects
    return create_json(0x12, params)


def json_subscribe_to_printer_object_status(objects):
    params = {}
    params["objects"] = objects
    return create_json(0x13, params)


def json_query_endstops():
    return create_json_without_params(0x14)


def json_query_server_info():
    return create_json_without_params(0x15)


def json_get_server_configuration():
    return create_json_without_params(0x16)


def json_request_cached_temperature_data():
    return create_json_without_params(0x17)


def json_request_cached_gcode_responses(count):
    params = {}
    params["count"] = count
    return create_json(0x18, params)


def json_restart_server():
    return create_json_without_params(0x19)


# GCode APIs
def json_run_a_gcode(script):
    params = {}
    params["script"] = script
    return create_json(0x21, params)


def json_get_gcode_help():
    return create_json_without_params(0x22)


# Print Management
def json_print_a_file(filename):
    params = {}
    params["filename"] = filename
    return create_json(0x31, params)


def json_pause_a_print():
    return create_json_without_params(0x32)


def json_resume_a_print():
    return create_json_without_params(0x33)


def json_cancel_a_print():
    return create_json_without_params(0x34)


# Machine Commands
def json_get_system_info():
    return create_json_without_params(0x41)


def json_shutdown_the_operating_system():
    return create_json_without_params(0x42)


def json_reboot_the_operating_system():
    return create_json_without_params(0x43)


def json_restart_a_system_service(name):
    params = {}
    params["service"] = name
    return create_json(0x44, params)


def json_stop_a_system_service(name):
    params = {}
    params["service"] = name
    return create_json(0x45, params)


def json_start_a_system_service(name):
    params = {}
    params["service"] = name
    return create_json(0x46, params)


def json_get_moonraker_process_stats():
    return create_json_without_params(0x47)


# File Operations
def json_list_available_files():
    return create_json_without_params(0x51)


def json_get_gcode_metadata(filename):
    params = {}
    params["filename"] = filename
    return create_json(0x52, params)


def json_get_directory_information(extended):
    params = {}
    params["extended"] = bool(extended)
    return create_json(0x53, params)


def json_create_directory(path):
    params = {}
    params["path"] = path
    return create_json(0x54, params)


def json_delete_directory(path, force):
    params = {}
    params["path"] = path
    params["force"] = bool(force)
    return create_json(0x55, params)


def json_move_a_file_or_directory(source, dest):
    params = {}
    params["source"] = source
    params["dest"] = dest
    return create_json(0x56, params)


def json_copy_a_file_or_directory(source, dest):
    params = {}
    params["source"] = source
    params["dest"] = dest
    return create_json(0x57, params)


def json_file_delete(path):
    # path: {root}/{filename}
    params = {}
    params["path"] = path
    return create_json(0x5a, params)


# Database APIs
def json_list_namespaces():
    return create_json_without_params(0x71)


def json_get_database_item(nsp, key):
    params = {}
    params["namespace"] = nsp
    params["key"] = key
    return create_json(0x72, params)


def json_add_database_item(nsp, key, value):
    params = {}
    params["namespace"] = nsp
    params["key"] = key
    params["value"] = value
    return create_json(0x73, params)


def json_delete_database_item(nsp, key):
    params = {}
    params["namespace"] = nsp
    params["key"] = key
    return create_json(0x74, params)


# Job Queue APIs
def json_retrieve_the_job_queue_status():
    return create_json_without_params(0x81)


def json_enqueue_a_job(filenames):
    params = {}
    params["filenames"] = list(filenames)
    return create_json(0x82, params)


def json_remove_a_job(job_ids):
    params = {}
    params["job_ids"] = list(job_ids)
    return create_json(0x83, params)


def json_pause_the_job_queue():
    return create_json_without_params(0x84)


def json_start_the_job_queue():
    return create_json_without_params(0x85)


# Announcement APIs
def json_list_announcements(incluede_dismissed):
    params = {}
    params["include_dismissed"] = bool(incluede_dismissed)
    return create_json(0x86, params)


def json_update_announcements():
    return create_json_without_params(0x87)


def json_dismiss_an_announcement(entry_id, wake_time):
    params = {}
    params["entry_id"] = entry_id
    params["wake_time"] = wake_time
    return create_json(0x88, params)


def json_list_announcement_feeds():
    return create_json_without_params(0x89)


def json_add_an_announcement_feed(name):
    params = {}
    params["name"] = name
    return create_json(0x8a, params)


def json_remove_an_announcement_feed(name):
    params = {}
    params["name"] = name
    return create_json(0x8b, params)


# Webcam APIs
def json_list_webcams():
    return create_json_without_params(0x101)


def json_get_webcam_information(name):
    params = {}
    params["name"] = name
    return create_json(0x102, params)


def json_add_or_update_a_webcam(name):
    params = {}
    params["name"] = name
    params["snapshot_url"] = "/webcam?action=snapshot"
    params["stream_url"] = "/webcam?action=stream"
    return create_json(0x103, params)


def json_delete_a_webcam(name):
    params = {}
    params["name"] = name
    return create_json(0x104, params)


def json_test_a_webcam(name):
    params = {}
    params["name"] = name
    return create_json(0x105, params)


# Update Manager APIs
def json_get_update_status(refresh):
    params = {}
    params["refresh"] = bool(refresh)
    return create_json(0x91, params)


# Perform a full update
def json_perform_a_full_update():
    return create_json_without_params(0x90)


def json_update_moonraker():
    return create_json_without_params(0x92)


def json_update_klipper():
    return create_json_without_params(0x93)


def json_update_client(name):
    params = {}
    params["name"] = name
    return create_json(0x94, params)


def json_update_system_packages():
    return create_json_without_params(0x95)


def json_recover_a_corrupt_repo(name, hard):
    params = {}
    params["name"] = name
    params["hard"] = bool(hard)
    return create_json(0x96, params)


# Power APIs
def json_get_device_list():
    return create_json_without_params(0xa1)


def json_get_device_status(device):
    params = {}
    params["device"] = device
    return create_json(0xa2, params)


def json_get_device_state(device, action):
    params = {}
    params["device"] = device
    params["action"] = action
    return create_json(0xa3, params)


# WLED APIs
def json_get_strips():
    return create_json_without_params(0xb1)


def json_get_strip_status():
    params = {}
    params["lights"] = None
    params["desk"] = None
    return create_json(0xb2, params)


def json_turn_strip_on():
    params = {}
    params["lights"] = None
    params["desk"] = None
    return create_json(0xb3, params)


def json_turn_strip_off():
    params = {}
    params["lights"] = None
    params["desk"] = None
    return create_json(0xb4, params)


def json_toggle_strip_on_off_state():
    params = {}
    params["lights"] = None
    params["desk"] = None
    return create_json(0xb5, params)


def json_get_job_totals():
    return create_json_without_params(0xd2)


def json_reset_totals():
    return create_json_without_params(0xd3)
