import winreg
import pathlib
import re

# Get steam path from registry
# Check steam path and paths in libraryfolders.vdf
# Determine the folder that has the appmanifest for the appid given
# Return the base steam library folder for the app

def steam_library_folders() -> list:
    hkey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\WOW6432Node\Valve\Steam")   
    steam_path = winreg.QueryValueEx(hkey, "InstallPath")[0]
    library_folders = pathlib.Path(steam_path, r"steamapps/libraryfolders.vdf")
    folderList = []
    folderList.append(steam_path)

    with library_folders.open() as f:
        for line in f:
            if "path" in line:
                possible_path = pathlib.Path(re.search(r"""(?<="path"\t\t").*(?=")""", line).group(), "steamapps")
                folderList.append(possible_path)
    winreg.CloseKey(hkey)
    return folderList    

def get_steam_folder(appID: str) -> pathlib.Path:
    for dir in steam_library_folders():
        p = pathlib.Path(dir).joinpath(f"appmanifest_{appID}.acf")
        if p.exists():
            return pathlib.Path(dir,"common")

def main() -> None:
    appID = "443030" # Conan Exiles Dedicated Server
    print(f"Game base directory is: {get_steam_folder(appID)}")

if __name__ == "__main__":
   main()