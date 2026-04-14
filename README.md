# Connect 4 - Concurrent & Distributed Programming Project

## Road Map

- [ ] Login & Sign up pages (back REST API & front)
  - [x] Login connected and works (simple)
  - [x] Register connected
  - [x] Error handling
  - [ ] Logout
  - [x] Redirect to game and login page (IsAuth)
- [ ] Manual game room creation (channels & web sockets)
- [ ] Game implementation frontend interface
- [ ] Game logic implementation backend (move validation ...)
- [ ] Database expansion - redis for channels & board representation, moves log
- [ ] ? Match making queue (private games & public games)
- [ ] ? MinMax bot opponent

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
