# singer-cloud

WIP

## Install

## Usage

## Supported Cloud Providers

### AWS

#### Services Used

- ECS - Used to run the containers container taps and targets.
- EventBridge - The cron-like EventBridge scheduler is used to trigger Singer pipeline jobs.
- S3 - S3 stores configs, catalogs, and other intermediate files.
- Secrets Manager - Secrets Manager stores secrets used in the config files, like a database password.
