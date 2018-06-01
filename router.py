#!/usr/bin/python3

import socket
import ast
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
thread_kill = False

###############################################################################
# dictionary { DESTINATION_IP : (<whom_to_send>, <weight>) }
# initialized with link to self
distance_vector = { UDP_ORIG_IP : (UDP_ORIG_IP, 0)}

###############################################################################
#UDP Socket
udp_sock = socket.socket(socket.AF_INET, 	# Internet
	                     socket.SOCK_DGRAM) 	# UDP
udp_sock.settimeout(2)
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
			distance_vector[cmd[1]] = (cmd[1], int(cmd[2]))
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
		# print("procurar rota para ", cmd[1], " ( incompleto )\n")
		send_via_udp(start_trace(cmd[1]))
		return 1
	elif cmd[0] == "quit": 		# stop the program
		print("\n > > > Adeus! Encerrando threads . . .\n")
		return -1
	else :
		print("\n > > > Comando desconhecido!\n")
		return 1


###############################################################################
###############################################################################
# decides what to do for received JSON. Returns JSON to send (if needed)
def resolve_rcv_json(data):
	# print("assfgfdhjljçk")
	messageJ = json.loads(data)
	if messageJ['type'] == "trace" :
		# print("trace received from ", messageJ['source'], "to", messageJ['destination'])
		# print(str(UDP_ORIG_IP), type(messageJ['hops']))
		messageJ['hops'].append(UDP_ORIG_IP)
		# print("aaaaaaa")
		if messageJ['destination'] == UDP_ORIG_IP:
			# print("enviar messageJ de volta ao source como payload (~incompleto)")
			return trace_done(messageJ)
		else:
			# print("enviar json pelo caminho mais curto até destination (~incompleto)")
			return messageJ
	elif messageJ['type'] == "data" :
		#print("rcv DATA")
		if messageJ['destination'] == UDP_ORIG_IP:	
			print(messageJ['payload'], "\n$ ", end='')
			return ''
		else:
			return messageJ
	elif messageJ['type'] == "update" :
		# print("rcv UPDATE")
		update_distance_vector(messageJ['distances'], messageJ['source'])
	else:
		print("MSG MAL FORMATADA")
	

###############################################################################
###############################################################################
# creates JSON structure of type TYPEJ to destination DESTINATIONJ 
def build_dict(typeJ,destinationJ,optJ=''):
	new_json = {'type' : typeJ, 'source': UDP_ORIG_IP, 'destination': destinationJ}
	if typeJ == "data":
		new_json['payload'] = optJ
	elif typeJ == "trace":
		new_json['hops'] = []
		new_json['hops'].append(UDP_ORIG_IP)
	elif typeJ == "update":
		new_json['distances'] = optJ

	return new_json


###############################################################################
###############################################################################
def start_trace(target_IP):
	return build_dict("trace", target_IP )


###############################################################################
###############################################################################
# builds JSON to be sent back to trace's 
def trace_done(traceJ):
	return build_dict("data",traceJ['source'], json.dumps(traceJ))

###############################################################################
###############################################################################
# handler to send dictionarys via UDP on JSON format
def send_via_udp(msg_to_send):
	global udp_sock, distance_vector
	neighbor = distance_vector[msg_to_send['destination']][0]
	udp_sock.sendto(str.encode(json.dumps(msg_to_send)), (neighbor,UDP_PORT))

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
		#print("chega aqui")
		if neighbor != UDP_ORIG_IP:
			udp_sock.sendto(str.encode(json.dumps(build_dict("update", str(neighbor), json.dumps(new_distance_vector)))), (neighbor,UDP_PORT))

###############################################################################
###############################################################################
def update_distance_vector(rcv_distance_vector, sender):
	global distance_vector
	rcv_distance_vector = ast.literal_eval(rcv_distance_vector)
	#print(type(rcv_distance_vector))
	for rcv_neighbor in rcv_distance_vector:
		#print ("value for ", rcv_neighbor)
		if(rcv_neighbor in distance_vector):
			# Updates distance of neighbors that sender and receiver can reach directly
			#print ("update ", rcv_neighbor)
			if distance_vector[sender][1] + int(rcv_distance_vector[rcv_neighbor][1]) < distance_vector[rcv_neighbor][1]: 
				distance_vector[rcv_neighbor] = (sender, int(rcv_distance_vector[rcv_neighbor][1]) + distance_vector[sender][1]) 
		else:
			#Updates distance of neighbors that receiver can't reach directly
			#print ("add ", rcv_neighbor)
			distance_vector[rcv_neighbor] = (sender, int(rcv_distance_vector[rcv_neighbor][1]) + distance_vector[sender][1])

###############################################################################
###############################################################################
def should_update_vector():
	global start
	while (True):
		if(thread_kill):
			break
		if(time.time() - start > TIME_TO_WAIT): 
			#print(time.time() - start)		
			send_update_message()
			start = time.time()
	#print("termina")

def receive_message():
	while (True):
		if(thread_kill):
			break
		try:
			message, addr = udp_sock.recvfrom(1024) #message is a string representation of JSON message
			message = message.decode()
			#print(message)
			if(message):
				msg_to_send = resolve_rcv_json(message)
				if msg_to_send != '' :
					send_via_udp(msg_to_send)
		except Exception as e:
			pass
			# print (e)

###############################################################################
###############################################################################
if __name__ == "__main__":
	global thread_kill

	# execute commands from input file
	if len(args) == 4:
		file = open(args[3], "r") 
		for line in file:
			resolve_cmd_str(line)
		file.close()

	thread_update = threading.Thread(target = should_update_vector, args = ())
	thread_listen = threading.Thread(target = receive_message, args = ())
	thread_listen.start()
	thread_update.start()

	while True:
		print("Atual vetor de distancias:\n", json.dumps(distance_vector))

		#data, addr = udp_sock.recvfrom(1024) # buffer size is 1024 bytes

		#resolve_rcv_json(data)
	
		#should_update_vector(time.time())
		
			
		print("\n$ ", end='')
		if resolve_cmd_str(input()) < 0:
			#thread_listen.join()
			#thread_update.join()
			thread_kill = True
			break  
	thread_listen.join()
	thread_update.join()