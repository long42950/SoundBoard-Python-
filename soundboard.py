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
print_error = lambda x:cprint(x, 'red')

##Audio##
CONFIG_FILE = 'KeyBind.config'
inputi = -1
outputi = -1
p = pyaudio.PyAudio()
isplaying = False
folder_count = 0
folders = []
wavs = []
    
    

##KeyBind##
keyboard_controller = Controller()
keybind_enabled = True
    

###Fail Safe###
def exit_on_failure():
    input("Press any key to exit....")
    sys.exit()

###Audio Steup###

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
        print_error("ERROR: Cannot find VB-Cable Output(Microphone)")
        rtn = False
    if inputi == -1:
        print_error("ERROR: Cannot find VB-Cable Input(Speaker)")
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

def parse_dir_name(string):
    rtn = string.split('\t')[0]
    #print(rtn)
    return rtn

def parse_keybind(string):
    rtn = string.split()
    #print(rtn)
    return rtn[0]

def parse_config(lines):
    current_line = 0
    rtn = {
        "count" : 0,
        "combination" : []
    }
    for line in lines:
        if current_line < 3:
            current_line += 1
            continue
        try:
            var = line.split('|')
            if len(var) == 4:
                rtn["count"] += 1
                rtn["combination"].append(
                    {"name" : parse_dir_name(var[1]),
                     "key" : parse_keybind(var[2])
                    })
        except:
            rtn["count"] = -1
            rtn["combination"] = []
            break
    return rtn

def get_audio_directories():
    global folder_count, folders, wavs
    p = Path('.')
    lines = []
    try:
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                lines.append(line)
    except:
        print_error("ERROR: Cannot read config file")
        return False
    configs = parse_config(lines)
    if configs["count"] < 0:
        print_error("ERROR: Your KeyBind.config might be corrupted.")
        return False
    di = 0
    #print(list(configs["combination"][0].keys()))
    for d in p.iterdir():
        dstring = str(d)
        if d.is_dir():
            for combo in configs["combination"]:
                if combo["name"] == dstring:
                    fp = Path(combo["name"])
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
                if combo["name"] == dstring:
                    wavs.append(combo)
                    break
    return True

def play_audio(key):
    global keybind_enabled, folder_count, folders, wavs
    voice_modifier = 0
    CHUNK = 0
    try:
        char = key.char
        char = char.lower()
    except:
        return

    if folder_count > 0:
        for folder in folders:
            if folder["key"] == char:
                randno = random.randint(0,len(folder["audios"])-1)
                #print('{0}/{1}'.format(folder["name"], folder["audios"][randno]))
                wf1 = wave.open('{0}/{1}'.format(
                    folder["name"], folder["audios"][randno]))
                CHUNK = wf1.getnframes()
                break  
    if CHUNK == 0:
        for wav in wavs:
            if wav["key"] == char:
                wf1 = wave.open(wav["name"])
                CHUNK = wf1.getnframes()
                break

    if CHUNK == 0:
        print("ERROR: Failed to locate .wav file!")
        return
    stream1 = p.open(format=p.get_format_from_width(wf1.getsampwidth()),
                    channels=wf1.getnchannels(),
                    rate=wf1.getframerate()-voice_modifier,
                    output=True,
                    output_device_index=inputi)
    data1 = wf1.readframes(CHUNK)
    keyboard_controller.press('k')
    #time.sleep(1)
    stream1.write(data1)
    stream1.stop_stream()
    stream1.close()
    time.sleep(1)
    keyboard_controller.release('k')
    
#p.terminate()

###KeyBind###

def init_keybind():
    print("KeyBind is now enabled")

def on_release(key):
    global keybind_enabled
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
            thread.start_new_thread( play_audio, (key,))
        except:
            print("ERROR: Unable to create thread!!!")
        #play_audio(key)
    return True

###Main###
if init_audio():
    if not get_audio_directories():
        exit_on_failure()
    init_keybind()
else:
    exit_on_failure()

# Collect events until released
with keyboard.Listener(on_release=on_release) as listener:
    listener.join()
