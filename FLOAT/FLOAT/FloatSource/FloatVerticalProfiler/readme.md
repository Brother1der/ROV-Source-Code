This repository contains the FLOAT source code used during the 2026 competition year.
The software is designed to operate the FLOAT vertical profiler using a Raspberry Pi and the FLOAT PCB version 2.3.0.

CONTACT INFO:
If for whatever reason something is broken, or you have some questions about how this code works
feel free to contact me @ oreillyconner@gmail.com

HARDWARE
    Computer-Raspberry Pi Zero or Zero 2 W
    Interface-FLOAT PCB 2.3.0
    Sensors-
        MS5837 pressure sensor from Blue Robotics configured for the low pressure variant
        Two limit switches used to restrict the travel of the buoyancy engine. These switches are required to
            prevent motor overheating and mechanical damage
    Motor Controller- Pololu VNH5019 motor controller

Outputs
RFM9X LoRa radio from Adafruit. This radio provides long range communication at reasonable data rates and maintains a 
stable connection even in high interference environments
Blue Robotics indicator light used to signal that the robot 
has completed its profiling run and is ready to be removed from the water

IMPORTANT HARDWARE NOTE
The FLOAT PCB version 2.3.0 contains a manufacturing error. 
The positive pin and the diode must be manually connected due to a missing trace on the board

SOFTWARE OVERVIEW
This program is designed to run on a Raspberry Pi using the FLOAT 2.3.0 PCB. 
It manages sensor input motor control and communication required for autonomous vertical profiling

SETUP
    This software is optimized for the Raspberry Pi Zero 2 W but should run on most Raspberry Pi models. 
    The Raspberry Pi 5 has not been tested and may experience issues due to major changes in IO behavior

    1.Install Raspberry Pi OS onto a micro SD card and insert it into the Raspberry Pi
    2.verify that Python is installed by running python -V. If Python is not installed install it before continuing
    3.Connect the Raspberry Pi and your computer to the same network
    4.Use SSH to connect to the Raspberry Pi and transfer this repository to the device
    5.Install required dependencies by running pip install -r requirements.txt
    6.Create your own FloatVerticalProfiler using the system controls and use the library

DESIGN PRINCIPLES
    This codebase follows several key design principles
    Object oriented design. Each major function is implemented as its own independent object
    Reusability. Components are written to be as general as possible to reduce redundant code
    Readability. Code favors clarity and simplicity over clever or complex implementations
