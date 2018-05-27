#!/usr/bin/python3

import socket
import sys
import json
import time
import struct
import codecs
import threading

#./router.py <ADDR> <PERIOD> [STARTUP]
###############################################################################
###############################################################################
#### GLOBAL
args = list(sys.argv)
UDP_ORIG_IP = args[1]
UDP_PORT = 55151
TIME_TO_WAIT = int(args[2])


###############################################################################
###############################################################################
def resolve_cmd_str(cmd, distance_vector):
	
	cmd = cmd.split(" ")

	if cmd[0] == "add": 			# add cmd[1] in distance_vector with wheight cmd[2]
		distance_vector[cmd[1]] = (cmd[1], int(cmd[2]), UDP_ORIG_IP)
		return 1
	elif cmd[0] == "del": 			# remove cmd[1] from distance_vector
		del distance_vector[cmd[1]]
		return 1
	elif cmd[0] == "trace": 		# finds route to cmd[1]
		print("procurar rota para ", cmd[1], " ( incompleto )\n")
		return 1
	elif cmd[0] == "quit": 		# finds route to cmd[1]
		print("Adeus!\n")
		return -1
	else :
		print("comando desconhecido!\n")
		return 1


###############################################################################
###############################################################################
if __name__ == "__main__":

	udp_sock = socket.socket(socket.AF_INET, 	# Internet
	                     socket.SOCK_DGRAM) 	# UDP

	# bind this port on local IP to UDP socket
	udp_sock.bind((UDP_ORIG_IP, UDP_PORT))

	# dictionary { DESTINATION_IP : (<whom_to_send>, <weight>, <who_told>) }
	# initialized with link to self
	distance_vector = { UDP_ORIG_IP : (UDP_ORIG_IP, 0, UDP_ORIG_IP)}

	# execute commands from input file
	if len(args) == 4:
		file = open(args[3], "r") 
		for line in file:
			resolve_cmd_str(line, distance_vector)
		file.close()

	while True:
		print("Atual vetor de distancias:\n", json.dumps(distance_vector))
		
		print("\n$ ", end='')
		if resolve_cmd_str(input(), distance_vector) < 0:
			break  
