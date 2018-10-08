#!/bin/sh
sudo ionice -c1 -n0 nice -n -20 sudo python /home/pi/Documents/Python/ir/ir.py go
