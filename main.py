import traceback
import matplotlib.pyplot as plt
from time import sleep
from my_wearable.ble import BLE
from my_wearable.pedometer import Pedometer

""" -------------------- Settings -------------------- """
run_config = True                 # whether to config PC HM-10 or not
baudrate = 9600                   # PySerial baud rate of the PC HM-10
serial_port = "/dev/cu.usbserial-0001"    # Serial port of the PC HM-10
peripheral_mac = "78DB2F141044"   # Mac Address of the Arduino HM-10

""" -------------------- Main Wearable Code -------------------- """


#                OBJECTIVE 1
def get_samples(hm10, frequency, pedometer):
    
    # remove the first value because it is usually incomplete
    try:
        msg = hm10.read_line(eol = ";")
    except KeyboardInterrupt:
        print("\nExiting due to user input (<ctrl>+c).")
        hm10.close()
    except Exception:
        print("\nExiting due to an error.")
        traceback.print_exc()
        hm10.close()
    
    # append data to the pedometer
    for i in range(500):
        print(i)
        # read a line of data from BLE
        try:
            msg = hm10.read_line(eol = ";")
            print(msg)
        except KeyboardInterrupt:
            print("\nExiting due to user input (<ctrl>+c).")
            hm10.close()
            break
        except Exception:
            print("\nExiting due to an error.")
            hm10.close()
            traceback.print_exc()
        
        # append data to the pedometer
        pedometer.append(msg)
    
    # write to file
    data_file = "walking_{}hz.txt".format(frequency)
    pedometer.save_file(data_file)
    
    return

#***************************************************************************
#
#                               MAIN
#
#***************************************************************************
"""
# create a BLE instance and establish the connection with peripheral
try:
    hm10 = BLE(serial_port, baudrate, run_config)
    hm10.connect(peripheral_mac)
except Exception:
    print("Can't connect to the peripheral properly")
    hm10.close()
    exit()


# Create a new Pedometer instance
pedometer = Pedometer(maxlen=500, file_flag=True)
frequencies = [100, 50, 5, 2, 0.1]
for i in range(1):
    #hm10.flush()
    print("Current sampling frequency: {}".format(frequencies[i]))
    hm10.write("CF{:d};".format(i))
    print("CF{:d};".format(i))
    sleep(0.2)
    hm10.flush()
    get_samples(hm10, frequencies[i], pedometer)
    pedometer.reset()
    
hm10.close()
"""

# OBJECTIVE 2,3,4

pedometer = Pedometer(maxlen=500, file_flag=True)
pedometer.process()

