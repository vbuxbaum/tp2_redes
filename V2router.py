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
# dictionary { DESTINATION_IP : [ [<whom_to_send>, <weight>, <age>] , [ ... ] ] }
# initialized with link to self
distance_vector = { UDP_ORIG_IP : [ [UDP_ORIG_IP, 0, -1] ]}
linked = [ UDP_ORIG_IP ]

###############################################################################
#UDP Socket
udp_sock = socket.socket(socket.AF_INET, 	# Internet
	                     socket.SOCK_DGRAM) 	# UDP
udp_sock.settimeout(2)
# bind this port on local IP to UDP socket
udp_sock.bind((UDP_ORIG_IP, UDP_PORT))
# Global lock
lock = threading.RLock()



###############################################################################
###############################################################################
# decides what to do based on received command
def resolve_cmd_str(cmd):
	global distance_vector, linked

	cmd = cmd.split(" ")

	if cmd[0] == "add": 			# add cmd[1] in distance_vector with wheight cmd[2]
		try: 
			if(cmd[1] in distance_vector):
				distance_vector[cmd[1]].insert(0, [cmd[1], int(cmd[2]), -1] )
			else:
				distance_vector[cmd[1]] = [ [cmd[1], int(cmd[2]), -1] ]

			linked.append(cmd[1])
		except ValueError:
			print("\n > > > Escolha ruim de valores . . .\n")
		return 1
	elif cmd[0] == "del": 			# remove cmd[1] from distance_vector
		try:
			lock.acquire()
			#print("lock resolve_cmd_str acquired")

			linked.remove(cmd[1])
			del_connection(cmd[1])
			lock.release()
			#print("lock resolve_cmd_str released")

		except KeyError:
			print("\n > > > ConexÃ£o inexistente . . .\n")
		return 1
	elif cmd[0] == "trace": 		# finds route to cmd[1]
		# print("procurar rota para ", cmd[1], " ( incompleto )\n")
		try:
			#print(start_trace(cmd[1]))
			send_via_udp(start_trace(cmd[1]))
		except Exception as e:
			print("\n > > > NÃ£o foi possÃ­vel calcular rota . . .\n")
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
	# print("assfgfdhjljÃ§k")
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
			# print("enviar json pelo caminho mais curto atÃ© destination (~incompleto)")
			return messageJ
	elif messageJ['type'] == "data" :
		# print("rcv DATA")
		if messageJ['destination'] == UDP_ORIG_IP:	
			print(messageJ['payload'], "\n$ ", end='')
			return ''
		else:
			return messageJ
	elif messageJ['type'] == "update" :
		#print("rcv UPDATE")
		#print("lock resolve_rcv_json acquired")
		update_distance_vector(messageJ['distances'], messageJ['source'])
		#print("lock resolve_rcv_json released")
	
	else:
		print("MSG MAL FORMATADA")


###############################################################################
###############################################################################
# deletes all paths to
def del_connection(neighbour):
	global distance_vector
	delete_after = []
	for key in distance_vector:
		# update feasible paths to only those that do not include 'neighbour' 
		distance_vector[key] = [x for x in distance_vector[key] if x[0] != neighbour]
		
		# if no more paths, delete from distance vector
		if len(distance_vector[key]) == 0: 	
			delete_after.append(key)

	for key in delete_after:
		del distance_vector[key]


###############################################################################
###############################################################################
# Receives an distance vector and a key. LRU tuple has higher priority, coming
# at index 0. The list of tuples is still in ascending order by weight.
def sort_distance_vector(key):
	global distance_vector
	routes = distance_vector[key] #list of tuples
	index = 0
	weight = routes[0][1]
	while (index < len(routes)) and (weight == routes[index][1]):
		index += 1
	distance_vector[key].insert(index-1, routes.pop(0))


###############################################################################
###############################################################################
def get_mininum_dist_vector():
	global distance_vector
	new_distance_vector = {}
	for key in distance_vector: # get all neighbours
		#print(key,distance_vector[key])
		new_distance_vector[key] = distance_vector[key][0][0:2]
		#print("distance_vector[key][0][0:3]", distance_vector[key][0])
	return new_distance_vector


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
	if msg_to_send['destination'] in distance_vector:
		neighbour = distance_vector[msg_to_send['destination']][0][0]
	else:
		msg_to_send = build_dict("data", msg_to_send['source'], "ERRO: destino" + msg_to_send['destination'] + "nao encontrado no roteador" + UDP_ORIG_IP + "!!!")
		neighbour = distance_vector[msg_to_send['source']][0][0]

	#print(neighbour, msg_to_send['source'], msg_to_send['destination'])
	sort_distance_vector(neighbour)
	udp_sock.sendto(str.encode(json.dumps(msg_to_send)), (neighbour,UDP_PORT))


###############################################################################
###############################################################################
# Send an update Json message to each neighbour 
def send_update_message():
	global linked, distance_vector
	#print (distance_vector)
	
	for key in linked:	
		# distance_vector of A: [A, B, C]. When A sends update message to B, new_distance_vector of A:[C]
		if key != UDP_ORIG_IP: 
			new_distance_vector = get_mininum_dist_vector() 
			del new_distance_vector[key] 
			#new_distance_vector = {i:new_distance_vector[i] for i in new_distance_vector if }
			#del new_distance_vector[UDP_ORIG_IP]
			#print("chega aqui")
			#print("new_distance_vector",new_distance_vector)
			
			udp_sock.sendto(str.encode(json.dumps(build_dict("update", str(key), json.dumps(new_distance_vector)))), (key,UDP_PORT))


###############################################################################
###############################################################################
def update_distance_vector(rcv_distance_vector, sender):
	global distance_vector

	rcv_distance_vector = ast.literal_eval(rcv_distance_vector)
	sender_weight = distance_vector[sender][0][1]
	#print("sender_weight",sender_weight)

	for rcv_neighbour in rcv_distance_vector:

		rcv_weight = int(rcv_distance_vector[rcv_neighbour][1])
		#print("rcv_weight",rcv_weight)

		if(rcv_neighbour in distance_vector ):
			#print("a")

			# caso já haja rotas para o destino: CONFERE SE NOVA ROTA É MELHOR
			curr_dest_weight =  distance_vector[rcv_neighbour][0][1]
			#print("b")

			distance_vector[rcv_neighbour] = [x for x in distance_vector[rcv_neighbour] if (x[0] != sender and x[2] >=0)]
			#print("c")
			if (sender_weight + rcv_weight <= curr_dest_weight):
				#print("d")
				# caso a rota nova seja a menos custosa: INSERE NO INICIO DA LISTA DE ROTAS
				if not (sender_weight + rcv_weight == curr_dest_weight and distance_vector[rcv_neighbour][0][2] == -1):
					#print("e")
					distance_vector[rcv_neighbour].insert(0, [sender, rcv_weight + sender_weight, 0] )

			else:
				# caso a rota nova seja mais custosa: INSERE NO FINAL DA LISTA DE ROTAS
				#print("f")
				distance_vector[rcv_neighbour].append([sender, rcv_weight + sender_weight, 0])
		else:
			#print("g")
			distance_vector[rcv_neighbour] = [ [sender, rcv_weight + sender_weight , 0] ]
	#print("h")


###############################################################################
###############################################################################
def age_routes():
	global distance_vector
	delete_after = []
	for key in distance_vector:
		# age every route
		for route in distance_vector[key]:
			if route[2] != -1:
				route[2] += 1
		# update feasible paths to only those that have age <= 4
		distance_vector[key] = [x for x in distance_vector[key] if x[2] <= 4]
		if len(distance_vector[key]) == 0: 	
			delete_after.append(key)

	for key in delete_after:
		del distance_vector[key]
				


###############################################################################
###############################################################################
def should_update_vector():
	global start
	while (True):
		if(time.time() - start >= TIME_TO_WAIT): 
			start = time.time()

			#print("lock should_update_vector acquired")
			send_update_message()
			lock.acquire()
			age_routes()			
			lock.release()
			#print("lock should_update_vector released")
		elif(thread_kill):
			break
	#print("termina")


###############################################################################
###############################################################################
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

	global thread_kill
	while True:
		# shows the most recently used distance vector
		print("Atual vetor de distancias:\n", json.dumps(get_mininum_dist_vector()))

		#data, addr = udp_sock.recvfrom(1024) # buffer size is 1024 bytes

		#resolve_rcv_json(data)
	
		#should_update_vector(time.time())
		
			
		print("\n$ ", end='')
		if resolve_cmd_str(input()) < 0:
			thread_kill = True
			break

	thread_listen.join()
	thread_update.join()

	udp_sock.close()
