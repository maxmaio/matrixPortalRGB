# Matrix Weather display
# For Metro M4 Airlift with RGB Matrix shield, 64 x 32 RGB LED Matrix display

"""
This example queries the Open Weather Maps site API to find out the current
weather for your location... and display it on a screen!
if you can find something that spits out JSON data, we can display it
"""
import time
import board
import microcontroller
import displayio
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font
from digitalio import DigitalInOut, Direction, Pull
from adafruit_matrixportal.network import Network
from adafruit_matrixportal.matrix import Matrix  # pylint: disable=wrong-import-position

BLINK = False
DEBUG = False

cwd = ("/" + __file__).rsplit("/", 1)[
    0
]  # the current working directory (where this file is)

clockFont = cwd + "/fonts/bitbuntu.bdf"
clockFont = bitmap_font.load_font(clockFont)
tempFont = cwd + "/fonts/cherry.bdf"
tempFont = bitmap_font.load_font(tempFont)

icon_spritesheet = cwd + "/weather-icons.bmp"
icon_width = 14
icon_height = 14
icons = displayio.OnDiskBitmap(open(icon_spritesheet, "rb"))


# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

if hasattr(board, "D12"):
    jumper = DigitalInOut(board.D12)
    jumper.direction = Direction.INPUT
    jumper.pull = Pull.UP
    is_metric = jumper.value
elif hasattr(board, "BUTTON_DOWN") and hasattr(board, "BUTTON_UP"):
    button_down = DigitalInOut(board.BUTTON_DOWN)
    button_down.switch_to_input(pull=Pull.UP)

    button_up = DigitalInOut(board.BUTTON_UP)
    button_up.switch_to_input(pull=Pull.UP)
    if not button_down.value:
        print("Down Button Pressed")
        microcontroller.nvm[0] = 1
    elif not button_up.value:
        print("Up Button Pressed")
        microcontroller.nvm[0] = 0
    print(microcontroller.nvm[0])
    is_metric = not microcontroller.nvm[0]
else:
    is_metric = False

if is_metric:
    UNITS = "metric"  # can pick 'imperial' or 'metric' as part of URL query
    print("Jumper set to metric")
else:
    UNITS = "imperial"
    print("Jumper set to imperial")

# Use cityname, country code where countrycode is ISO3166 format.
# E.g. "New York, US" or "London, GB"
LOCATION = "San Francisco, US"
print("Getting weather for {}".format(LOCATION))
# Set up from where we'll be fetching data
DATA_SOURCE = (
    "http://api.openweathermap.org/data/2.5/weather?q=" + LOCATION + "&units=" + UNITS
)
DATA_SOURCE += "&appid=" + secrets["openweather_token"]
# You'll need to get a token from openweather.org
# it goes in your secrets.py file on a line such as:
# 'openweather_token' : 'your_big_humongous_gigantor_token',
DATA_LOCATION = []
SCROLL_HOLD_TIME = 0  # set this to hold each line before finishing scroll

# --- Display setup ---
matrix = Matrix()
network = Network(status_neopixel=board.NEOPIXEL, debug=True)
display = matrix.display
splash = displayio.Group(max_size=1)
background = displayio.OnDiskBitmap(open("loading.bmp", "rb"))
bg_sprite = displayio.TileGrid(
    background,
    pixel_shader=displayio.ColorConverter(),
)
splash.append(bg_sprite)
display.show(splash)
# Drawing setup
group = displayio.Group(max_size=10)  # Create a Group
color = displayio.Palette(4)  # Create a color palette
color[0] = 0x000000  # black background
color[1] = 0xFF0000  # red
color[2] = 0xCC4000  # amber
color[3] = 0x85FF00  # greenish
clock_label = Label(clockFont, max_glyphs=6)
group.append(clock_label)  # add the clock label to the group
_icon_group = displayio.Group(max_size=1)
group.append(_icon_group)

temp_text = Label(tempFont, max_glyphs=6)
temp_text.x = 33
temp_text.y = 23
group.append(temp_text)

_icon_sprite = displayio.TileGrid(
    icons,
    pixel_shader=displayio.ColorConverter(),
    width=1,
    height=1,
    tile_width=icon_width,
    tile_height=icon_height,
    default_tile=0,
    x=17,
    y=16,
)


def set_icon(icon_name):
    """Use icon_name to get the position of the sprite and update
    the current icon.

    :param icon_name: The icon name returned by openweathermap

    Format is always 2 numbers followed by 'd' or 'n' as the 3rd character
    """

    icon_map = ("01", "02", "03", "04", "09", "10", "11", "13", "50")

    print("Set icon to", icon_name)
    if _icon_group:
        _icon_group.pop()
    if icon_name is not None:
        row = None
        for index, icon in enumerate(icon_map):
            if icon == icon_name[0:2]:
                row = index
                break
        column = 0
        if icon_name[2] == "n":
            column = 1
        if row is not None:
            _icon_sprite[0] = (row * 2) + column
            _icon_group.append(_icon_sprite)


def update_time(*, hours=None, minutes=None, show_colon=False):
    now = time.localtime()  # Get the time values we need
    if hours is None:
        hours = now[3]
    if hours >= 18 or hours < 6:  # evening hours to morning
        clock_label.color = color[1]
    else:
        clock_label.color = color[3]  # daylight hours
    suffix = "AM"
    if hours > 12:  # Handle times later than 12:59
        suffix = "PM"
        hours -= 12
    elif not hours:  # Handle times between 0:00 and 0:59
        hours = 12

    if minutes is None:
        minutes = now[4]

    if BLINK:
        colon = ":" if show_colon or now[5] % 2 else " "
    else:
        colon = ":"
    clock_label.color = 0x777777
    clock_label.text = "{hours}{colon}{minutes:02d}{suffix}".format(
        hours=hours, minutes=minutes, colon=colon, suffix=suffix
    )
    bbx, bby, bbwidth, bbh = clock_label.bounding_box
    # Center the label
    clock_label.x = round(display.width / 2 - bbwidth / 2)
    clock_label.y = 6
    if DEBUG:
        print("Label bounding box: {},{},{},{}".format(bbx, bby, bbwidth, bbh))
        print("Label x: {} y: {}".format(clock_label.x, clock_label.y))


def tempColor(temp):
    temp_text.color = 0x777777


localtime_refresh = None
weather_refresh = None
while True:
    # only query the weather every 10 minutes (and on first run)
    if (not weather_refresh) or (time.monotonic() - weather_refresh) > 600:
        try:
            weather = network.fetch_data(DATA_SOURCE, json_path=(DATA_LOCATION,))
            print("Response is", weather)
            set_icon(weather["weather"][0]["icon"])
            temperature = weather["main"]["temp"]
            temp_text.text = "%d" % temperature
            print(temperature)
            tempColor(temperature)
            weather_refresh = time.monotonic()
        except RuntimeError as e:
            print("Some error occured, retrying! -", e)
            continue
        try:
            update_time(
                show_colon=True
            )  # Make sure a colon is displayed while updating
            network.get_local_time()  # Synchronize Board's clock to Internet
            last_check = time.monotonic()
        except RuntimeError as e:
            print("Some error occured, retrying! -", e)
        display.show(group)
    update_time()
    time.sleep(1)
