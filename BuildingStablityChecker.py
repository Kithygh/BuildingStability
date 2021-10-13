import shutil
import os
import lzma
import sqlite3
import subprocess
import time
import argparse
import winreg
import steampath
from mcrcon import MCRcon
from datetime import datetime

def follow(thefile):
    thefile.seek(0, os.SEEK_END) # End-of-file
    while True:
        line = thefile.readline()
        if not line:
            time.sleep(0.1)
            continue
        yield line

def launch_dedicated_server(gamedb):
            # Open db and get the map column from actor_position table
        con = sqlite3.connect(gamedb)
        cur = con.cursor()
        cur.execute("SELECT * FROM actor_position LIMIT 1")
        mapFromDB = cur.fetchall()
        mapColumn = mapFromDB[0][1]
        con.close()
        print("Mapcolumn shows: "+mapColumn)

        # Test the db for map type, copy file in and start the server
        if "DLC_Isle_of_Siptah" == mapColumn:
            print(gamedb+" is a Siptah database")
            shutil.move(gamedb, os.path.abspath(game_folder + r"\Conan Exiles Dedicated Server\ConanSandbox\Saved\dlc_siptah.db"))
            print("Starting server as ")
            print(siptah_start)
            subprocess.Popen(siptah_start)
        elif "ConanSandbox" == mapColumn:
            print(gamedb+" is an Exiled Lands database")
            shutil.move(gamedb, os.path.abspath(game_folder + r"\Conan Exiles Dedicated Server\ConanSandbox\Saved\game.db"))
            print("Starting server as ")
            print(exiled_start)
            subprocess.Popen(exiled_start)
        else:
            print(gamedb + " is an unknown map. ABORT!")
            quit()

def wait_for_serverup():
    # Checking for the server fully up and ready to run RCON commands
    time.sleep(60) # new log file wasn't always created yet
    logfile = open(game_folder + r"\Conan Exiles Dedicated Server\ConanSandbox\Saved\Logs\ConanSandbox.log")
    loglines = follow(logfile)
    print("Waiting for server...")
    for line in loglines:
        # print(line, end='')
        if "LogServerStats" in line:
            print(line, end='')
            print("Server fully up")
            break

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dbdir", help="Location of the zipped databases to analyze")
    parser.add_argument("--rconcommand", default="validateallbuildings", help="rcon command to run on server.")
    parser.add_argument("--rconport", default=25575, help="rcon port to start server with")
    parser.add_argument("--rconpassword", default="password", help="rcon password to start server with")
    parser.add_argument("--searchederror", default="RemoveUnstableModules", help="string to search log for")
    args = parser.parse_args()
   
    db_source_dir = args.dbdir
    
    APPID = "443030" #Dedicated server appid

    game_folder = steampath.folderOfMyApp(steampath.getSteamLibraryFolders(), APPID)
    # game_folder = os.path.abspath(game_folder)

    # Crafting the server startup lines
    siptah_start = [game_folder + r"\Conan Exiles Dedicated Server\ConanSandboxServer.exe", "/Game/DLC_EXT/DLC_Siptah/Maps/DLC_Isle_of_Siptah"]
    exiled_start = [game_folder + r"\Conan Exiles Dedicated Server\ConanSandboxServer.exe"]
    siptah_start.append("-log")
    siptah_start.append("-RconPassword="+args.rconpassword)
    siptah_start.append("-RconPort=%d" %args.rconport)
    exiled_start.append("-log")
    exiled_start.append("-RconPassword="+args.rconpassword)
    exiled_start.append("-RconPort=%d" %args.rconport)

    file_list = os.listdir(db_source_dir)
    

    # Report setup
    searched_error = args.searchederror
    report_error_count = 0
    report_summary = ["Report Summary:\n"]

    # print(db_source_dir)
    # print(game_folder)
    print("Looking for files in : "+db_source_dir)


    # just get zipped files, not dirs or any other crap
    zipped_file_list = []
    for f in file_list:
        if f.endswith(".xz"):
            zipped_file_list.append(f)
    print("Found the following zipped files:")
    for f in zipped_file_list:
        print(f)


    #Open report file
    now = datetime.now()
    #currentrunlog = now.strftime("%Y-%m%d-%H%M")
    report = open("stability_report-"+now.strftime("%Y-%m-%d-%H%M")+".log", "w")
    #report = open(r"C:\Users\hygha\Documents\StabilityTesting\ExilesDBs"+"stability_report-"+now.strftime("%Y-%m-%d-%H%M")+".log", "w")
    #report = open("report"+currentrunlog+".log", "w")

    for currdb in zipped_file_list:

        report_error_count = 0
        # Open and uncompress the zipped file, write it locally
        localunzipped = currdb[0:4]+"-unzipped.db"
        out = open(localunzipped, "wb")
        with lzma.open(db_source_dir+"\\"+currdb) as f:
            file_content = f.read()
        out.write(file_content)
        out.close()
        print("Unzipped "+currdb+" to "+localunzipped)

        launch_dedicated_server(localunzipped)
        wait_for_serverup()
 
        # Run the RCON command to check buildings
        # report.write("Testing "+currdb[0:4]+"\n")
        report.write("Running " + args.rconcommand + " on " + currdb[0:4]+"\n")
        with MCRcon("127.0.0.1", args.rconpassword, port=args.rconport) as mcr:
            resp = mcr.command(args.rconcommand)
            report.write(resp+"\n")
            print(f"RCON command {args.rconcommand} response: {resp}")

        # Shut down the server and wait for it to finish shutting down
        time.sleep(10) # wait for log to finish writing before we kill it. Get lines cut off otherwise.
        os.system("taskkill /f /im ConanSandboxServer-Win64-Test.exe") # force, imagename

        # Open ConanSandbox.log and check for error lines
        time.sleep(10) # wait for log to finish being written to
        report_error_count = 0
        with open(game_folder + r"\Conan Exiles Dedicated Server\ConanSandbox\Saved\Logs\ConanSandbox.log", "r", encoding='utf8') as my_log:
            for line in my_log:
                if searched_error in line:
                    report_error_count += 1
                    report.write(line)                    
                    
        time.sleep(5)
        report.write("End testing of "+localunzipped+"\n")

        report_summary.append(f"{currdb}: {searched_error} {report_error_count}\n")

    for line in report_summary:
        report.write(line)
    report.close()



