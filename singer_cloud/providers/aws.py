import base64

import boto3

from singer_cloud.providers.base import CloudProvider

class AWSCloudProvider(CloudProvider):
    def __init__(self, *args, **kwargs):
        super(AWSCloudProvider, self).__init__(*args, **kwargs)

        self.region = self.config.get('cloud', {}).get('region', 'us-east-1')
        self._clients = {}

    def sync(self):
        ## TODO: ensure credentials are available

        self._ensure_s3()
        self._ensure_ecr()
        self._ensure_ecs()

        ## TODO: ensure task IAM role exists
        ## TODO: for each pipelines
        ##          - upsert task definitions
        ##          - upsert task schedule

        ## TODO: destroy pipelines? Track state or use tags?

    def get_docker_uri(self):
        ## TODO: cache docker URI?
        self._ensure_ecr()
        ecr_client = self._get_client('ecr')
        response = ecr_client.describe_repositories(
            repositoryNames=[
                self.config['name']
            ]
        )
        return response['repositories'][0]['repositoryUri']

    def get_docker_auth(self):
        self._ensure_ecr()
        ecr_client = self._get_client('ecr')
        response = ecr_client.describe_repositories(
            repositoryNames=[
                self.config['name']
            ]
        )
        response = ecr_client.get_authorization_token(
            registryIds=[
                response['repositories'][0]['registryId']
            ]
        )

        auth_data = response['authorizationData'][0]

        username, password = base64.b64decode(auth_data['authorizationToken']).decode().split(':')

        return {
            'username': username,
            'password': password,
            'registry': auth_data['proxyEndpoint'],
            'reauth': True
        }

    def _get_client(self, service_name):
        if service_name in self._clients:
            return self._clients[service_name]

        client = boto3.client(service_name, region_name=self.region)
        self._clients[service_name] = client

        return client

    def _ensure_s3(self):
        s3_client = self._get_client('s3')
        bucket_name = self.config.get('cloud', {}).get('bucket_name')

        self.logger.debug('Ensuring "{}" bucket exists'.format(bucket_name))

        try:
            response = s3_client.create_bucket(
                Bucket=bucket_name
            )
        except s3_client.exceptions.BucketAlreadyExists:
            pass

    def _ensure_ecr(self):
        ecr_client = self._get_client('ecr')
        repository_name = self.config['name']

        self.logger.debug('Ensuring "{}" ECR repository exists'.format(repository_name))

        try:
            response = ecr_client.create_repository(
                repositoryName=repository_name
            )
        except ecr_client.exceptions.RepositoryAlreadyExistsException:
            pass

    def _ensure_ecs(self):
        ecs_client = self._get_client('ecs')
        cluster_name = self.config['name']

        self.logger.debug('Ensuring "{}" ECS cluster exists'.format(cluster_name))

        try:
            response = client.create_cluster(
                clusterName=cluster_name,
                settings=[
                    {
                        'name': 'containerInsights',
                        'value': 'enabled'
                    },
                ],
                capacityProviders=[
                    'FARGATE'
                ]
            )
            ## TODO: wait for cluster to be provisioned
        except Exception as e: ## ???
            print(e)
