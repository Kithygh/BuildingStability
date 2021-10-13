import sys
import os.path
import winreg



# Get steam path from registry
# Check that path for the appmanifest
# If not there, look at libraryfolders.vdf for other folders to check
# Wherever the appmanifest exists, do some text manip to get the actual exe path

def getSteamLibraryFolders():
    hkey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\WOW6432Node\Valve\Steam")
    # print(hkey)
    steam_path = winreg.QueryValueEx(hkey, "InstallPath")
    # print(steam_path[0])
    folderList = []
    folderList.append(steam_path[0])
    # print(folderList)

    with open(steam_path[0]+"/steamapps/libraryfolders.vdf", "r") as f:
    # with open(steam_path[0]+"/steamapps/customlibraryfolders.vdf", "r") as f:  testing line
        content = f.read().splitlines()
        del content[-1:] #strips out closing brace
        del content[:4] # strips out title and opening brace 
        # print(content)
        for i in content:
            #print(i)
            i = i.replace("\t", "")
            i = i.replace("\"\"", "")
            i = i.replace("path", "")
            i = i.replace("\"", "")            
            #i = i.replace("\"", "")
            # i = i.replace(":\\", r":\")   This can't work. Can't escape trailing backslashes
            # print(i)
            if os.path.isdir(i):
                # print(i + " is a directory")
                folderList.append(i)
            #folderList.append(i[1:])
        # print(content)

    # for f in folderList:
    #     print(os.path.isdir(f))
    #     print(os.path.normpath(f))
    #print(folderList)
    #print("whereamI")
    return folderList
    winreg.CloseKey(hkey)

def folderOfMyApp(paths, appID):
    for dir in paths:
        # print(dir+r"\steamapps\appmanifest_" + appID + ".acf")
        if os.path.isfile(dir + r"\steamapps\appmanifest_" + appID + ".acf"):
            return (os.path.abspath(dir + r"\steamapps\common"))
        
if __name__ == "__main__":
    appID = "443030" # Conan Exiles Dedicated Server

    myPaths = getSteamLibraryFolders()
    # print(myPaths)

    # gameDir = folderOfMyApp(myPaths, appID)
    # print(gameDir)
    print("Game base directory is: " + folderOfMyApp(myPaths, appID))

# if os.path.isfile(steam_path[0]+"\\steamapps\\appmanifest_228981.acf"):
#     print("file found")
# else:
#     getSteamLibraryFolders(steam_path[0]+"\\steamapps\libraryfolders.vdf")


