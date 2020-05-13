from singer_cloud.providers.aws import AWSCloudProvider

PROVIDERS = {
    'aws': AWSCloudProvider
}

def get_provider(logger, config):
    provider_name = config['cloud']['provider']
    if provider_name not in PROVIDERS:
        raise Exception('Cloud provider "{}" not supported'.format(provider_name))
    return PROVIDERS[provider_name](logger, config)
