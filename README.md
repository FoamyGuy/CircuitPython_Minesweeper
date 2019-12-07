# CircuitPython_Minesweeper
This example game is a fiarly standard implementation of Minesweeper. 

The player controls a cursor with the D-Pad. Then uses the B button to flag, and the A button to reveal the currently selected tile.

Once the game is over due to winning or losing you can look around the revealed board. Press the A button to start a new game. 

Internally the game works similarly to the [CSV Tilemap Example](https://hackaday.io/project/168653-csv-tilemap-game), the same TILES dictionary structure and PLAYER_LOC system is used in this game. However the maps are generated randomly rather than read from CSV files, and there are less restrictions on the "player" since it's actually a cursor in this game so the movement is simplified.

The game defualt settings are 12x10 board size and 12 bombs. You can change the variables near the top of the file to change the settings to whatever you like though. We support board sizes larger than the screen by using the same CAMERA_VIEW technique from the Tilemap game example. 