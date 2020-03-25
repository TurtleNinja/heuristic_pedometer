# Imports
import serial
from time import sleep
from time import time

class BLE:

    """ ================================================================================
    Constructor that sets up the BLE for the first time. It will only run
    :param serial_port: (str) the Serial port for the PC HM-10
    :param baudrate: (int) the baud rate to use to connect to the PC HM-10
    :param do_config: (bool) whether to initialize the PC HM-10 or not
    :return: None
    ================================================================================ """
    def __init__(self, serial_port, baudrate=9600, do_config=False):
        self._baudrate = baudrate
        self._serial_port = serial_port
        self._ser = serial.Serial(port=serial_port, baudrate=baudrate, timeout=1)
        self._peripheral_mac = None

        if do_config :
            self.write("AT")
            sleep(0.5)
            self.flush()

            commands = ["AT+IMME1", "AT+NOTI1", "AT+ROLE1", "AT+RESET"]
            print("Setting up the HM-10:")
            for command in commands :
                print("> " + command)
                self.write(command)
                sleep(0.5)
            print("Config completed successfully.")
        return

    """ ================================================================================
    Function to connect to the remote HM-10 using a 2-step BLE handshake protocol.
    While the connection is not confirmed, it will loop until 'max_tries' and:
        1) read everything in the buffer (using read_lines())
        2) check if connected: looking for "OK+CONNAOK+CONN" and not "CONNF" or "CONNE"
        3) check if confirmed: looking for "#"
        4) if not connected, writes a connection message (using self.write())
        5) if not confirmed, writes a "AT+NAME?" message (using self.write())
        6) if the loop exited and it wasn't confirmed, it raises an IOError
    :param peripheral_mac: MAC address of the remote HM-10 to connect with
    :param max_tries: maximum number of attempts before raising an IOError
    :return: nothing
    ================================================================================ """
    def connect(self, peripheral_mac, max_tries=20):

        self._peripheral_mac = peripheral_mac

        if self._ser is None or self._ser.closed:
            self._ser = serial.Serial(port=self._serial_port, baudrate=self._baudrate, timeout=1)

        # Always assume connected. Disconnect first and remove connection lost messages.
        print("Resetting connection.")
        self.write("AT")
        sleep(0.5)
        self.flush()
        
        connected = False
        confirmed = False
        tries = 0
        
        while not confirmed and tries < max_tries:
            response = self.read_line()
            if "OK+CONNAOK+CONN" in response:
                connected = True
                print("Connected")
            
            if "#" in response:
                confirmed = True
                print("Confirmed")
                
            if not connected:
                self.write("AT+CON" + self._peripheral_mac)
                sleep(0.5)
                
            elif not confirmed:
                self.write("AT+NAME?")
                sleep(0.5)
                
            tries += 1
        
        if not confirmed:
            raise IOError("Exceed max number of attemps establishing connection")

    """ ================================================================================
    Function to check if a connection was broken and tries to reconnect 'max_tries'
    times. It will loop until 'max_tries' times and:
        1) look for 'OK+LOST' in the 'msg'
        2) call self.connect() if 'OK+LOST' was received
        3) call msg = self.read_lines() to see if 'OK+LOST' is still in the buffer
        4) If it reaches 'max_tries', it raises an IOError
    :param msg: the received message
    :param max_tries: maximum number of attempts before raising an IOError
    :return: nothing, but throws an IOError in case of failed connection
    ================================================================================ """
    def check_connection(self, msg, max_tries=10):
        tries = 0
        
        while "OK+LOST" in msg and tries < max_tries:
            self.connect(self._peripheral_mac)
            msg = self.read_lines()
            tries += 1

        if tries >= max_tries:
            raise IOError("Can't connect to Peripheral")
            

    """ ================================================================================
    Function to read a single character from the BLE buffer
    :return: String containing data read from the BLE buffer (or empty string)
    ================================================================================ """
    def read(self):
        c = ''
        try:
            if self._ser.in_waiting > 0:
                c = self._ser.read(1).decode('utf-8')
        except ValueError:
            print("decode() cannot convert an invalid utf-8 char")
        return c

    """ ================================================================================
    Function to read the HM-10 buffer until the character 'eol' and tries to reconnect a
    lost connection. It repeatedly calls the self.read() function to read one character
    at a time. It will read until 'timeout' is reached if the termination is not found.
    Once the message is received, it calls self.check_connection() to make sure the
    message did not have an error in it and then returns the message.
    :param eol: character (single element string) containing delimiting character
    :param timeout: integer signifying how many seconds before it quits
    :return: String containing data read from the BLE buffer (or empty string)
    ================================================================================ """
    def read_line(self, eol='\n', timeout=1):
        assert len(eol) == 1, "Delimiting character must be a single element string."
        assert isinstance(eol, str), "Delimiting character must be a string."

        msg = ""
        t1 = time()
        c = self.read()
        while (c != eol) and (time() - t1 < timeout):
            msg += c
            c = self.read()

        self.check_connection(msg)
        return msg

    """ ================================================================================
    Function to read the entire HM-10 buffer and tries to reconnect a lost connection.
    It repeatedly calls the self.read() function to read one character at a time.
    Once the message is received, it calls self.check_connection() to make sure the
    message did not have an error in it and then returns the message.
    :return: String containing data read from the BLE buffer (or empty string)
    ================================================================================ """
    def read_lines(self):
        msg = ''
        while self._ser.in_waiting :
            msg += self.read()

        self.check_connection(msg)
        return msg

    """ ================================================================================
    Function to write a message 'msg' to the PC HM-10. When not connected, these are
    commands to the module. When connected, it will be data sent over BLE.
    :return: nothing
    ================================================================================ """
    def write(self, msg):
        self._ser.write(msg.encode('utf-8'))
        return

    """ ================================================================================
    Function to clean both input and output buffers of the PC HM-10 module.
    :return: nothing
    ================================================================================ """
    def flush(self):
        self._ser.flushInput()
        self._ser.flushOutput()
        sleep(0.1)
        return

    """ ================================================================================
    Function to disconnect BLE, flush buffers, and close the Serial port
    :return: nothing
    ================================================================================ """
    def close(self):
        self.write("AT")
        sleep(0.5)
        self.flush()
        self._ser.close()
        return
