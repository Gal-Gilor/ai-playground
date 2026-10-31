# Cloud Setup

One-time Google Cloud setup for the pipelines. Run the sections in order, in the same shell.

## Variables

Replace the placeholders with your own values. They must match `config.toml`. The region needs Vertex AI training GPU quota (L4 or T4).

```bash
CONFIG_NAME="<gcloud-configuration-name>"
PROJECT_ID="<your-project-id>"
REGION="us-central1"
BUCKET="gs://<your-private-bucket>"
REPOSITORY="dog-breed-pipeline"
SA_NAME="dog-breed-pipeline"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"
```

## 1. Create the gcloud configuration

A named configuration keeps this project's settings apart from your others.

```bash
gcloud config configurations create $CONFIG_NAME
gcloud config set project $PROJECT_ID
gcloud config set compute/region $REGION
```

## 2. Log in

The first login is for the gcloud CLI. The second creates application default credentials, which the Python SDK uses to submit pipelines.

```bash
gcloud auth login
gcloud auth application-default login
gcloud auth application-default set-quota-project $PROJECT_ID
```

## 3. Check billing

The APIs below need a billing account on the project. Link one only if `billingEnabled` is false.

```bash
gcloud billing projects describe $PROJECT_ID
# Only if billingEnabled is false:
# gcloud billing projects link $PROJECT_ID --billing-account=<BILLING_ACCOUNT_ID>  # from: gcloud billing accounts list
```

## 4. Enable the APIs

The pipeline uses Vertex AI, Artifact Registry, Cloud Build and Cloud Storage, and each API must be enabled first. The Vertex AI SDK also uses Cloud Resource Manager to confirm the output bucket belongs to the project.

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  cloudresourcemanager.googleapis.com \
  storage.googleapis.com
```

## 5. Create the Artifact Registry repository

The container images for the pipeline steps are stored here.

```bash
gcloud artifacts repositories create $REPOSITORY \
  --repository-format=docker \
  --location=$REGION
```

## 6. Create the service account

The pipelines run as this account instead of your own.

```bash
gcloud iam service-accounts create $SA_NAME \
  --display-name="Dog breed pipeline"
```

## 7. Grant permissions

The service account needs to run Vertex AI jobs, write logs, read and write the private bucket, and pull images. You need permission to run jobs as it.

```bash
USER_EMAIL=$(gcloud config get-value account)

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SA_EMAIL --role=roles/aiplatform.user

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SA_EMAIL --role=roles/logging.logWriter

gcloud storage buckets add-iam-policy-binding $BUCKET \
  --member=serviceAccount:$SA_EMAIL --role=roles/storage.objectUser

gcloud artifacts repositories add-iam-policy-binding $REPOSITORY \
  --location=$REGION \
  --member=serviceAccount:$SA_EMAIL --role=roles/artifactregistry.reader

gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \
  --member=user:$USER_EMAIL --role=roles/iam.serviceAccountUser
```

## 8. Cloud Build access

Cloud Build runs as the Compute Engine default service account (`<project number>-compute@developer.gserviceaccount.com`), which has the Editor role by default and can push to the repository. No extra grant is needed. Confirm it with a one-step test build:

```bash
cat > /tmp/build-test.yaml <<'YAML'
steps:
  - name: bash
    args: ["bash", "-c", "true"]
YAML

gcloud builds submit --no-source --config=/tmp/build-test.yaml --region=$REGION
```

Right after enabling the Cloud Build API, the first build can fail with `Permission 'iam.serviceAccounts.get' denied`. Wait a minute and run it again.
