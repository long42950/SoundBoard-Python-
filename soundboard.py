from pynput import keyboard
from pynput.keyboard import KeyCode, Key, Controller
from pathlib import Path
from termcolor import colored, cprint
import pyaudio
import wave
import sys
import time
import random
import _thread as thread
import colorama

##Terminal##
colorama.init()
print_error = lambda x:cprint("ERROR: {0}".format(x), 'red')
print_warning = lambda x:cprint("WARNING: {0}".format(x), 'yellow')

##Audio##
inputi = -1
outputi = -1
p = pyaudio.PyAudio()
isplaying = False
folder_count = 0
folders = []
wavs = []
    
    

##KeyBind##
UNBOUND = 'UNBOUND'
keyboard_controller = Controller()
keybind_enabled = True
text_mode = False
shift_pressed = False

##General Config##
CONFIG_FILE = 'KeyBind.config'
FOLDER_PATH = 'music'
mic_key = UNBOUND
voice_modifier = 0
texting_key = [UNBOUND]


###Fail Safe###
def exit_on_failure():
    input("Press any key to exit....")
    sys.exit()
def GC_completed():
    if mic_key == UNBOUND:
        print_error("mic_key is unbounded in General_Configuration!")
        return False
    if texting_key == UNBOUND:
        print_warning("texting_key is unbounded in General_Configuration!")
    return True
def GC_setter(attribute, value):
    global mic_key, voice_modifier, texting_key
    try:
        match attribute:
            case "mic_key":
                if len(value) == 1:
                    mic_key = value
                    return True
                else:
                    print_error("Only 1 key for mic_key!")
            case "voice_modifier":
                voice_modifier = int(value)
                return True
            case "texting_key":
                varis = value.split(',')
                for var in varis:
                    if len(var) > 1:
                        return False
                texting_key = varis
                return True
        return False
    except:
        print_error("Failed to read Attribute - {0}".format(attribute))
        return False

###Audio Setup###

def init_audio():
    global p, outputi, inputi
    rtn = True
    device_count = p.get_device_count()
    for i in range(device_count):
        name = p.get_device_info_by_index(i)["name"]
        #print(name)
        if name == "CABLE Output (VB-Audio Virtual ":
            #print("output index is {0}".format(i))
            #print(name)
            outputi = i
        elif name == "CABLE Input (VB-Audio Virtual C":
            #print("Input index is {0}".format(i))
            #print(name)
            inputi = i
        #print(p.get_default_output_device_info())
    if outputi == -1:
        print_error("Cannot find VB-Cable Output(Microphone)")
        rtn = False
    if inputi == -1:
        print_error("Cannot find VB-Cable Input(Speaker)")
        rtn = False
    if not rtn:
        color = 'yellow'
        cprint("============Device List=============", 'white', 'on_yellow')
        for i in range(device_count):
            name = p.get_device_info_by_index(i)["name"]
            if name == p.get_default_output_device_info()["name"]:
                text = '{0}.{1}--Default Output Device'.format(i, name)
                color = 'green'
            elif name == p.get_default_input_device_info()["name"]:
                text = '{0}.{1}--Default Input Device'.format(i, name)
                color = 'green'
            else:
                text = '{0}.{1}'.format(i, name)
                color = 'yellow'
            print(colored(text, color))
        cprint("=========End of Device List=========", 'white', 'on_yellow')
    return rtn

def is_wav(name):
    file_format = str(name).split('.')[-1]
    if file_format == 'wav':
        return True
    return False

def parse_combination(string):
    rtn = string.split()[0]
    return rtn

def parse_attribute(string):
    return string.replace(" ", "")

def parse_config(lines):
    phase = 0 # 0=Undefined / 1=GC / 2=Combination
    current_line = 0
    line_to_skip = 0
    GC_succeed = True
    rtn = {
        "count" : 0,
        "combination" : [],
        "error_no" : 0
    }
    for line in lines:
        current_line += 1
        try:
            if line_to_skip > 0:
                line_to_skip -= 1
                continue      
            varis = line.split("|")
            if len(varis) == 3:
                section = parse_attribute(varis[1])
                match section:
                    case "General_Configuration":
                        line_to_skip = 3
                        phase = 1
                        continue
                    case "Combination":
                        line_to_skip = 3
                        phase = 2
                        continue
                    case _:
                        print_warning("Unknwon Section: {0}"
                                      .format(section))
                        continue
            if len(line.split("=")) > 1: #End of Line indicated by "="
                #print(current_line)
                phase = 0
                continue
            match phase:
                case 1:
                    #print(line)
                    #print(len(varis))
                    if len(varis) == 4:
                        attribute = varis[1]
                        value = varis[2]
                        GC_succeed = GC_setter(
                            parse_attribute(attribute),
                            parse_attribute(value)) and GC_succeed
                            
                case 2:
                    if len(varis) == 4:
                        rtn["count"] += 1
                        rtn["combination"].append(
                            {"name" : parse_combination(varis[1]),
                             "key" : parse_combination(varis[2]),
                             "cooldown_no" : -1}
                        )
                    else:
                        print_error("Invalid line format ->{0}".format(line))
                case _:
                    continue
                
        except:
            rtn["count"] = -1
            rtn["combination"] = []
            rtn["error_no"] = 525
            break
    if not GC_completed() or not GC_succeed:
        rtn["count"] = -1
        rtn["combination"] = []
        rtn["error_no"] = 502
    return rtn

def show_configs(configs):
    print('count: {0}'.format(configs["count"]))
    print('error_no: {0}'.format(configs["error_no"]))
    for combination in configs["combination"]:
        print(combination)

def get_audio_directories():
    global folder_count, folders, wavs
    p = Path('./'+FOLDER_PATH)
    lines = []
    try:
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                lines.append(line)
    except:
        print_error("Cannot read config file")
        return False
    configs = parse_config(lines)
    #show_configs(configs)
    match configs["error_no"]:
        case 525:
            print_error("Your KeyBind.config might be corrupted.")
            return False
        case 502:
            print_error("One or more essential configuration missing.")
            return False
    di = 0
    #print(list(configs["combination"][0].keys()))
    for d in p.iterdir():
        dstring = str(d)
        dir_name = dstring.split('\\')[1]
        if d.is_dir():
            for combo in configs["combination"]:
                if combo["name"] == dir_name:
                    fp = Path('./{0}/{1}'.format(FOLDER_PATH, combo["name"]))
                    audio_list = []
                    for audio in fp.iterdir():
                        astring = str(audio).split('\\')[-1]
                        if is_wav(astring):
                            audio_list.append(astring)
                    combo["audios"] = audio_list
                    folders.append(combo)
                    folder_count += 1
                    break
        elif is_wav(dstring):
            for combo in configs["combination"]:
                if combo["name"] == dir_name:
                    wavs.append(combo)
                    break
    return True

def play_audio(key):
    global keybind_enabled, folder_count, folders, wavs
    CHUNK = 0
    audio_name = ""
    try:
        char = key.char
        char = char.lower()
    except:
        return

    if folder_count > 0:
        for folder in folders:
            if folder["key"] == char:
                length = len(folder["audios"])
                while True:
                    randno = random.randint(0,length-1)
                    if folder["cooldown_no"] != randno or length == 1:
                        folder["cooldown_no"] = randno
                        break
                audio_name = folder["audios"][randno]
                #print('{0}/{1}'.format(folder["name"], folder["audios"][randno]))
                wf1 = wave.open('{0}/{1}/{2}'.format(
                    FOLDER_PATH, folder["name"], folder["audios"][randno]))
                CHUNK = wf1.getnframes()
                break  
    if CHUNK == 0:
        for wav in wavs:
            if wav["key"] == char:
                audio_name = wav["name"]
                wf1 = wave.open('{0}/{1}'.format(FOLDER_PATH, wav["name"]))
                CHUNK = wf1.getnframes()
                break

    try:
        stream1 = p.open(format=p.get_format_from_width(wf1.getsampwidth()),
                        channels=wf1.getnchannels(),
                        rate=wf1.getframerate()-voice_modifier,
                        output=True,
                        output_device_index=inputi)
    except:
        #print("Failed to locate .wav file!")
        return
    print('Playing {0}'.format(audio_name))
    data1 = wf1.readframes(CHUNK)
    keyboard_controller.press(mic_key)
    #time.sleep(1)
    stream1.write(data1)
    stream1.stop_stream()
    stream1.close()
    time.sleep(1)
    keyboard_controller.release(mic_key)
    
#p.terminate()

###KeyBind###

def init_keybind():
    print("KeyBind is now enabled")
    
def start_texting(key):
    if texting_key[0] == UNBOUND or text_mode:
        return False
    for tkey in texting_key:
        try:
            if tkey == key.char:
                print("Enable text mode")
                return True
        except:
            continue
    return False

def toggle_text_mode():
    global text_mode
    text_mode = not text_mode

def exit_text_mode(key):
    if not text_mode:
        return False
    if key == Key.esc or key == Key.enter:
        print("Disable text mode")
        return True
    return False

def on_release(key):
    global keybind_enabled, shift_pressed
    if key == Key.space and shift_pressed:
        print(key)
    if start_texting(key) or exit_text_mode(key):
        toggle_text_mode()
        return True
    if not keybind_enabled and key == Key.up:
        keybind_enabled = True
        print("KeyBind is now enabled")
        return True
    elif keybind_enabled:
        if key == Key.down:
            keybind_enabled = False
            print("KeyBind is disabled, press up to enable KeyBind...")
            return True
        try:
            if not text_mode and key.char != mic_key:
                thread.start_new_thread( play_audio, (key,))
        except:
            print_error("Unable to create thread!!!")
        #play_audio(key)
    shift_pressed = False
    return True

def on_press(key):
    global shift_pressed
    if key == Key.shift:
        shift_pressed = True

###Main###
if init_audio():
    if not get_audio_directories():
        exit_on_failure()
    init_keybind()
else:
    exit_on_failure()

# Collect events until released
with keyboard.Listener(on_release=on_release,
                       on_press = on_press) as listener:
    listener.join()
