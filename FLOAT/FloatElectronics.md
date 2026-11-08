# FLOAT ELECTRONICS NOTES
wanted to make a thing that explains what all the stuff for the float is and what it does so that anyone else who has to mess around with the board or make a new one has all the information and for me to thinkkk

## Board
    -Heltec Wireless Stick [https://heltec.org/project/wireless-stick-v3/]
    -Esp32
    -Built in radio
    -5v power

## Components
list of individual components on or connected to the PCB

### Motor Driver
    -Pololu G2 High-Power Motor Driver 18v17 (or something similar, idk for sure) [https://www.pololu.com/product/2991]
    -Controls the motor by using PWM signals from the stick and turning those 5v signals into 12v signals for our brushless dc motor
    -Has reverse current protection
    -Needs 5v and 12v

### 5v Converter
    -Pololu 5V, 5A Step-Down Voltage Regulator D24V50F5 (or similar) [https://www.pololu.com/product/2851]
    -Takes the 12v power from the battery and converts it for use for the board 

### Pressure Sensor
    -I think its the Bar High-Resolution Depth/Pressure Sensors from Blue Robotics [https://bluerobotics.com/store/sensors-cameras/sensors/bar-depth-pressure-sensor/]
    -Reads temperature, depth and pressure
    -2.2-5.5v power
    -4-position JST GH connector [https://www.digikey.com/en/products/detail/jst-sales-america-inc/BM04B-GHS-TBT-LF-SN-N/807802]

### Photoresistor
    -New for this year
    -Takes the amount of light and turns it into resistance, can be read by the board and spit out a light value
    -No clue what kind we are gonna use

### Hall Effect Sensors
    -Sense magnetic fields, used for sensing when syringe is at the top or bottom
    -Uses 1x3 pin connectors
    -Might be 5v power?

### Battery
    -12v NiMH battery
    -XT30 connector

### Motor
    -Brushless 12v DC motor