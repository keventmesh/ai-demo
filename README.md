## Building and pushing images

Just use the existing GitHub Actions workflows, by passing some environment variables.

Install act (https://github.com/nektos/act) first.

Create a `.build.secrets` file with the following content:

```shell
# get a token by running `gh auth token`
GITHUB_TOKEN=...
# if you're using Quay, make sure you have a robot account with push permissions
REGISTRY_USERNAME=...
REGISTRY_PASSWORD=...
````

Define your container registry and your tag:
```shell
export DOCKER_REPO_OVERRIDE="quay.io/kevent-mesh"
export AI_DEMO_IMAGE_TAG="my-tag"
```

```shell

# reuse the local build container - some stuff will be cached - faster builds
# do not copy files that are ignored by Git
# Change `--remote-name=origin` if that's how your upstream Git remote is named
act --job=build \
  --env DOCKER_REPO_OVERRIDE=${DOCKER_REPO_OVERRIDE} \
  --env AI_DEMO_IMAGE_TAG=${AI_DEMO_IMAGE_TAG} \
  --secret-file=.build.secrets \
  --reuse=true \
  --use-gitignore=true \
  --remote-name=origin    
```

## Deploying

```shell
export DOCKER_REPO_OVERRIDE="quay.io/kevent-mesh"
export AI_DEMO_IMAGE_TAG="my-tag"

./infra/openshift-manifests/install.sh
```

