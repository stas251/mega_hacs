"""Platform for light integration."""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta
from functools import partial

import colorsys
import voluptuous as vol

from homeassistant.components.light import (
    PLATFORM_SCHEMA as LIGHT_SCHEMA,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ID, CONF_NAME, CONF_PORT, CONF_UNIQUE_ID
from homeassistant.core import HomeAssistant

from .const import (
    CONF_CHIP,
    CONF_CUSTOM,
    CONF_DIMMER,
    CONF_DOMAIN,
    CONF_LED,
    CONF_ORDER,
    CONF_PORTS,
    CONF_SKIP,
    CONF_SMOOTH,
    CONF_SWITCH,
    CONF_WHITE_SEP,
    CONF_WS28XX,
    DOMAIN,
    RGB,
)
from .entities import BaseMegaEntity, MegaOutPort, safe_int
from .hub import MegaD
from .tools import int_ignore, map_reorder_rgb

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=5)

# Validation of the user's configuration
_EXTENDED = {
    vol.Required(CONF_PORT): int,
    vol.Optional(CONF_NAME): str,
    vol.Optional(CONF_UNIQUE_ID): str,
}
_ITEM = vol.Any(int, _EXTENDED)
DIMMER = {vol.Required(CONF_DIMMER): [_ITEM]}
SWITCH = {vol.Required(CONF_SWITCH): [_ITEM]}
PLATFORM_SCHEMA = LIGHT_SCHEMA.extend(
    {
        vol.Optional(str, description="mega id"): {
            vol.Optional("dimmer", default=[]): [_ITEM],
            vol.Optional("switch", default=[]): [_ITEM],
        }
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the light platform from YAML."""
    _LOGGER.warning(
        "mega integration does not support yaml for lights, please use UI configuration"
    )
    return True


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_devices
):
    """Set up lights from config entry."""
    mid = config_entry.data[CONF_ID]
    hub: MegaD = hass.data["mega"][mid]
    devices = []
    customize = hass.data.get(DOMAIN, {}).get(CONF_CUSTOM, {}).get(mid, {})
    skip = []
    
    # Setup LED strips
    if CONF_LED in customize:
        for entity_id, conf in customize[CONF_LED].items():
            ports = conf.get(CONF_PORTS) or [conf.get(CONF_PORT)]
            skip.extend(ports)
            devices.append(
                MegaRGBW(
                    mega=hub,
                    port=ports,
                    name=entity_id,
                    customize=conf,
                    id_suffix=entity_id,
                    config_entry=config_entry,
                )
            )
    
    # Setup regular lights
    for port, cfg in config_entry.data.get("light", {}).items():
        port = int_ignore(port)
        c = customize.get(port, {})
        if (
            c.get(CONF_SKIP, False)
            or port in skip
            or c.get(CONF_DOMAIN, "light") != "light"
        ):
            continue
        for data in cfg:
            hub.lg.debug(f"add light on port %s with data %s", port, data)
            light = MegaLight(
                mega=hub, port=port, config_entry=config_entry, **data
            )
            if "<" in light.name:
                continue
            devices.append(light)

    async_add_devices(devices)


class MegaLight(MegaOutPort, LightEntity):
    """Representation of a simple Mega light (on/off or dimmable)."""

    @property
    def supported_features(self) -> LightEntityFeature:
        """Flag supported features."""
        if self.dimmer:
            return LightEntityFeature.TRANSITION
        return LightEntityFeature(0)

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Return set of supported color modes."""
        if self.dimmer:
            return {ColorMode.BRIGHTNESS}
        return {ColorMode.ONOFF}

    @property
    def color_mode(self) -> ColorMode:
        """Return the current color mode."""
        if self.dimmer:
            return ColorMode.BRIGHTNESS
        return ColorMode.ONOFF


class MegaRGBW(LightEntity, BaseMegaEntity):
    """Representation of an RGB/W LED strip or RGBW light."""

    def __init__(self, *args, **kwargs):
        """Initialize an RGBW light."""
        super().__init__(*args, **kwargs)
        self._is_on = None
        self._brightness = None
        self._hs_color = None
        self._rgb_color: tuple[int, int, int] | None = None
        self._white_value = None
        self._task: asyncio.Task = None
        self._restore = None
        self.smooth: timedelta = self.customize[CONF_SMOOTH]
        self._color_order = self.customize.get(CONF_ORDER, "rgb")
        self._last_called: float = 0
        self._max_values = None

    @property
    def max_values(self) -> list:
        """Return maximum values for each channel."""
        if self._max_values is None:
            if self.is_ws:
                self._max_values = [255] * 4
            else:
                self._max_values = [
                    255 if isinstance(x, int) else 4095 for x in self.port
                ]
        return self._max_values

    @property
    def chip(self) -> int:
        """Return chip type for WS281x."""
        return self.customize.get(CONF_CHIP, 100)

    @property
    def is_ws(self) -> bool:
        """Return True if this is a WS281x LED strip."""
        return self.customize.get(CONF_WS28XX, False)

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Return set of supported color modes."""
        if len(self.port) == 4:
            return {ColorMode.RGBW}
        return {ColorMode.RGB}

    @property
    def color_mode(self) -> ColorMode:
        """Return the current color mode."""
        if len(self.port) == 4:
            return ColorMode.RGBW
        return ColorMode.RGB

    @property
    def white_value(self) -> float | None:
        """Return the white value of this light in RGBW mode."""
        return float(self.get_attribute("white_value", 0))

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the rgb color value [int, int, int]."""
        return self._rgb_color

    @property
    def rgbw_color(self) -> tuple[int, int, int, int] | None:
        """Return the rgbw color value [int, int, int, int]."""
        if self._white_value is not None and self._rgb_color is not None:
            return (*self._rgb_color, self._white_value)
        return None

    @property
    def brightness(self) -> float:
        """Return the brightness of this light between 0..255."""
        return float(self.get_attribute("brightness", 0))

    @property
    def hs_color(self) -> tuple[float, float]:
        """Return the hs color value."""
        return self.get_attribute("hs_color", [0, 0])

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self.get_attribute("is_on", False)

    @property
    def supported_features(self) -> LightEntityFeature:
        """Flag supported features."""
        return LightEntityFeature.TRANSITION

    def get_rgbw(self) -> list:
        """Get current RGBW values as a list."""
        if not self.is_on:
            return [0 for _ in range(len(self.port))] if not self.is_ws else [0] * 3
        
        # Convert HSB to RGB
        rgb = colorsys.hsv_to_rgb(
            self.hs_color[0] / 360, 
            self.hs_color[1] / 100, 
            self.brightness / 255
        )
        rgb = list(rgb)
        
        # Add white channel if needed
        if self.white_value is not None:
            white = self.white_value
            if not self.customize.get(CONF_WHITE_SEP, True):
                white = white * (self.brightness / 255)
            rgb.append(white / 255)
        
        # Scale to max values
        rgb = [round(x * self.max_values[i]) for i, x in enumerate(rgb)]
        
        # Reorder for WS281x
        if self.is_ws:
            rgb = map_reorder_rgb(rgb, RGB, self._color_order)
        
        return rgb

    async def async_turn_on(self, **kwargs):
        """Turn the light on."""
        if (time.time() - self._last_called) < 0.1:
            return
        self._last_called = time.time()
        self.logger.debug(f"turn on %s with kwargs %s", self.entity_id, kwargs)
        
        if self._restore is not None:
            self._restore.update(kwargs)
            kwargs = self._restore
            self._restore = None
        
        _before = self.get_rgbw()
        self._is_on = True
        if self._task is not None:
            self._task.cancel()
        self._task = asyncio.create_task(self.set_color(_before, **kwargs))

    async def async_turn_off(self, **kwargs):
        """Turn the light off."""
        if (time.time() - self._last_called) < 0.1:
            return
        self._last_called = time.time()
        
        # Save state for restore
        self._restore = {
            "hs_color": self.hs_color,
            "brightness": self.brightness,
            "white_value": self.white_value,
        }
        
        _before = self.get_rgbw()
        self._is_on = False
        if self._task is not None:
            self._task.cancel()
        self._task = asyncio.create_task(self.set_color(_before, **kwargs))

    async def set_color(self, _before, **kwargs):
        """Set the color with smooth transition."""
        transition = kwargs.get("transition")
        update_state = transition is not None and transition > 3
        _after = None
        
        # Update attributes from kwargs
        for item, value in kwargs.items():
            if hasattr(self, f"_{item}"):
                setattr(self, f"_{item}", value)
            if item == "rgb_color":
                _after = map_reorder_rgb(value, RGB, self._color_order)
        
        _after = _after or self.get_rgbw()
        
        # Update RGB color for internal state
        if len(_after) >= 3:
            self._rgb_color = map_reorder_rgb(tuple(_after[:3]), self._color_order, RGB)
        
        # Calculate transition time
        if transition is None:
            transition = self.smooth.total_seconds()
            ratio = self.calc_speed_ratio(_before, _after)
            transition = transition * ratio
        
        self.async_write_ha_state()
        
        # Prepare ports configuration
        ports = self.port if not self.is_ws else self.port * 3
        config = [(port, _before[i], _after[i]) for i, port in enumerate(ports)]
        
        try:
            await self.mega.smooth_dim(
                *config,
                time=transition,
                ws=self.is_ws,
                jitter=50,
                updater=partial(self._update_from_rgb, update_state=update_state),
                can_smooth_hardware=self.can_smooth_hardware,
                max_values=self.max_values,
                chip=self.chip,
            )
        except asyncio.CancelledError:
            return
        except Exception:
            self.logger.exception("Error while dimming")

    async def async_will_remove_from_hass(self) -> None:
        """Clean up when removing from hass."""
        await super().async_will_remove_from_hass()
        if self._task is not None:
            self._task.cancel()

    def _update_from_rgb(self, rgbw, update_state=False):
        """Update internal state from RGBW values."""
        if len(self.port) == 4:
            w = rgbw[-1]
            rgb = rgbw[:3]
        else:
            w = None
            rgb = rgbw
        
        if self.is_ws:
            rgb = map_reorder_rgb(rgb, self._color_order, RGB)
        
        # Convert RGB to HSV
        h, s, v = colorsys.rgb_to_hsv(
            *[x / self.max_values[i] for i, x in enumerate(rgb)]
        )
        h *= 360
        s *= 100
        v *= 255
        
        self._hs_color = [h, s]
        if self.is_on:
            self._brightness = v
        
        if w is not None:
            if not self.customize.get(CONF_WHITE_SEP, True):
                w = w / (self._brightness / 255) if self._brightness else 0
            else:
                w = w
            w = w / (self.max_values[-1] / 255)
            self._white_value = w
        
        if update_state:
            self.async_write_ha_state()

    async def async_update(self):
        """
        Update the light state from Mega.
        This is needed to sync on/off state with reality.
        """
        if not self.enabled:
            return
        
        rgbw = []
        for x in self.port:
            data = self.coordinator.data
            if not isinstance(data, dict):
                return
            data = data.get(x, None)
            if isinstance(data, dict):
                data = data.get("value")
            data = safe_int(data)
            if data is None:
                return
            rgbw.append(data)
        
        if sum(rgbw) == 0:
            self._is_on = False
        self.async_write_ha_state()

    def calc_speed_ratio(self, _before, _after):
        """Calculate speed ratio for smooth transitions."""
        ret = None
        for i, x in enumerate(_before):
            if i >= len(self.max_values):
                break
            r = abs(x - _after[i]) / self.max_values[i]
            if ret is None:
                ret = r
            else:
                ret = max(r, ret)
        return ret or 1.0
        