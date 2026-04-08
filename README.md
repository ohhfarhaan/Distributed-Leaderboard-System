# Distributed Leaderboard System (Secure Version)

A real-time distributed leaderboard system using TCP sockets and SSL/TLS encryption.

## Features

- Client-server architecture using TCP sockets
- Secure communication using SSL/TLS
- Multiple clients can connect simultaneously
- Real-time leaderboard updates
- Persistent storage using JSON file
- GUI client using tkinter

## Technologies Used

- Python
- Socket Programming
- SSL/TLS Encryption
- Multithreading
- JSON for data storage
- Tkinter for GUI

## How it Works

1. Server starts and listens for connections
2. Client connects securely using SSL/TLS
3. Client sends team name and score
4. Server stores highest score in leaderboard.json
5. Server broadcasts updated leaderboard to all connected clients
6. Clients update leaderboard in real-time

## File Structure

server.py → Secure TCP server with SSL  
client.py → GUI client with SSL connection  
leaderboard.json → Stores scores persistently  
cert.pem → SSL certificate  
key.pem → SSL private key  

## Run Instructions

Start server:

python server.py

Start client:

python client.py

## Concepts Implemented

- TCP Socket Programming
- SSL/TLS Secure Communication
- Client-Server Architecture
- Multithreading
- JSON Data Storage
- Real-time Data Broadcasting

## Security

All communication between client and server is encrypted using SSL/TLS.

Self-signed certificates are used for secure communication.