/********************************************************************************
** Bidirectional BLE Communication using a 2-step handshake protocol
*********************************************************************************/
// IMU library includes
#include "I2Cdev.h"                       // library for operations with IMU
#include "MPU6050_6Axis_MotionApps20.h"
#include "Wire.h"                         
#include <AltSoftSerial.h>                // alternative serial printer
#include "U8x8lib.h"                      // OLED library


AltSoftSerial hm10;                       // create the AltSoftSerial connection for the HM10
#define OLED_RESET 4                      // this value resets the OLED
U8X8_SSD1306_128X32_UNIVISION_HW_I2C u8x8(OLED_RESET); // initialize a connection with OLED

// IMU variables
const int MPU_addr=0x68;                    // I2C address of the MPU-6050
MPU6050 IMU(MPU_addr);                      // Instantiate IMU object
const int IMUPin = 2;                       // IMUInterrupt pin
volatile bool imuDataReady = false;         // track if there is new interruped from IMU
int16_t ax, ay, az, gx, gy, gz, tp;         // IMU data variables
const unsigned long sampling_period[] = {10000, 20000, 200000, 500000, 10000000};
unsigned long current_sampling_period = 0;
unsigned int sample_count = 0;

// Button Variables
const int buttonPin = 3;                    // button interrupt pin
bool asleep = false;                        // program's state
volatile bool buttonPressed = false;        // track botton presses

// BLE variables
char in_text[64];                           // Character buffer
bool bleConnected = false;                  // false == not connected, true == connected
unsigned long startPeriod = 0;                // timer for sending data once connected



/**********************************************************************************
 *                            BLE FUNCTIONS
 */
// --------------------------------------------------------------------------------
// This function handles the BLE handshake
// It detects if central is sending "AT+...", indicating the handshake is not complete
// If a "T" is received right after an "A", we send back the handshake confirmation
// The function returns true if a connection is established and false otherwise
// --------------------------------------------------------------------------------
bool bleHandshake(char input) {
  static char lastChar;
    if (lastChar == 'A' && input == 'T') {
      hm10.print("#;");
      delay(50);
      hm10.flushInput();
      bleConnected = true;
      startPeriod = micros();
      return true;
    }
    
    lastChar = input;
    
    return false;
}

// --------------------------------------------------------------------------------
// This function reads characters from the HM-10
// It calls the bleHandshake() function to see if we are connecting
// Otherwise, it fills a buffer "in_text" until we see a ";" (our newline stand-in)
// --------------------------------------------------------------------------------
bool readBLE() {
  static int i = 0;
  
  char c = hm10.read();
  
  if (bleHandshake(c)) {
    i = 0;
  }
  else {
    // If the buffer overflows, go back to its beginning
    if (i >= sizeof(in_text)-1)
      i = 0;

  
    // All of our messages will terminate with ';' instead of a newline
    if (c == ';') {
      in_text[i] = '\0'; // terminate the string
      i = 0;
      return true;
    }
    else {
      in_text[i++] = c;

      // change the sampling period
      if (c >= '0' && c <= '4') {
        current_sampling_period = sampling_period[c - '0'];
        sample_count = 0;
        hm10.flushOutput();
        Serial.print("Current sampling period: ");
        Serial.println(current_sampling_period);
      }
    }
  }

  return false; // nothing to print
}



/**********************************************************************************
 *                            OLED DISPLAY
 */
 
// --------------------------------------------------------------------------------
// Initialize the OLED with base font for fast refresh
// --------------------------------------------------------------------------------
void initDisplay() {
  u8x8.begin();
  u8x8.setPowerSave(0);
  u8x8.setFont(u8x8_font_amstrad_cpc_extended_r);
  u8x8.setCursor(0, 0);
}

// --------------------------------------------------------------------------------
// Show message to OLED display
// --------------------------------------------------------------------------------
void showMessage(const char * message, int row, bool cleardisplay) {
  
  // clear display when requested or when reaching the bound of display
  if(cleardisplay || row % 4 == 0) {
    u8x8.clearDisplay();
    u8x8.setCursor(0, 0);
  }
  u8x8.print(message);
}



/**********************************************************************************
 *                            IMU FUNCTIONS
 */
 
// --------------------------------------------------------------------------------
// Initialize the IMU (only on startup)
// --------------------------------------------------------------------------------
void initIMU() {

  // Initialize the IMU and the DMP (Digital Motion Processor) on the IMU
  IMU.initialize();
  IMU.dmpInitialize();
  IMU.setDMPEnabled(true);

  // Initialize I2C communications
  Wire.begin();
  Wire.beginTransmission(MPU_addr);
  Wire.write(MPU_addr);               // PWR_MGMT_1 register
  Wire.write(0);                      // Set to zero (wakes up the MPU-6050)
  Wire.endTransmission(true);

  // Create an interrupt for pin 2, which is connected to the INT pin of the MPU6050
  pinMode(IMUPin, INPUT);
  attachInterrupt(digitalPinToInterrupt(IMUPin), interruptPinISR, RISING);
}

// --------------------------------------------------------------------------------
// Function to check the interrupt pin if there is data available in the buffer
// --------------------------------------------------------------------------------
void interruptPinISR() {
  imuDataReady = true;
}

// --------------------------------------------------------------------------------
// Function to read a single sample of IMU data
// Currently, this reads 3 acceleration axis, temperature, and 3 gyro axis.
// --------------------------------------------------------------------------------
void readIMU() {
  Wire.beginTransmission(MPU_addr);
  Wire.write(0x3B);                   // starting with register 0x3B (ACCEL_XOUT_H)
  Wire.endTransmission(false);
  
  Wire.requestFrom(MPU_addr,14,true); // request a total of 14 registers
  
  //Accelerometer (3 Axis)
  ax = Wire.read()<<8|Wire.read();      // 0x3B (ACCEL_XOUT_H) & 0x3C (ACCEL_XOUT_L)    
  ay = Wire.read()<<8|Wire.read();      // 0x3D (ACCEL_YOUT_H) & 0x3E (ACCEL_YOUT_L)
  az = Wire.read()<<8|Wire.read();      // 0x3F (ACCEL_ZOUT_H) & 0x40 (ACCEL_ZOUT_L)
  
  //consume over temperature data
  tp = Wire.read()<<8|Wire.read();           // 0x41 (TEMP_OUT_H) & 0x42 (TEMP_OUT_L)
  
  //Gyroscope (3 Axis)
  gx = Wire.read()<<8|Wire.read();      // 0x43 (GYRO_XOUT_H) & 0x44 (GYRO_XOUT_L)
  gy = Wire.read()<<8|Wire.read();      // 0x45 (GYRO_YOUT_H) & 0x46 (GYRO_YOUT_L)
  gz = Wire.read()<<8|Wire.read();      // 0x47 (GYRO_ZOUT_H) & 0x48 (GYRO_ZOUT_L)
}

// --------------------------------------------------------------------------------
// Function to grab new IMU data
// --------------------------------------------------------------------------------
bool getData()
{
  bool newData = false;
  if (imuDataReady)
  {
    readIMU();
    newData = true;
  }
  return newData;
}


// --------------------------------------------------------------------------------
// Function to calculate the L1-Norm from accelerometer data and send to BLE
// --------------------------------------------------------------------------------
void sendAccelL1Norm()
{
  getData();
  
  // calculate the L1-Norm
  unsigned long l1_norm = abs(ax);
  l1_norm += abs(ay);
  l1_norm += abs(az);

  // formatting data before sending
  char msg[16] = {0};
  sprintf(msg, "%8lu,%5lu;", startPeriod, l1_norm);

  // send to BLE and print to Serial to check
  hm10.print(msg);
  Serial.println(msg);
}


/**********************************************************************************
 *                            THE MAIN PROGRAM
 */

// --------------------------------------------------------------------------------
// Setup: executed once at startup or reset
// --------------------------------------------------------------------------------
void setup() {
  // set up OLED
  initDisplay();
  u8x8.clearDisplay();  
  
  // set up the IMU
  current_sampling_period = sampling_period[0];
  sample_count = 0;
  initIMU();

  Serial.begin(9600);
  hm10.begin(9600);
  
  Serial.println("==============================");
  Serial.println("    MyWearable Code Started   ");
  Serial.println("==============================");
} 

// --------------------------------------------------------------------------------
// Loop: main code; executed in an infinite loop
// --------------------------------------------------------------------------------
void loop() {
  
  // Confirm the connection
  if (hm10.available()) {
    if (readBLE())
      Serial.println(in_text);
  }

  
  if (!asleep && bleConnected) {
    if (micros() - startPeriod >= current_sampling_period && sample_count < 515) {
      startPeriod = micros();
      sendAccelL1Norm();
      sample_count++;
    }
  }
  
}
