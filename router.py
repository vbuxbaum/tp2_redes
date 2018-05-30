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
start = time.time()

###############################################################################
# dictionary { DESTINATION_IP : (<whom_to_send>, <weight>) }
# initialized with link to self
distance_vector = { UDP_ORIG_IP : (UDP_ORIG_IP, 0)}

###############################################################################
#UDP Socket
udp_sock = socket.socket(socket.AF_INET, 	# Internet
	                     socket.SOCK_DGRAM) 	# UDP

# bind this port on local IP to UDP socket
udp_sock.bind((UDP_ORIG_IP, UDP_PORT))

###############################################################################
###############################################################################

# decides what to do based on received command
def resolve_cmd_str(cmd):
	global distance_vector

	cmd = cmd.split(" ")

	if cmd[0] == "add": 			# add cmd[1] in distance_vector with wheight cmd[2]
		try: 
			distance_vector[cmd[1]] = (UDP_ORIG_IP, int(cmd[2]))
		except ValueError:
			print("\n > > > Escolha ruim de valores . . .\n")
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
	elif cmd[0] == "quit": 		# stop the program
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
			return messageJ
	elif messageJ['type'] == "data" :
		if messageJ['destination'] == UDP_ORIG_IP:
			print("printar payload (incompleto)")
		else:
			print("enviar json pelo caminho mais curto até destination (incompleto)") 
	elif messageJ['type'] == "update" :
		print("disparar thread")
		update_distance_vector(messageJ['distances'])
	

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

	return json.dumps(new_json)


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

# Send an update Json message to each neighbor
def send_update_message():
	global distance_vector
	for neighbor in distance_vector: # get all neighbors
		# distance_vector of A: [A, B, C]. When A sends update message to B, new_distance_vector of A:[C]
		new_distance_vector = dict(distance_vector) 
		del new_distance_vector[neighbor] 
		#del new_distance_vector[UDP_ORIG_IP]
		udp_sock.sendto(bytes(build_json("update", str(neighbor), json.dumps(new_distance_vector)), "utf-8"), (neighbor,UDP_PORT))

###############################################################################
###############################################################################
def update_distance_vector(rcv_distance_vector):
	global distance_vector

	sender = rcv_distance_vector.keys()[0]
	for rcv_neighbor in rcv_distance_vector:
		if(distance_vector.has_key(rcv_neighbor)):
			# Updates distance of neighbors that sender and receiver can reach directly
			if distance_vector[sender][1] + rcv_distance_vector[rcv_neighbor][1] < distance_vector[rcv_neighbor][1]: 
				distance_vector[rcv_neighbor] = (sender, rcv_distance_vector[rcv_neighbor][1] + distance_vector[sender][1]) 
		else:
			#Updates distance of neighbors that receiver can't reach directly
			distance_vector[rcv_neighbor] = (sender, rcv_distance_vector[rcv_neighbor][1] + distance_vector[sender][1])

###############################################################################
###############################################################################
def should_update_vector(rcv_time):
	global start
	#while (True):
	if(rcv_time - start > TIME_TO_WAIT): 
		#print(rcv_time - start)		
		send_update_message()
		start = time.time()

###############################################################################
###############################################################################
if __name__ == "__main__":

	# execute commands from input file
	if len(args) == 4:
		file = open(args[3], "r") 
		for line in file:
			resolve_cmd_str(line, distance_vector)
		file.close()

	#thread = threading.Thread(target = should_update_vector, args = (time.time(),))
	#thread.start()
	while True:
		print("Atual vetor de distancias:\n", json.dumps(distance_vector))

		#data, addr = udp_sock.recvfrom(1024) # buffer size is 1024 bytes

		#resolve_rcv_json(data)
	
		should_update_vector(time.time())
		#message, addr = udp_sock.recvfrom(1024) #message is a string representation of JSON message
		#if(message):
		try:
			resolve_rcv_json(message)
		except Exception:
			pass
			
		print("\n$ ", end='')
		if resolve_cmd_str(input()) < 0:
			#thread.join()
			break  
