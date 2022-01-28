import os
import shutil
import pathlib
import subprocess
import difflib
from datetime import datetime
from ast import literal_eval

import sendStabilityMail
import GetLiveDBs
import BuildingStablityChecker

def move_old_dbs(): # rename the current ZippedDBs to zipped old
    shutil.move("ZippedDBs/", "OldZippedDBs/")
    os.makedirs("ZippedDBs/")

def get_version(install_dir: pathlib.Path) -> tuple[str,str]:
    revision, snapshot = None, None
    with open(str(install_dir) + r"\ConanSandbox\Saved\Logs\ConanSandbox.log", "r", encoding='utf8') as log:
        for line in log:
            if "Dreamworld revision" in line:
                revision = line.split().pop()
            if "Dreamworld snapshot" in line:
                snapshot = line.split().pop()
            if (revision and snapshot): # exit early, don't need to go through whole log
                return revision, snapshot

def steamcmd_update(branch: str, steam_config: dict) -> None:
    install_dir = f"{steam_config['install_dir']}\\branch-{branch}"
    branch_pwd = steam_config["branch_pwds"][branch]
    steamcmd_path = steam_config["executable_path"]
    beta_info = f"-beta {branch} -betapassword {branch_pwd}"
    steamcmd_command = f"{steamcmd_path} +force_install_dir {install_dir} +login anonymous +app_update 443030 {beta_info} {branch_pwd} +quit"
    print(steamcmd_command)
    subprocess.run(steamcmd_command)


def main():
    compared_branch = "exiles-development"
    GetLiveDBs.GetDBs() # run getlivedbs, defaults are fine
    with open("steamcmd.config", "r") as f:
        s = f.read()
        steam_config = literal_eval(s)
    steamcmd_update("default", steam_config) # update default branch

    # run buildingstabilitychecker on live install
    live_install_dir = pathlib.Path(steam_config["install_dir"], "branch-default")
    print(live_install_dir)
    _, live_report_summary = BuildingStablityChecker.check_stability(pathlib.Path("ZippedDBs/"),
                                            game_folder=pathlib.Path(live_install_dir, "ConanSandbox", "Saved"),
                                            rconpassword="password",
                                            rconport=25575,
                                            rconcommand="validateallbuildings",
                                            searched_error="RemoveUnstableModules")

    # steamcmd to update beta install
    steamcmd_update(compared_branch, steam_config)

    # run buildingstabilitychecker on beta install
    beta_install_dir = pathlib.Path(steam_config["install_dir"], f"branch-{compared_branch}")
    _, beta_report_summary = BuildingStablityChecker.check_stability(
                            pathlib.Path("ZippedDBs/"),
                            game_folder=pathlib.Path(beta_install_dir, "ConanSandbox", "Saved"),
                            rconpassword="password",
                            rconport=25575,
                            rconcommand="validateallbuildings",
                            searched_error="RemoveUnstableModules")
    
    # Get version/snapshot
    rev, snap = get_version(live_install_dir)
    live_version = f"live-{rev}/{snap}"
    rev, snap = get_version(beta_install_dir)
    beta_version = f"{compared_branch}-{rev}/{snap}"

    with open(f"diff-{datetime.now().strftime('%Y-%m-%d')}.log", "w") as diff_report:
        if beta_report_summary == live_report_summary:
            message = f"No differences found between {live_version} and {beta_version}"
        else:
            message = f"Differences found between {live_version} and {beta_version}:\n"
            for line in difflib.unified_diff(live_report_summary, beta_report_summary, n=0):
                print(f"{line=}")
                if ("---" in line) or ("+++" in line) or(line.startswith("@@")):
                    pass
                else:
                    message += line
                    diff_report.write(line)

    # send report to trigger@applet.ifttt.com
    sendStabilityMail.send_mail(message)

if __name__ == "__main__":
    main()