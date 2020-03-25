# Imports
import serial
from time import sleep
from time import time
from scipy import signal as sig
import numpy as np
from matplotlib import pyplot as plt

class Pedometer:

    # Attributes of the class Pedometer
    _maxlen = 0
    _file_flag = False
    __time_buffer = []
    __data_buffer = []
    __steps = 0
    __peaks = []

    """ ================================================================================
    Constructor that sets up the Pedomter class. It will only run once.
    :param max len: (int) max length of the buffer
    :param file_flag: (bool) set whether we will be working with a file or not
    :return: None
    ================================================================================ """
    def __init__(self, maxlen, file_flag):
        self._maxlen = maxlen       # Set the max length of the buffer
        self._file_flag = file_flag # Set whether we are writing to a file or not
        return

    """ ================================================================================
    Resets the pedometer to default state
    :return: None
    ================================================================================ """
    def reset(self):
        self.__time_buffer = []
        self.__data_buffer = []
        __steps = 0
        return

    """ ================================================================================
    Appends new elements to the data and time buffers by parsing 'msg_str' and splitting
    it, assuming comma separation. It also keeps track of buffer occupancy and notifies
    the user when the buffers are full.
    :param msg_str: (str) the string containing data that will be appended to the buffer
    :return: None
    ================================================================================ """
    def append(self, msg_str):

        if (len(self.__time_buffer) == self._maxlen or len(self.__data_buffer) == self._maxlen):
            print("The buffer is full")
            return
        
        try:
            received = msg_str.split(',')
            self.__time_buffer.append(int(received[0]))
            self.__data_buffer.append(int(received[1]))
        except:
            print("Received invalid data")
            print(msg_str)
        
        return


    """ ================================================================================
    Saves the contents of the buffer into the specified file one line at a time.
    :param filename: (str) the name of the file that will store the buffer data
    :return: None
    ================================================================================ """
    def save_file(self, filename):

        with open(filename, 'w') as file:
            for i in range(len(self.__time_buffer)):
                file.write("{},{}\n".format(self.__time_buffer[i], self.__data_buffer[i]))
        return


    """ ================================================================================
    Loads the contents of the file 'filename' into the time and data buffers
    :param filename: (str) the name (full path) of the file that we read from
    :return: None
    ================================================================================ """
    def load_file(self, filename):
        self.__time_buffer = []
        self.__data_buffer = []
        count = 0

        with open(filename, 'r') as file:
            while True:
                line = file.readline()
                if not line:
                    break
                
                vals = line.rstrip().split(',')
                self.__time_buffer.append(int(vals[0]))
                self.__data_buffer.append(int(vals[1]))
                count += 1
                
        self._maxlen = count
        return


    """ ================================================================================
    Plots the data in the time and data buffers onto a figure
    :param: None
    :return: None
    ================================================================================ """
    def plot(self, filename):

        plt.figure()
        plt.subplot(111)
        plt.plot(self.__time_buffer, self.__data_buffer)
        plt.savefig(filename)
        #plt.show()
        return

    """ ================================================================================
    This function runs the contents of the __data_buffer through a low-pass filter. It
    first generates filter coefficients and  runs the data through the low-pass filter.
    Note: In the future, we will only generate the coefficients once and reuse them.
    :param cutoff: (int) the cutoff frequency of the filter
    :return: None
    ================================================================================ """
    def __lowpass_filter(self, cutoff): # __ makes this a private method

        b,a = sig.butter(3, cutoff, btype='low', analog=False, output='ba', fs=None)
        filtered_data = sig.lfilter(b, a, self.__data_buffer)
        self.__data_buffer = filtered_data
        return


    """ ================================================================================
    This function runs the contents of the __data_buffer through a high-pass filter. It
    first generates filter coefficients and runs the data through the high-pass filter.
    Note: In the future, we will only generate the coefficients once and reuse them.
    :param cutoff: (int) the cutoff frequency of the filter
    :return: None
    ================================================================================ """
    def __highpass_filter(self, cutoff): # __ makes this a private method
        
        b,a = sig.butter(3, cutoff, btype='high', analog=False, output='ba', fs=None)
        filtered_data = sig.lfilter(b, a, self.__data_buffer)
        self.__data_buffer = filtered_data
        return


    """ ================================================================================
    Runs the contents of the __data_buffer through a moving average filter
    :param N: order of the smoothing filter (the filter length = N+1)
    :return: None
    ================================================================================ """
    def __smoothing_filter(self, N):
        
        boxcar = sig.boxcar(N+1)  / (N+1)
        filtered_data = sig.lfilter(boxcar, 1, self.__data_buffer)
        self.__data_buffer = filtered_data
        return


    """ ================================================================================
    Runs the contents of the __data_buffer through a de-meaning filter.
    :param: None
    :return: None
    ================================================================================ """
    def __demean_filter(self):
        # Compute the mean using a sliding window
        filtered = sig.detrend(self.__data_buffer)
        self.__data_buffer = filtered
        return
    

    """ ================================================================================
    Run raw data through multiple filters
    :param None:
    :return: None:
    ================================================================================ """
    def __filter_pedometer(self):

        self.__demean_filter()
        # run the smoothing_filter with a window of 5
        self.__smoothing_filter(4)
        # Take the gradient of the data using np.gradient
        self.__data_buffer = np.gradient(self.__data_buffer)
        # 4. Use a lowpass fiter with a cutoff frequency of around 5Hz
        cutoff = 5 / (0.5 * 50)
        self.__lowpass_filter(cutoff)
        return
        
    """ ================================================================================
    Mark all peaks in filtered data - indicating the indices of steps
    :param None:
    :return: None:
    ================================================================================ """
    def __find_peaks(self):

        self.__peaks = [None] * 500
        self.__filter_pedometer()
        self.__peaks = sig.find_peaks(self.__data_buffer)[0]
        return

    """ ================================================================================
    Saves the contents of the buffer into the file line by line
    :param filename: (str) the name of the file that will store the buffer data
    :return: None
    ================================================================================ """
    def __count_steps(self):
        
        self.__find_peaks()
        upper_bound = 4000
        lower_bound = -200
        
        inds = []
        for peak in self.__peaks:
          if peak < upper_bound and peak > lower_bound:
              self.__steps += 1
              inds.append(peak)
        
        # Plot the data with peaks marked
        plt.subplot(111)
        plt.title("Peaks")
        for x in inds:
            plt.plot(self.__time_buffer[x], self.__data_buffer[x], 'rs')
            print(self.__data_buffer[x])
        plt.show()

        return
    
    """ ================================================================================
    The main process block of the pedometer. When completed, this will run through the
    filtering operations and heuristic methods to compute and return the step count.
    For now, we will use it as our "playground" to filter and visualize the data.
    :param None:
    :return: Current step count
    ================================================================================ """
    def process(self):
        
        file = "objective1/walking_50hz.txt"
        #       OBJECTIVE 4
        self.load_file(file)
        self.__count_steps()
        print(self.__steps)
        return self.__steps
        
        
        """
        
        #       OBJECTIVE 1
        frequencies = [100, 50, 5, 2, 0.1]
        for i in range(4):
            file = "objective1/walking_{}hz.txt".format(frequencies[i])
            self.reset()
            self.load_file(file)
            self.plot("objective1/IMU_sampling_{}hz.png".format(frequencies[i]))
        
        
        """
        """
        
        #           OBJECTIVE 2
        # Raw data
        self.reset()
        self.load_file(file)
        self.plot("Images/IMU_sampling_50Hz.png")
        
        # Demean filter
        self.reset()
        self.load_file(file)
        self.__demean_filter()
        self.plot("Images/IMU_filtered_DM.png")
        
        # Smoothing filter
        self.reset()
        self.load_file(file)
        self.__smoothing_filter(4)
        self.plot("Images/IMU_filtered_SF.png")

        cutoff_freqencies = [0.01, 0.5, 1, 5, 10, 15]
        for cutoff_freq in cutoff_freqencies:
            # calculating normalized cutoff frequency
            cutoff = cutoff_freq / (0.5 * 50)
            
            # High-pass frequency
            self.reset()
            self.load_file(file)
            self.__highpass_filter(cutoff)
            self.plot("Images/IMU_filtered_HPF{}.png".format(cutoff_freq))
            
            # Low-pass frequency
            self.reset()
            self.load_file(file)
            self.__lowpass_filter(cutoff)
            self.plot("Images/IMU_filtered_LPF{}.png".format(cutoff_freq))
        
        """
        """
        
        # OBJECTIVE 3
        plt.figure()
        plt.subplot(211)
        plt.title("Raw")
        # load the contents of 'walking_50hz.txt' into the data buffer
        self.load_file(file)
        # find the peaks of the data
        self.__find_peaks()
        # plot data
        plt.subplot(212)
        plt.title("Filtered")
        plt.plot(self.__time_buffer, self.__data_buffer)
        plt.savefig("Images/peak_detection.png")
        plt.show()
        
        """
