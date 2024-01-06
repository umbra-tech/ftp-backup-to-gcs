import os
import subprocess
import base64
import datetime
import pytz
import argparse
import shutil
from google.cloud import secretmanager

# Constants
TIMEZONE = "America/Chicago"

# Initialize the Secret Manager client
client = secretmanager.SecretManagerServiceClient()

def get_secret(project_id, secret_name):
    name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

def create_backup(ftp_username, ftp_password, ftp_server, local_dir, temp_dir, remote_dir, gcs_bucket):
    timestamp = datetime.datetime.now(pytz.timezone(TIMEZONE)).strftime("%Y%m%d%H%M")
    tar_file = f"backup_{timestamp}.tar.gz"
    gcs_object_name = f"conan_{timestamp}.tar.gz"

    # Connect to FTP server and download the directory recursively
    subprocess.run(["lftp", "-e", f"mirror --verbose {remote_dir} {local_dir}; quit", "-u", f"{ftp_username},{ftp_password}", ftp_server])

    # Create a tar archive of the local directory
    subprocess.run(["tar", "-czvf", os.path.join(temp_dir, tar_file), "-C", local_dir, "."])

    # Upload the tar archive to GCS
    subprocess.run(["gsutil", "cp", os.path.join(temp_dir, tar_file), f"gs://{gcs_bucket}/{gcs_object_name}"])

    # Clean up temporary files
    os.remove(os.path.join(temp_dir, tar_file))
    shutil.rmtree(local_dir)

    print(f"Backup completed and uploaded to GCS: {gcs_object_name}")

def main():
    parser = argparse.ArgumentParser(description='FTP to GCS backup script')
    parser.add_argument('--project_id', required=True, help='Google Cloud project ID')
    parser.add_argument('--secret_name', required=True, help='Secret name in Google Cloud Secret Manager')
    parser.add_argument('--local_dir', required=True, help='Local directory to archive')
    parser.add_argument('--remote_dir', required=True, help='Remote directory on FTP server')
    parser.add_argument('--gcs_bucket', required=True, help='Google Cloud Storage bucket name')
    parser.add_argument('--temp_dir', default='/tmp/', help='Temporary directory for tar archive (default: /tmp/)')

    args = parser.parse_args()

    secret = get_secret(args.project_id, args.secret_name)
    creds = dict(line.split('=') for line in secret.splitlines())
    ftp_username = creds.get("username")
    ftp_password = creds.get("password")
    ftp_server = creds.get("server")

    if ftp_username and ftp_password and ftp_server:
        create_backup(ftp_username, ftp_password, ftp_server, args.local_dir, args.temp_dir, args.remote_dir, args.gcs_bucket)
    else:
        print("Failed to retrieve FTP credentials from Secret Manager.")

if __name__ == "__main__":
    main()

