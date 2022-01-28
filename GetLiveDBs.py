import datetime
import paramiko
import stat


def GetDBs(count = 10, config_file="ssh.config", server_name="odin", keyfile="id_rsa", passphrase_file="passphrase"):
    with paramiko.SSHClient() as ssh:
        folder_name = "/mnt/exiles-DB/" + (datetime.datetime.now() - datetime.timedelta(2)).strftime("%Y-%m-%d")
        #print(folder_name)
        with open(passphrase_file) as f:
            sftpPass = f.readline()
        key = paramiko.RSAKey(filename=keyfile, password=sftpPass)
        config = paramiko.SSHConfig.from_file(open(config_file))
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        #ssh.connect(sftpURL, username=sftpUser, passphrase=sftpPass, pkey=key)
        ssh.connect(**(config.lookup(server_name)), pkey=key)
        sftp = ssh.open_sftp()
        files = [file for file in sftp.listdir_attr(path=f"{folder_name}")
            if (stat.S_ISREG(file.st_mode) and file.filename.endswith(".xz"))]
        files.sort(key=lambda x: x.st_size, reverse=True) # getting big dbs for testing large buildings.
        #files.sort(key=lambda x: x.st_size) # getting small for testing scripts
        for progress, file in enumerate(files[:count]):
            print(f"Downloading {file.filename} size:{file.st_size} ({progress+1} / {count})")
            sftp.get(f"{folder_name}/{file.filename}", f'ZippedDBs/{file.filename}')

if __name__ == "__main__":
    GetDBs()