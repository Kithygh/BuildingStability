import shutil
import os
import lzma
import sqlite3
import subprocess
import time
import argparse
import pathlib

from mcrcon import MCRcon
from datetime import datetime
from contextlib import closing

import steampath

def follow(thefile):
    thefile.seek(0, os.SEEK_END) # End-of-file
    while True:
        line = thefile.readline()
        if not line:
            time.sleep(0.1)
            continue
        yield line

def unzip_game_db(gamedbxz, db_source_dir) -> str:
    unzipped = gamedbxz[0:4]+"-unzipped.db"
    with open(unzipped, "wb") as out:
        with lzma.open(str(db_source_dir)+"\\"+gamedbxz) as f:
            file_content = f.read()
            out.write(file_content)
    print("Unzipped "+gamedbxz+" to "+unzipped)
    return unzipped

def launch_server_withdb(gamedb: str, game_folder: pathlib.Path, launch_options: str) -> None:
    # Open db and get the map column from actor_position table
    with closing(sqlite3.connect(gamedb)) as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM actor_position LIMIT 1")
        mapFromDB = cur.fetchall()
        map_column = mapFromDB[0][1]
        print("Mapcolumn shows: "+map_column)
    exe = pathlib.Path(game_folder.parent.parent, "ConanSandboxServer.exe")
    
    # Test the db for map type, copy file in and start the server
    match map_column:
        case "DLC_Isle_of_Siptah":        
            print(gamedb+" is a Siptah database")
            shutil.move(gamedb, os.path.abspath(str(game_folder) + r"\dlc_siptah.db"))
            print(f"Starting server as {str(exe)} /Game/DLC_EXT/DLC_Siptah/Maps/DLC_Isle_of_Siptah {launch_options}")
            subprocess.Popen(f"{str(exe)} /Game/DLC_EXT/DLC_Siptah/Maps/DLC_Isle_of_Siptah {launch_options}")
        case "ConanSandbox":
            print(gamedb+" is an Exiled Lands database")
            shutil.move(gamedb, os.path.abspath(str(game_folder) + r"\game.db"))
            print(f"Starting server as {str(exe)} {launch_options}")
            subprocess.Popen(f"{str(exe)} {launch_options}")
        case _:
            print(f"{gamedb} - {map_column}  is an unknown map. ABORT!")
            quit()

def wait_for_serverup(game_folder: pathlib.Path) -> None:
    # Checking for the server fully up and ready to run RCON commands
    time.sleep(10) # new log file wasn't always created yet
    log_path = pathlib.Path(game_folder, r"Logs\ConanSandbox.log")
    #print(log_path)
    print("Waiting for server...")
    with open(log_path) as logfile:
        loglines = follow(logfile)        
        for line in loglines:
            if "LogServerStats" in line:
                print("Server fully up")
                break

def run_mcrcon(rconcommand: str, rconpassword:str, rconport:int):
    max_attempts = 3
    for i in range(max_attempts):
        try:
            with MCRcon("127.0.0.1", rconpassword, port=rconport) as mcr:
                response = mcr.command(rconcommand)
                print(f"Received rcon response on attempt {i+1}")
                return response
        except:
            print(f"Try {i+1}/{max_attempts} failed to connect using {rconpassword=},  {rconport=}\n")
    return None

def check_stability(db_source_dir: pathlib.Path = None,
                    *,
                    game_folder: pathlib.Path = None,
                    rconpassword: str = "password",
                    rconport: str = 25575,
                    rconcommand: str = "validateallbuildings",
                    searched_error: str = "RemoveUnstableModules"
                    ) -> tuple[pathlib.Path, list[str]]:
    APPID = "443030" #Dedicated server appid
    if game_folder == None: # If we're not explicitly told a game folder, look for it.
        print(steampath.get_steam_folder(APPID))
        game_folder = pathlib.Path(steampath.get_steam_folder(APPID), r"Conan Exiles Dedicated Server\ConanSandbox\Saved")
    launch_options = f"-log -RconPassword={rconpassword} -RconPort={rconport}"    
    file_list = os.listdir(db_source_dir)
    print(f"Looking for files in : {db_source_dir}")

    zipped_file_list = [f for f in file_list if f.endswith(".xz")]
    print("Found the following zipped files:")
    for f in zipped_file_list:
        print(f)

    #Open report file
    with open(f"stability_report-{datetime.now().strftime('%Y-%m-%d-%H%M')}.log", "w") as report:
        report_summary = ["Report Summary:\n"]
        # Look at each database, run rcon command, search for specified error
        for database in zipped_file_list:
            report_error_count = 0
            # Open and uncompress the zipped file, write it locally
            localunzipped = unzip_game_db(database, db_source_dir)
            launch_server_withdb(localunzipped, game_folder, launch_options)
            wait_for_serverup(game_folder)
    
            # Run the RCON command to check buildings
            # report.write("Testing "+currdb[0:4]+"\n")
            report.write(f"Running {rconcommand} on {database[0:4]} \n")
            response = run_mcrcon(rconcommand, rconpassword, rconport)
            if None == response:
                report.write(f"Failed to connect to {database[0:4]}")
                report_summary.append(f"Failed to connect to {database[0:4]}\n")
            else:
                report.write(f"RCON command {rconcommand} response: {response}\n")

            # Shut down the server and wait for it to finish shutting down
            time.sleep(10) # wait for log to finish writing before we kill it. Get lines cut off otherwise.
            os.system("taskkill /f /im ConanSandboxServer-Win64-Test.exe") # force, imagename
            time.sleep(10) # wait for log to finish being written to
            
            # Open ConanSandbox.log and check for error lines            
            report_error_count = 0
            with open(str(game_folder) + r"\Logs\ConanSandbox.log", "r", encoding='utf8') as my_log:
                for line in my_log:
                    if searched_error in line:
                        report_error_count += 1
                        report.write(line.lstrip(".0123456789[ ]-:"))
            report.write(f"End testing of {localunzipped}\n")
            if response is not None:
                report_summary.append(f"{database}: {searched_error} {report_error_count}\n")

        for line in report_summary:
            report.write(line)
    return pathlib.Path(report.name), report_summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dbdir", help="Location of the zipped databases to analyze")
    parser.add_argument("--rconcommand", default="validateallbuildings", help="rcon command to run on server.")
    parser.add_argument("--rconport", default=25575, help="rcon port to start server with")
    parser.add_argument("--rconpassword", default="password", help="rcon password to start server with")
    parser.add_argument("--searchederror", default="RemoveUnstableModules", help="string to search log for")
    args = parser.parse_args()

    check_stability(db_source_dir=args.dbdir,
                    rconpassword=args.rconpassword,
                    rconport=args.rconport,
                    rconcommand=args.rconcommand,
                    searched_error=args.searchederror)