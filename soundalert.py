#!/usr/bin/python
import argparse
import logging
import os
import pyaudio
import signal
import smtplib
import subprocess
import sys
import time
import wave
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
# include the local path to dejavu.py and associated modules
sys.path.append('/usr/local/bin')
#-----------------------
# Begin Declarations   |
#-----------------------
#-----------------------
#     Constants        |
#-----------------------
VERSION = '0.1'
LATESTMODS = '0.1: I am completely operational, and all my circuits are functioning perfectly.'
CHUNK = 8192
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 10
MINIMUM_ACCEPTABLE_CONFIDENCE = 3
FROMEMAIL = 'FROMEMAIL@MYSERVER.COM' // replace with your from email address
FROMPASS = 'EMAILPASSWORD' // replace with your email password
FROMSERVER = 'smtp.SERVER.com' //replace with your SMTP server, e.g. smtp.gmail.com
FROMPORT = 465 // this is the right port for Gmail
RECIPIENTS = ['8039999999@vtext.com'] // replace with an email to text email address
SUBJECT = 'Sound Match'
#-----------------------
# End Declarations     |
#-----------------------
#-----------------------
# Begin Subroutines    |
#-----------------------
def getArgs():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,description='Capture audio clips and look for a match:\n1. Record a clip and save the audio file\n2. Call dejavu to look for a match\n3. If a match is detected, send message\n4. Log success or failure and repeat if no critical errors.')
    parser.add_argument("-d", "--debug", help="set logging level to debug and turn on console messages.",
                    action="store_true")
    parser.add_argument("-v", "--version", help="display current version number then exit",
                    action="store_true")
    args = parser.parse_args()
    return(args)

def sigTermHandler(signum, frame):
    global analyzing, shutdown
    if analyzing:
        logging.info('Shutdown requested while analyzing an audio clip.  Setting shutdown flag.')
        shutdown = bool(True)
    else:
        logging.info('Shutdown requested and no analysis in process.  Terminating now.')
        sys.exit(0)
    return()

def getInputInfo():
    logging.debug('Entering getInput')
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    inputDevices = []
    for i in range (0,numdevices):
        if p.get_device_info_by_host_api_device_index(0,i).get('maxInputChannels')>0:
            inputDevices.append(i)
    if len(inputDevices) == 0:
        device_id = -1
        channels = 0
        rate = 0
    else:
        device_id = inputDevices[0]
        devinfo = p.get_device_info_by_index(device_id)
        channels = int(devinfo['maxInputChannels'])
        rate = int(devinfo['defaultSampleRate'])
    p.terminate()
    logging.debug('Exiting getInput')
    return({'device_id' : device_id, 'channels' : channels, 'rate' : rate})

def createAudioClip(dev_info):
    # first off, create a pyaudio instance and set up our
    # input stream
    logging.debug('Entering createAudioClip')
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
             channels = dev_info['channels'],
             rate = dev_info['rate'],
             input = True,
             input_device_index = dev_info['device_id'],
             frames_per_buffer = CHUNK)
    # output our getting started message
    logging.debug('Starting %s second audio clip recording', RECORD_SECONDS)
    frames = []
    starttime = time.time()
    # loop for RECORD_SECONDS seconds buffering all
    # data received from our input stream above
    try:
        logging.debug('Preparing to record clip')
        while (time.time() - starttime) < RECORD_SECONDS:
            try:
                data = stream.read(CHUNK)
            except IOError as ex:
                if ex[1] <> pyaudio.paInputOverflowed:
                    raise
                data = '\x00' * CHUNK
            frames.append(data)
        # save the data in wav format to file named clipYYYYMMDDHHMMSS.wav
        out_file = '/tmp/clip' + time.strftime('%Y%m%d%H%M%S') + '.wav'
        logging.debug('Audio recording completed, preparing to write file %s', out_file)
        wf = wave.open(out_file, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        # close file and exit
        wf.close()
        logging.debug('Audio clip saved to file %s.', out_file)
    except:
        logging.error('Unable to record audio clip')
        out_file = 'none'
    # perform orderly cleanup/shutdown of our stream
    stream.stop_stream()    # "Stop Audio Recording
    stream.close()          # "Close Audio Recording
    p.terminate()           # "Audio System Close
    logging.debug('Exiting createAudioClip')
    return(out_file)

def sendAlert(emailText):
    logging.debug('Entering sendAlert')
    for emailAddr in RECIPIENTS:
        msgRoot = MIMEMultipart('related')  # first off, create a multipart MIME object
        msgRoot['Subject'] = SUBJECT
        msgRoot['From'] = FROMEMAIL
        msgRoot['To'] = emailAddr
        msgRoot.preamble = 'This is a multi-part message in MIME format.'
        msg = MIMEMultipart('alternative')
        msgRoot.attach(msg)
        # Record the MIME types of both parts - text/plain and text/html.
        part1 = MIMEText(emailText, 'plain')
        part2 = MIMEText('<html><body><p>' + emailText + '</p></body></html>', 'html')
        # Attach parts into message container.
        # According to RFC 2046, the last part of a multipart message, in this case
        # the HTML message, is best and preferred.
        msg.attach(part1)
        msg.attach(part2)
        logging.debug('Message constructed successfully.  Preparing to send email to %s.', emailAddr)
        try:
            s = smtplib.SMTP_SSL(FROMSERVER, FROMPORT)
            s.login(FROMEMAIL, FROMPASS)
            s.sendmail(msgRoot['From'], msgRoot['To'], msgRoot.as_string())
            s.quit()
            logging.info('Alert Message: ' + msgRoot['Subject'] + ' sent to ' + msgRoot['To'])
        except Exception as e:
            logging.error('Error encountered while sending the email to "%s": %s' % (msgRoot['To'], repr(e)))
    logging.debug('Exiting sendAlert')
    return()

#-----------------------
# End Subroutines      |
#-----------------------
#-----------------------
# Begin Main Program   |
#-----------------------
# First, check to see if any arguments were entered on the command line.
args = getArgs()
if args.version:  # If the -v or --version option was specified on the command line, print out version number and exit
    print 'You are running soundalert.py version: ' + VERSION
    print 'Featuring:\n' + LATESTMODS
    exit(0)
# Next, instantiate our logging function.  logging.debug, .info, .warning, .error, .critical are supported
if args.debug:
    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename="/var/log/soundalert.log", level=logging.DEBUG)
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.debug('Debug mode enabled.')
else:
    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename="/var/log/soundalert.log", level=logging.INFO)
# find an attached microphone, if it exists...
device_info = getInputInfo()
# if a microphone has been found, get started...
if device_info['device_id'] <> -1:
    # set a couple flags that are used for handling a shutdown request and initiate our sigTerm handler so that a kill request is handled gracefully...
    shutdown = bool(False)
    analyzing = bool(False)
    signal.signal(signal.SIGTERM, sigTermHandler)
    # get our first sound clip
    sound_file = createAudioClip(device_info)
    while not shutdown and True:
        if sound_file <> 'none':
            this_file = sound_file
            analyzing = bool(True)
            proc = subprocess.Popen(['dv.py', '-c', '/usr/local/bin/dejavu.cnf', '-r', 'file', this_file], stdout=subprocess.PIPE, \
                                 stderr=subprocess.STDOUT, stdin=subprocess.PIPE, bufsize=0)
            sound_file = createAudioClip(device_info)
            match_result = proc.stdout.readline()
            analyzing = bool(False)  
            if match_result.startswith('None'):
                logging.debug('No match for this audio clip.')
            else:
                confidence_level = 0
                items = match_result.split(',')
                for item in items:
                    if item.split(':')[0].strip() == "'confidence'":
                        confidence_level = int(item[item.find(':')+1:].strip())
                        break
                if confidence_level != 0:
                    if confidence_level >= MINIMUM_ACCEPTABLE_CONFIDENCE:
                        try:
                            sendAlert(match_result)
                            logging.info('Alert successfully sent.')
                        except:
                            logging.error('Unable to send out alert.')
                    else:
                        logging.info('Possible match, but below minimum threshhold of ' + \
                                     str(MINIMUM_ACCEPTABLE_CONFIDENCE))
            try:
                os.remove(this_file)
                logging.debug('Removed analyzed audio clip %s.', this_file)
            except:
                pass
        else:
            logging.warning('Missing audio clip.  Pausing for %s seconds before attempting to capture another.', RECORD_SECONDS)
            time.sleep(RECORD_SECONDS)
            sound_file = createAudioClip(device_info)
    logging.info('Your shutdown request is now being processed.  Thank you for your patience.  Exiting now.')
else:
    logging.critical('No audio input device detected.  Please ensure that a microphone is connected and restart.')
sys.exit(0)
#-----------------------
# End Main Program     |
#-----------------------
