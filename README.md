# Connect 4 - Concurrent & Distributed Programming Project

## Road Map

- [x] Login & Sign up pages (back REST API & front)
  - [x] Login connected and works (simple)
  - [x] Register connected
  - [x] Error handling
  - [x] Logout
  - [x] Redirect to game and login page (IsAuth)
  - [x] Background refresh token
- [x] Manual game room creation (channels & web sockets)
  - [x] Revisit messages on join
  - [x] Leave room event
  - [x] Both players can rejoin room
- [x] Game implementation frontend interface
  - [x] Board is clickable
  - [x] On click send move via socket
  - [x] Update board from received response
  - [x] State updates on game won
- [ ] Game logic implementation backend (move validation ...)
  - [x] Store board state in DB
  - [x] Socket receive move info & update state
  - [x] Check & process win condition 
  - [ ] Validate correct user moves
- [ ] Database expansion - redis for channels & board representation, moves log
  - [x] Change default DB to PostgreSql
  - [x] Add Redis for channels management  
- [ ] MinMax bot opponent
  - [x] Base bot endpoint
  - [ ] Front end implementation
  - [ ] Possible player bot game room
  - [ ] Implementation of MinMax alg
- [ ] ? Match making queue (private games & public games)

## Evaluation Criteria
1. Implementation [12 points]
   - correct implementation of methods allowing client-server communication
   - appropriate use of multithreading or/and multiprocessing
   - application of protections in case of connection breaks
   - level of difficulty of implementing the rules of the game
   - appropriate locks and messages relating to incorrect game movement
   - quality of written code
   - user interface (console is sufficient);
2. demonstration of the game [5 points] 
   - presentation of the course of the game;
   - justification for the use of particular communication methods;
   - presentation of the UI and methods to prevent non-compliant movements;
3. documentation README [3 points]
   - a brief description of the game
   - description of the project's file structure
   - listing the methods used in concurrent programming
   - list of external libraries/frameworks used
   - screenshots of the game
   - a description of the contributions of individual group members
