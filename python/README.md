### Create bucket
``` 
gsutil mb -p YOUR_PROJECT_ID -c nearline -l REGION gs://YOUR_BUCKET_NAME/ 
```

### Apply Lifecycle policy to bucket

You will fine the lifecycle policy already created in the root folder.  Right now it is set to 14 days but this can be editted to whatever is preferred.

```
gsutil lifecycle set gcs-lifecycle.json gs://YOUR_BUCKET_NAME/
```

## Create GCP secret with FTP credentials
First, create a file with your FTP creds that just looks like this:
```
server=
username=
password=
```
Then run the bellow command:
```
gcloud secrets create SECRET_NAME --data-file=<PATH TO FTP CREDENTIAL FILE>
```

### Run python script with require arguments
Be sure to change the arguments to match your environment.  I have left some example entries for what was used for Conan Exiles
```
python /python/gportal-backup.py --gcs_bucket "YOUR_BUCKET_NAME" --secret_name "gportal-ftp-credentials" --remote_dir "/ConanSandbox/Saved" --local-dir "/tmp/conan" --project-id "PROJECT-ID" 
```

</br>
</br>
</br>

## Coming Soon

### Docker
```
IMAGE_NAME=
REPO_LOCATION=


docker build -t $IMAGE_NAME .

docker tag $IMAGE_NAME $REPO_URL/$IMAGE_NAME:latest

docker push $REPO_URL/$IMAGE_NAME:latest
```
```
docker run -d \
--name=gportal-backup-image \
-e "GCS_BUCKET=<BUCKET_NAME>" \
-e "SECRET_NAME=gportal-ftp-credentials" \
-e "REMOTE_DIR=/ConanSandbox/Saved" \
-e "LOCAL_DIR=/tmp/conan" \
-e "PROJECT_ID=<PROJECT_ID>" \
gportal-backup-image
```