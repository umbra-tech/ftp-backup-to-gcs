## Automated Task in GCP
The following serries of commands will help you to build a completely automated solution in GCP for very little cost.

* Create a project in GCP.  (All these steps can be performed through Cloud Shell as well)

* Clone down repository and enter folder
    ```
    git clone https://github.com/umbra-tech/gcs-ftp-backup.git
    cd gcs-ftp-backup
    ```

* Authenticate to GCP
```
gcloud auth login
```

* Set Variables:
    (The BACKUP_SCHEDULE is set in unix cron format https://cloud.google.com/scheduler/docs/configuring/cron-job-schedules#defining_the_job_schedule)
    ```
    JOB_NAME=daily-ftp-backup
    IMAGE_NAME=ftp-backup-image  
    PROJECT_ID=gcp_project_id
    REGION=us-central1
    GCS_BUCKET=bucket_name
    SECRET_NAME=secret_name
    REMOTE_DIR=/path/on/ftp
    LOCAL_DIR=/tmp/backup
    BACKUP_SCHEDULE="0 */6 * * 0-6"
    TIMEZONE="America/Chicago"
    ```

* Enable needed APIs in GCP
    ```
    gcloud config set project $PROJECT_ID
    gcloud services enable \
        artifactregistry.googleapis.com \
        storage.googleapis.com \
        run.googleapis.com \
        cloudscheduler.googleapis.com \
        compute.googleapis.com
    ```

* Create bucket:
    ``` 
    gsutil mb -p $PROJECT_ID -c nearline -l $REGION gs://$GCS_BUCKET/ 
    ```

* Apply Lifecycle policy to bucket:

    (You will find the lifecycle policy already created in the root folder.  Right now it is set to 14 days but this can be editted to whatever is preferred.)
    ```
    gsutil lifecycle set gcs-lifecycle.json gs://$GCS_BUCKET/
    ```

* Create GCP secret with FTP credentials:

    * Edit the ftp-creds file and fill in the required info, then run the command below:
    ```
    gcloud secrets create $SECRET_NAME --data-file=/ftp-creds
    ```

* Create Artifact Registry
    ```
    gcloud artifacts repositories create $JOB_NAME \
        --repository-format=docker \
        --location=$REGION \
        --description="Docker repository for $JOB_NAME"
    ```

* Create Docker image and upload to Artifact Registry
    ```
    REPO_URL=$REGION-docker.pkg.dev/$PROJECT_ID/$JOB_NAME/

    docker build -t $IMAGE_NAME .

    docker tag $IMAGE_NAME $REPO_URL/$IMAGE_NAME:latest

    docker push $REPO_URL/$IMAGE_NAME:latest
    ```

* Create Service Account and assign it permissions
    1. Create Service Account
        ```
        gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
          --description="Service account for Cloud Run job" \
          --display-name="$SERVICE_ACCOUNT_NAME"
        ```
    2. Assign the Artifact Registry Reader Role
        ```
        gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
        --role="roles/artifactregistry.reader"
        ```
    3. Assign the Storage Admin Role to the Storage Bucket
        ```
        gsutil iam ch serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com:roles/storage.admin gs://$GCS_BUCKET
        ```
    4. Assign the Cloud Run Invoker Role
        ```
        gcloud projects add-iam-policy-binding $PROJECT_ID \
            --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
            --role="roles/run.invoker"
        ```
    5. Assign the Secret Accessor Role to the created secret
        ```
        gcloud secrets add-iam-policy-binding $SECRET_NAME \
            --project=$PROJECT_ID \
            --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
            --role="roles/secretmanager.secretAccessor"
        ```


* Create Cloud Run Job:
    ```
    gcloud beta run jobs create $JOB_NAME \
        --image=$REPO_URL/$IMAGE_NAME:latest \
        --set-env-vars= \
            GCS_BUCKET=$GCS_BUCKET, \
            SECRET_NAME=$SECRET_NAME, \
            REMOTE_DIR=$REMOTE_DIR, \
            LOCAL_DIR=$LOCAL_DIR, \
            PROJECT_ID=$PROJECT_ID \
        --region=$REGION \
        --cpu=1000m \  # Increase if needed
        --memory=4Gi \ # Increase if needed
        --service-account=$SERVICE_ACCOUNT 
    ```

* Create Cloud Scheduler task to trigger with Cloud Run job
    ```
    gcloud scheduler jobs create http conan-backup-job-scheduler-trigger \
        --project=$PROJECT_ID \
        --location=$REGION \
        --schedule=$BACKUP_SCHEDULE \
        --time-zone=$TIMEZONE \
        --http-method=POST \
        --headers=User-Agent=Google-Cloud-Scheduler \
        --uri="https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
        --oauth-service-account-email=$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com \
        --oauth-token-scope="https://www.googleapis.com/auth/cloud-platform" \
        --max-backoff=3600s \
        --min-backoff=5s \
        --max-doublings=5 \
        --attempt-deadline=180s
    ```


## Alternative Setup Methods

### <ins>Prerequisites</ins>
* Clone repo
    ```
    git clone https://github.com/umbra-tech/gcs-ftp-backup.git
    cd gcs-ftp-backup
    ```

* Create bucket
    ``` 
    gsutil mb -p YOUR_PROJECT_ID -c nearline -l REGION gs://YOUR_BUCKET_NAME/ 
    ```

* Apply Lifecycle policy to bucket

    You will find the lifecycle policy already created in the root folder.  Right now it is set to 14 days but this can be editted to whatever is preferred.

    ```
    gsutil lifecycle set gcs-lifecycle.json gs://YOUR_BUCKET_NAME/
    ```

* Create GCP secret with FTP credentials
    
    Edit the ftp-creds file with the information for your ftp server, then run the command below:
    ```
    gcloud secrets create SECRET_NAME --data-file=/ftp-creds
    ```

### <ins>Manual Run of Python App</ins>


#### Run python script with require arguments
Be sure to change the arguments to match your environment. 
```
python /python/gcs-ftp-backup.py --gcs_bucket "YOUR_BUCKET_NAME" --secret_name "YOUR_SECRET_NAME" --remote_dir "/path/on/ftp" --local-dir "/tmp/backup" --project-id "PROJECT-ID" 
```


### <ins>Docker Container</ins>
Alternatively, you can also run it as a Docker container


Build and push to private repo (Note: Can skip the 'docker tag' and 'docker push' steps if running locally)
```
IMAGE_NAME=
REPO_LOCATION=


docker build -t $IMAGE_NAME .

docker tag $IMAGE_NAME $REPO_URL/$IMAGE_NAME:latest

docker push $REPO_URL/$IMAGE_NAME:latest
```

Docker run example if running locally
```
docker run \
--name=$IMAGE_NAME \
-e "GCS_BUCKET=BUCKET_NAME" \
-e "SECRET_NAME=SECRET_NAME" \
-e "REMOTE_DIR=/path/on/ftp" \
-e "LOCAL_DIR=/tmp/backup" \
-e "PROJECT_ID=PROJECT_ID" \
$IMAGE_NAME
```