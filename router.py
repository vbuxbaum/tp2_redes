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
# decides what to do based on received command
def resolve_cmd_str(cmd, distance_vector):
	
	cmd = cmd.split(" ")

	if cmd[0] == "add": 			# add cmd[1] in distance_vector with wheight cmd[2]
		try: 
			distance_vector[cmd[1]] = (cmd[1], int(cmd[2]), UDP_ORIG_IP)
		except ValueError:
			print("\n > > > Escolha ruim de valores. . .\n")
		return 1
	elif cmd[0] == "del": 			# remove cmd[1] from distance_vector
		try:
			del distance_vector[cmd[1]]
		except KeyError:
			print("\n > > > Conexão inexistente . . .\n")
		return 1
	elif cmd[0] == "trace": 		# finds route to cmd[1]
		print("procurar rota para ", cmd[1], " ( incompleto )\n")
		start_trace(cmd[1])
		return 1
	elif cmd[0] == "quit": 		# finds route to cmd[1]
		print("\n > > > Adeus!\n")
		return -1
	else :
		print("\n > > > Comando desconhecido!\n")
		return 1


###############################################################################
###############################################################################
# decides what to do for received JSON. Returns JSON to send (if needed)
def resolve_rcv_json(data):
	messageJ = json.loads(data)

	if messageJ['type'] == "trace" :
		messageJ['hops'].push(UDP_ORIG_IP)
		if messageJ['destination'] == UDP_ORIG_IP:
			print("enviar messageJ de volta ao source como payload (~incompleto)")
			return trace_done(messageJ)
		else:
			print("enviar json pelo caminho mais curto até destination (~incompleto)")
			return continue_trace(messageJ)
	elif messageJ['type'] == "data" :
		if messageJ['destination'] == UDP_ORIG_IP:
			print("printar payload (incompleto)")
		else:
			print("enviar json pelo caminho mais curto até destination (incompleto)") 
	elif messageJ['type'] == "update" :
		print("atualizar distance_vector (incompleto)")
	

###############################################################################
###############################################################################
# creates JSON structure of type TYPEJ to destination DESTINATIONJ 
def build_json(typeJ,destinationJ,optJ=''):
	new_json = {'type' : typeJ, 'source': UDP_ORIG_IP, 'destination': destinationJ}
	if typeJ == "data":
		new_json['payload'] = optJ
	elif typeJ == "trace":
		new_json['hops'] = [UDP_ORIG_IP]
	elif typeJ == "update":
		new_json['distances'] = optJ

	return new_json


###############################################################################
###############################################################################
def start_trace(target_IP):
	return build_json("trace", target_IP)

###############################################################################
###############################################################################
# builds JSON to be sent back to trace's 
def trace_done(traceJ):
	return build_json("data",traceJ['source'], json.dumps(traceJ))

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

		#data, addr = udp_sock.recvfrom(1024) # buffer size is 1024 bytes

		#resolve_rcv_json(data)


		print("\n$ ", end='')
		if resolve_cmd_str(input(), distance_vector) < 0:
			break  
