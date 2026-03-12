"""Constants for the mega integration."""
import re
from itertools import permutations

from homeassistant.const import Platform

DOMAIN = "mega"

# Mega IDs and addressing
CONF_MEGA_ID = "mega_id"
CONF_ADDR = "addr"
CONF_ID = "id"  # Добавлено для совместимости
CONF_UNIQUE_ID = "unique_id"  # Добавлено для совместимости

# Port and device configuration
CONF_PORT = "port"  # Добавлено для совместимости
CONF_PORTS = "ports"
CONF_DOMAIN = "domain"  # <-- ВАЖНО: добавлена недостающая константа
CONF_DIMMER = "dimmer"
CONF_SWITCH = "switch"
CONF_LED = "led"
CONF_WS28XX = "ws28xx"
CONF_ORDER = "order"
CONF_SMOOTH = "smooth"
CONF_WHITE_SEP = "white_sep"
CONF_CHIP = "chip"
CONF_RANGE = "range"
CONF_INVERT = "invert"
CONF_SKIP = "skip"
CONF_KEY = "key"

# Sensor types
TEMP = "temp"
HUM = "hum"
W1 = "w1"
W1BUS = "w1bus"
LUX = "lux"

# Button events
LONG = "long"
RELEASE = "release"
LONG_RELEASE = "long_release"
PRESS = "press"
SINGLE_CLICK = "single"
DOUBLE_CLICK = "double"
CONF_CLICK_TIME = "click_time"
CONF_LONG_TIME = "long_time"

# Scanning and polling
CONF_PORT_TO_SCAN = "port_to_scan"
CONF_NPORTS = "nports"
CONF_POLL_OUTS = "poll_outs"
CONF_UPDATE_ALL = "update_all"
CONF_UPDATE_TIME = "update_time"
CONF_GET_VALUE = "get_value"
CONF_FORCE_D = "force_d"
CONF_FORCE_I2C_SCAN = "force_i2c_scan"

# Templates and formatting
CONF_RESPONSE_TEMPLATE = "response_template"
CONF_CONV_TEMPLATE = "conv_template"
CONF_DEF_RESPONSE = "def_response"
CONF_HEX_TO_FLOAT = "hex_to_float"
CONF_FILL_NA = "fill_na"

# Filtering
CONF_FILTER_VALUES = "filter_values"
CONF_FILTER_SCALE = "filter_scale"
CONF_FILTER_LOW = "filter_low"
CONF_FILTER_HIGH = "filter_high"

# Network and communication
CONF_ALLOW_HOSTS = "allow_hosts"
CONF_PROTECTED = "protected"
CONF_FAKE_RESPONSE = "fake_response"
CONF_MQTT_INPUTS = "mqtt_inputs"
CONF_1WBUS = "1wbus"

# System and internal
CONF_RELOAD = "reload"
CONF_RESTORE_ON_RESTART = "restore_on_restart"
CONF_ACTION = "action"
CONF_CUSTOM = "__custom"
CONF_HTTP = "__http"
CONF_ALL = "__all"

# Events
EVENT_BINARY_SENSOR = f"{DOMAIN}.sensor"
EVENT_BINARY = f"{DOMAIN}.binary"

# Platforms
PLATFORMS = [
    Platform.LIGHT,
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
]

# Regular expressions
PATT_SPLIT = re.compile("[;/]")
PATT_FW = re.compile(r"fw:\s(.+?)\)")

# RGB combinations
RGB = "rgb"
RGB_COMBINATIONS = ["".join(x) for x in permutations("rgb")]

# Configuration keys to remove during cleanup
REMOVE_CONFIG = [
    "extenders",
    "ext_in",
    "ext_acts",
    "i2c_sensors",
    "binary_sensor",
    "light",
    "i2c",
    "sensor",
    "smooth",
]